"""Tkinter based application shell for the BrainSimIII Python port.

This module recreates a small portion of the C# application's start-up
sequence and user interface.  The goal is not to perfectly mimic the WPF
version but to provide a functional GUI entry point capable of loading and
saving projects, managing modules, and routing menu events.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

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
from pathlib import Path


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
        file_menu.add_command(label="Exit", command=self.root.destroy)
        menu.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menu)

        # Toolbar with textual buttons; using images would require shipping binary files.
        toolbar = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        tk.Button(toolbar, text="Step", command=self.module_handler.fire_modules).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Record", command=lambda: self.save_project(self._project_file)).pack(side=tk.LEFT)
        toolbar.pack(side=tk.TOP, fill=tk.X)

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
            path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("BrainSim Project", "*.json")])
            if not path:
                return
        data = {
            "network": self.network.to_dict(),
            "uks": self.uks.to_dict(),
            "modules": self.module_handler.serialize_active(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        self._project_file = Path(path)

    def save_project_as(self) -> None:
        self.save_project(None)

    def open_project(self, path: Optional[str] = None) -> None:
        """Load network, UKS and modules from *path*.

        If *path* is omitted a file dialog is used to select the file.
        """

        if path is None:
            if filedialog is None:  # pragma: no cover - GUI not available
                raise RuntimeError("file dialogs are unavailable")
            path = filedialog.askopenfilename(filetypes=[("BrainSim Project", "*.json")])
            if not path:
                return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.network.from_dict(data.get("network", {}))
        self.uks.from_dict(data.get("uks", {}))
        self.module_handler.load_active(data.get("modules", []))
        self._project_file = Path(path)

    # ------------------------------------------------------------------
    # Application execution
    # ------------------------------------------------------------------
    def run(self) -> None:  # pragma: no cover - requires GUI loop
        self.root.mainloop()


__all__ = ["BrainSimApp"]
