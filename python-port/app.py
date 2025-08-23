"""Tkinter based application shell for the BrainSimIII Python port.

This module recreates a small portion of the C# application's start-up
sequence and user interface.  The goal is not to perfectly mimic the WPF
version but to provide a functional GUI entry point capable of loading and
saving projects, managing modules, and routing menu events.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, List

try:  # GUI imports may fail in headless environments during testing
    import tkinter as tk
    from tkinter import filedialog, messagebox
except Exception:  # pragma: no cover - GUI not available
    tk = None  # type: ignore
    filedialog = messagebox = None  # type: ignore

from modules.module_handler import ModuleHandler
from network import Network
from uks.uks import UKS
from uks.thing_labels import ThingLabels
from xml_utils import save_xml, load_xml
from gui.module_dialogs import DialogManager


class BrainSimApp:
    """Main application window built with Tkinter.

    Parameters
    ----------
    root:
        Optional pre-created Tk root.  Supplying a dummy object here allows the
        class to be instantiated during automated testing without requiring a
        display server.
    """

    def __init__(self, root: Optional["tk.Tk"] = None) -> None:
        if tk is None:
            raise RuntimeError("Tkinter is not available on this system")
        self.root = root or tk.Tk()
        self.root.title("BrainSimIII")
        self.module_handler = ModuleHandler()
        self.network = Network()
        self.uks = self.module_handler.the_uks
        self._project_file: Optional[Path] = None
        self.mru: List[Path] = self._load_mru()
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=0)
        file_menu.add_command(label="New", command=self.new_project, accelerator="Ctrl+N")
        file_menu.add_command(label="Open", command=self.open_project, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_project, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As", command=self.save_project_as)
        file_menu.add_separator()
        self._recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Open Recent", menu=self._recent_menu)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)
        menu.add_cascade(label="File", menu=file_menu)

        sim_menu = tk.Menu(menu, tearoff=0)
        sim_menu.add_command(label="Run", command=lambda: self.network.run())
        sim_menu.add_command(label="Pause", command=self.network.pause)
        sim_menu.add_command(label="Stop", command=self.network.stop)
        menu.add_cascade(label="Simulation", menu=sim_menu)

        # Modules menu
        modules_menu = tk.Menu(menu, tearoff=0)
        modules_menu.add_command(label="Configure Active Modules", command=self.configure_modules)
        modules_menu.add_separator()
        # Add individual module configuration options
        modules_menu.add_command(label="Vision Module", command=lambda: self.configure_specific_module("ModuleVision"))
        modules_menu.add_command(label="GPT Info Module", command=lambda: self.configure_specific_module("ModuleGPTInfo"))
        modules_menu.add_command(label="Add Counts Module", command=lambda: self.configure_specific_module("ModuleAddCounts"))
        menu.add_cascade(label="Modules", menu=modules_menu)

        self.root.config(menu=menu)
        self._refresh_mru_menu()

        # Toolbar with textual buttons; using images would require shipping binary files.
        toolbar = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        tk.Button(toolbar, text="Step", command=self.module_handler.fire_modules).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Run", command=lambda: self.network.run()).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Pause", command=self.network.pause).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Stop", command=self.network.stop).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Record", command=lambda: self.save_project(self._project_file)).pack(side=tk.LEFT)
        toolbar.pack(side=tk.TOP, fill=tk.X)

    # ------------------------------------------------------------------
    # MRU handling and resources
    # ------------------------------------------------------------------
    MRU_FILE = Path.home() / ".brainsim_mru.json"
    MAX_MRU = 5

    def _load_mru(self) -> List[Path]:
        try:
            data = json.loads(self.MRU_FILE.read_text(encoding="utf-8"))
            return [Path(p) for p in data]
        except Exception:
            return []

    def _save_mru(self) -> None:
        try:
            self.MRU_FILE.write_text(json.dumps([str(p) for p in self.mru]), encoding="utf-8")
        except Exception:
            pass

    def _update_mru(self, path: Path) -> None:
        if path in self.mru:
            self.mru.remove(path)
        self.mru.insert(0, path)
        del self.mru[self.MAX_MRU :]
        self._save_mru()
        self._refresh_mru_menu()

    def _refresh_mru_menu(self) -> None:
        self._recent_menu.delete(0, tk.END)
        for p in self.mru:
            self._recent_menu.add_command(label=str(p), command=lambda path=p: self.open_project(str(path)))

    def _load_resource(self, name: str) -> str:
        """Load a text resource from the local resources directory."""
        res_dir = Path(__file__).resolve().parent / "resources"
        path = res_dir / name
        return path.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Project management
    # ------------------------------------------------------------------
    def new_project(self) -> None:
        """Clear network, UKS and modules creating a fresh project."""
        self.network = Network()
        ThingLabels.clear_label_list()
        self.module_handler = ModuleHandler()
        self.uks = self.module_handler.the_uks
        self._project_file = None

    def save_project(self, path: Optional[str] = None) -> None:
        """Serialise network, UKS and active modules to *path*.

        If *path* is omitted a file dialog is shown to choose the destination.
        """

        if path is None:
            if filedialog is None:  # pragma: no cover - GUI not available
                raise RuntimeError("file dialogs are unavailable")
            path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("BrainSim Project", "*.json"), ("BrainSim Project", "*.xml")],
            )
            if not path:
                return
        data = {
            "network": self.network.to_dict(),
            "uks": self.uks.to_dict(),
            "modules": self.module_handler.serialize_active(),
        }
        ext = Path(path).suffix.lower()
        if ext == ".xml":
            save_xml(path, data)
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        self._project_file = Path(path)
        self._update_mru(self._project_file)

    def save_project_as(self) -> None:
        self.save_project(None)

    def open_project(self, path: Optional[str] = None) -> None:
        """Load network, UKS and modules from *path*.

        If *path* is omitted a file dialog is used to select the file.
        """

        if path is None:
            if filedialog is None:  # pragma: no cover - GUI not available
                raise RuntimeError("file dialogs are unavailable")
            path = filedialog.askopenfilename(filetypes=[("BrainSim Project", "*.json"), ("BrainSim Project", "*.xml")])
            if not path:
                return
        ext = Path(path).suffix.lower()
        if ext == ".xml":
            data = load_xml(path)
        else:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        self.network.from_dict(data.get("network", {}))
        self.uks.from_dict(data.get("uks", {}))
        self.module_handler.load_active(data.get("modules", []))
        self._project_file = Path(path)
        self._update_mru(self._project_file)

    # ------------------------------------------------------------------
    # Module configuration
    # ------------------------------------------------------------------
    def configure_modules(self) -> None:
        """Show configuration dialogs for all active modules."""
        active_modules = self.module_handler.active_modules
        if not active_modules:
            if messagebox:
                messagebox.showinfo("No Active Modules", "No modules are currently active. Activate modules first.")
            return
            
        # Create a module selection dialog
        self._show_module_selection_dialog(active_modules)
        
    def configure_specific_module(self, module_class_name: str) -> None:
        """Configure a specific module type."""
        # Find if module is active
        target_module = None
        for module in self.module_handler.active_modules:
            if module.__class__.__name__ == module_class_name:
                target_module = module
                break
                
        if not target_module:
            # Try to activate the module
            try:
                target_module = self.module_handler.activate(module_class_name)
            except Exception as e:
                if messagebox:
                    messagebox.showerror("Module Error", f"Could not activate {module_class_name}: {e}")
                return
                
        # Show configuration dialog
        try:
            result = DialogManager.show_module_dialog(target_module, self.root)
            if result:
                print(f"Module {module_class_name} configured: {result}")
        except Exception as e:
            if messagebox:
                messagebox.showerror("Configuration Error", f"Error configuring {module_class_name}: {e}")
                
    def _show_module_selection_dialog(self, modules: List) -> None:
        """Show a dialog to select which module to configure."""
        if not tk:
            return
            
        # Create selection window
        selection_window = tk.Toplevel(self.root)
        selection_window.title("Configure Modules")
        selection_window.geometry("400x300")
        selection_window.transient(self.root)
        selection_window.grab_set()
        
        # Center the window
        selection_window.update_idletasks()
        x = (selection_window.winfo_screenwidth() // 2) - 200
        y = (selection_window.winfo_screenheight() // 2) - 150
        selection_window.geometry(f"400x300+{x}+{y}")
        
        # Title label
        title_label = tk.Label(selection_window, text="Select Module to Configure", 
                              font=('Arial', 12, 'bold'))
        title_label.pack(pady=10)
        
        # Module list frame
        list_frame = tk.Frame(selection_window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Listbox with scrollbar
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=('Arial', 10))
        listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        
        # Populate listbox
        for module in modules:
            display_name = f"{module.__class__.__name__} ({module.label})"
            listbox.insert(tk.END, display_name)
            
        # Button frame
        button_frame = tk.Frame(selection_window)
        button_frame.pack(fill=tk.X, padx=20, pady=10)
        
        def configure_selected():
            selection = listbox.curselection()
            if selection:
                selected_module = modules[selection[0]]
                selection_window.destroy()
                try:
                    result = DialogManager.show_module_dialog(selected_module, self.root)
                    if result:
                        print(f"Module {selected_module.__class__.__name__} configured: {result}")
                except Exception as e:
                    if messagebox:
                        messagebox.showerror("Configuration Error", f"Error configuring module: {e}")
            else:
                if messagebox:
                    messagebox.showwarning("No Selection", "Please select a module to configure.")
                    
        tk.Button(button_frame, text="Configure", command=configure_selected,
                 width=12, font=('Arial', 10)).pack(side=tk.RIGHT, padx=5)
        tk.Button(button_frame, text="Cancel", command=selection_window.destroy,
                 width=12, font=('Arial', 10)).pack(side=tk.RIGHT, padx=5)

    # ------------------------------------------------------------------
    # Application execution
    # ------------------------------------------------------------------
    def run(self) -> None:  # pragma: no cover - requires GUI loop
        self.root.mainloop()


__all__ = ["BrainSimApp"]
