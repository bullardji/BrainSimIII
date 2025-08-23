"""Module configuration dialogs using Tkinter.

This module provides GUI dialog windows for configuring various BrainSimIII modules,
replacing the WPF/XAML dialogs from the original C# implementation.
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from typing import Dict, Any, Optional, Callable, List
from abc import ABC, abstractmethod
import json
from pathlib import Path

try:
    from modules.module_base import ModuleBase
    from modules.module_vision import ModuleVision
    from modules.module_gpt_info import ModuleGPTInfo
    from modules.module_uks import ModuleUKS  
    from modules.module_add_counts import ModuleAddCounts
except ImportError:
    # Fallback for testing without full module system
    ModuleBase = ModuleVision = ModuleGPTInfo = ModuleUKS = ModuleAddCounts = None


class ModuleBaseDialog(ABC):
    """Base class for all module configuration dialogs.
    
    Provides common functionality like parameter management, window setup,
    and standardized button layouts.
    """
    
    def __init__(self, parent: Optional[tk.Tk] = None, module: Optional[ModuleBase] = None):
        self.parent = parent
        self.module = module
        self.window: Optional[tk.Toplevel] = None
        self.result: Dict[str, Any] = {}
        self.widgets: Dict[str, tk.Widget] = {}
        self.callbacks: Dict[str, Callable] = {}
        
    def create_dialog(self, title: str, width: int = 600, height: int = 400) -> tk.Toplevel:
        """Create the main dialog window with standard setup."""
        if self.parent:
            self.window = tk.Toplevel(self.parent)
        else:
            self.window = tk.Tk()
            
        self.window.title(title)
        self.window.geometry(f"{width}x{height}")
        self.window.configure(bg='#f0f0f0')
        self.window.resizable(True, True)
        
        # Make dialog modal
        if self.parent:
            self.window.transient(self.parent)
            self.window.grab_set()
            
        # Center the window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        
        return self.window
        
    def add_label(self, parent: tk.Widget, text: str, row: int, column: int = 0, 
                  sticky: str = "w", **kwargs) -> tk.Label:
        """Add a label widget with consistent styling."""
        label = tk.Label(parent, text=text, bg='#f0f0f0', font=('Arial', 10), **kwargs)
        label.grid(row=row, column=column, sticky=sticky, padx=5, pady=2)
        return label
        
    def add_entry(self, parent: tk.Widget, textvariable: tk.StringVar, row: int, 
                  column: int = 1, width: int = 30, **kwargs) -> tk.Entry:
        """Add an entry widget with consistent styling."""
        entry = tk.Entry(parent, textvariable=textvariable, width=width, font=('Arial', 10), **kwargs)
        entry.grid(row=row, column=column, sticky="ew", padx=5, pady=2)
        return entry
        
    def add_button(self, parent: tk.Widget, text: str, command: Callable, 
                   row: int, column: int, **kwargs) -> tk.Button:
        """Add a button with consistent styling."""
        button = tk.Button(parent, text=text, command=command, font=('Arial', 10), **kwargs)
        button.grid(row=row, column=column, padx=5, pady=5, **kwargs)
        return button
        
    def add_checkbutton(self, parent: tk.Widget, text: str, variable: tk.BooleanVar,
                        row: int, column: int = 0, **kwargs) -> tk.Checkbutton:
        """Add a checkbutton with consistent styling."""
        check = tk.Checkbutton(parent, text=text, variable=variable, bg='#f0f0f0',
                              font=('Arial', 10), **kwargs)
        check.grid(row=row, column=column, sticky="w", padx=5, pady=2)
        return check
        
    def add_text_widget(self, parent: tk.Widget, row: int, column: int = 0, 
                        columnspan: int = 2, height: int = 10) -> scrolledtext.ScrolledText:
        """Add a scrolled text widget."""
        text_widget = scrolledtext.ScrolledText(parent, height=height, font=('Arial', 9))
        text_widget.grid(row=row, column=column, columnspan=columnspan, 
                        sticky="nsew", padx=5, pady=5)
        return text_widget
        
    def create_button_frame(self) -> tk.Frame:
        """Create a standard button frame with OK/Cancel buttons."""
        button_frame = tk.Frame(self.window, bg='#f0f0f0')
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        tk.Button(button_frame, text="OK", command=self.on_ok, 
                 width=10, font=('Arial', 10)).pack(side=tk.RIGHT, padx=5)
        tk.Button(button_frame, text="Cancel", command=self.on_cancel,
                 width=10, font=('Arial', 10)).pack(side=tk.RIGHT, padx=5)
        tk.Button(button_frame, text="Apply", command=self.on_apply,
                 width=10, font=('Arial', 10)).pack(side=tk.RIGHT, padx=5)
                 
        return button_frame
        
    def on_ok(self):
        """Handle OK button click."""
        if self.validate_inputs():
            self.apply_changes()
            self.close_dialog()
            
    def on_cancel(self):
        """Handle Cancel button click."""
        self.close_dialog()
        
    def on_apply(self):
        """Handle Apply button click."""
        if self.validate_inputs():
            self.apply_changes()
            
    def close_dialog(self):
        """Close the dialog window."""
        if self.window:
            if self.parent:
                self.window.grab_release()
            self.window.destroy()
            
    def validate_inputs(self) -> bool:
        """Validate user inputs. Override in subclasses."""
        return True
        
    @abstractmethod
    def setup_ui(self):
        """Setup the dialog UI. Must be implemented by subclasses."""
        pass
        
    @abstractmethod
    def load_module_parameters(self):
        """Load parameters from the module. Must be implemented by subclasses.""" 
        pass
        
    @abstractmethod
    def apply_changes(self):
        """Apply changes to the module. Must be implemented by subclasses."""
        pass
        
    def show(self) -> Dict[str, Any]:
        """Show the dialog and return results."""
        self.setup_ui()
        self.load_module_parameters()
        
        if self.window:
            self.window.wait_window()
        return self.result


class ModuleVisionDialog(ModuleBaseDialog):
    """Configuration dialog for ModuleVision."""
    
    def __init__(self, parent: Optional[tk.Tk] = None, module: Optional[ModuleVision] = None):
        super().__init__(parent, module)
        
        # Vision-specific variables
        self.image_path = tk.StringVar()
        self.show_pixels = tk.BooleanVar()
        self.show_boundaries = tk.BooleanVar()
        self.show_strokes = tk.BooleanVar()
        self.show_segments = tk.BooleanVar()
        self.show_corners = tk.BooleanVar()
        self.horiz_scan = tk.BooleanVar(value=True)
        self.vert_scan = tk.BooleanVar(value=True)
        self.edge_threshold_low = tk.StringVar(value="50")
        self.edge_threshold_high = tk.StringVar(value="150")
        
    def setup_ui(self):
        """Setup the vision module dialog UI."""
        self.create_dialog("Vision Module Configuration", 650, 500)
        
        # Main frame
        main_frame = tk.Frame(self.window, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Image selection frame
        img_frame = tk.LabelFrame(main_frame, text="Image Selection", bg='#f0f0f0', font=('Arial', 10, 'bold'))
        img_frame.pack(fill=tk.X, pady=5)
        
        self.add_label(img_frame, "Path:", 0)
        self.add_entry(img_frame, self.image_path, 0, width=40)
        self.add_button(img_frame, "Browse", self.browse_image_file, 0, 2)
        
        # Processing parameters frame
        params_frame = tk.LabelFrame(main_frame, text="Processing Parameters", bg='#f0f0f0', font=('Arial', 10, 'bold'))
        params_frame.pack(fill=tk.X, pady=5)
        
        self.add_label(params_frame, "Edge Threshold Low:", 0)
        self.add_entry(params_frame, self.edge_threshold_low, 0, width=10)
        
        self.add_label(params_frame, "Edge Threshold High:", 1)
        self.add_entry(params_frame, self.edge_threshold_high, 1, width=10)
        
        # Display options frame
        display_frame = tk.LabelFrame(main_frame, text="Display Options", bg='#f0f0f0', font=('Arial', 10, 'bold'))
        display_frame.pack(fill=tk.X, pady=5)
        
        # Create a grid for checkboxes
        self.add_checkbutton(display_frame, "Show Pixel Array", self.show_pixels, 0, 0)
        self.add_checkbutton(display_frame, "Show Boundaries", self.show_boundaries, 0, 1)
        self.add_checkbutton(display_frame, "Show Strokes", self.show_strokes, 1, 0)
        self.add_checkbutton(display_frame, "Show Segments", self.show_segments, 1, 1)
        self.add_checkbutton(display_frame, "Show Corners", self.show_corners, 2, 0)
        
        # Scan direction frame
        scan_frame = tk.LabelFrame(main_frame, text="Scan Directions", bg='#f0f0f0', font=('Arial', 10, 'bold'))
        scan_frame.pack(fill=tk.X, pady=5)
        
        self.add_checkbutton(scan_frame, "Horizontal", self.horiz_scan, 0, 0)
        self.add_checkbutton(scan_frame, "Vertical", self.vert_scan, 0, 1)
        
        # Processing buttons frame
        process_frame = tk.Frame(main_frame, bg='#f0f0f0')
        process_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(process_frame, text="Process Image", command=self.process_image,
                 font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        tk.Button(process_frame, text="Refresh", command=self.refresh_display,
                 font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        # Results text area
        results_frame = tk.LabelFrame(main_frame, text="Processing Results", bg='#f0f0f0', font=('Arial', 10, 'bold'))
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.results_text = self.add_text_widget(results_frame, 0, 0, 2, 8)
        
        # Button frame
        self.create_button_frame()
        
    def browse_image_file(self):
        """Open file browser for image selection."""
        filename = filedialog.askopenfilename(
            title="Select Image File",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.image_path.set(filename)
            
    def process_image(self):
        """Process the selected image."""
        if not self.image_path.get():
            messagebox.showwarning("Warning", "Please select an image file first.")
            return
            
        try:
            if self.module and hasattr(self.module, 'load_image'):
                self.module.load_image(self.image_path.get())
                self.module.process_image()
                
                # Display results
                results = self.get_processing_results()
                self.results_text.delete(1.0, tk.END)
                self.results_text.insert(1.0, results)
                
            else:
                self.results_text.delete(1.0, tk.END)
                self.results_text.insert(1.0, f"Image loaded: {Path(self.image_path.get()).name}\\n")
                self.results_text.insert(tk.END, "Processing completed (simulated)")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process image: {e}")
            
    def get_processing_results(self) -> str:
        """Get processing results as formatted string."""
        if not self.module:
            return "No module connected"
            
        try:
            results = []
            results.append(f"Image: {Path(self.image_path.get()).name}")
            
            if hasattr(self.module, 'get_edge_count'):
                results.append(f"Edges detected: {self.module.get_edge_count()}")
            if hasattr(self.module, 'get_corner_count'):
                results.append(f"Corners detected: {self.module.get_corner_count()}")
            if hasattr(self.module, 'get_line_count'):
                results.append(f"Lines detected: {self.module.get_line_count()}")
            if hasattr(self.module, 'get_circle_count'):
                results.append(f"Circles detected: {self.module.get_circle_count()}")
                
            if hasattr(self.module, 'analyze_shapes'):
                shape_analysis = self.module.analyze_shapes()
                if shape_analysis:
                    results.append("\\nShape Analysis:")
                    results.append(f"Total contours: {shape_analysis.get('total_contours', 0)}")
                    for shape in shape_analysis.get('shapes', []):
                        results.append(f"- {shape['type'].title()}: area={shape['area']:.1f}")
                        
            return "\\n".join(results)
        except Exception as e:
            return f"Error getting results: {e}"
            
    def refresh_display(self):
        """Refresh the display."""
        if self.image_path.get():
            self.process_image()
        else:
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(1.0, "No image selected")
            
    def load_module_parameters(self):
        """Load parameters from the vision module."""
        if self.module and hasattr(self.module, 'get_parameters'):
            params = self.module.get_parameters()
            
            self.edge_threshold_low.set(str(params.get('edge_threshold_low', 50)))
            self.edge_threshold_high.set(str(params.get('edge_threshold_high', 150)))
            self.horiz_scan.set(params.get('horiz_scan', True))
            self.vert_scan.set(params.get('vert_scan', True))
            
            if hasattr(self.module, 'image_path') and self.module.image_path:
                self.image_path.set(self.module.image_path)
                
    def validate_inputs(self) -> bool:
        """Validate the input values."""
        try:
            low = int(self.edge_threshold_low.get())
            high = int(self.edge_threshold_high.get())
            if low < 0 or high < 0 or low >= high:
                messagebox.showerror("Invalid Input", "Edge thresholds must be positive and low < high")
                return False
            return True
        except ValueError:
            messagebox.showerror("Invalid Input", "Edge thresholds must be numbers")
            return False
            
    def apply_changes(self):
        """Apply changes to the vision module."""
        if self.module and hasattr(self.module, 'set_parameters'):
            params = {
                'edge_threshold_low': int(self.edge_threshold_low.get()),
                'edge_threshold_high': int(self.edge_threshold_high.get()),
                'horiz_scan': self.horiz_scan.get(),
                'vert_scan': self.vert_scan.get(),
                'forty_five_scan': False,  # Not implemented in UI
                'minus_forty_five_scan': False  # Not implemented in UI
            }
            self.module.set_parameters(params)
            
        self.result = {
            'image_path': self.image_path.get(),
            'parameters': params if self.module else {}
        }


class ModuleGPTInfoDialog(ModuleBaseDialog):
    """Configuration dialog for ModuleGPTInfo."""
    
    def __init__(self, parent: Optional[tk.Tk] = None, module: Optional[ModuleGPTInfo] = None):
        super().__init__(parent, module)
        
        # GPT-specific variables
        self.gpt_input = tk.StringVar()
        self.status_text = tk.StringVar(value="Ready")
        
    def setup_ui(self):
        """Setup the GPT info module dialog UI."""
        self.create_dialog("GPT Information Module", 800, 450)
        
        # Main frame
        main_frame = tk.Frame(self.window, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Input frame
        input_frame = tk.LabelFrame(main_frame, text="GPT Request", bg='#f0f0f0', font=('Arial', 10, 'bold'))
        input_frame.pack(fill=tk.X, pady=5)
        
        instruction_label = tk.Label(input_frame, 
                                   text="GPT Request. Follow by [Enter] for Info.\\nFollow by [Up-arrow] for parents only.",
                                   bg='#f0f0f0', font=('Arial', 9))
        instruction_label.pack(anchor="w", padx=5, pady=5)
        
        input_entry = tk.Entry(input_frame, textvariable=self.gpt_input, font=('Arial', 12), width=60)
        input_entry.pack(fill=tk.X, padx=5, pady=5)
        input_entry.bind('<Return>', self.on_gpt_request)
        input_entry.bind('<Up>', self.on_parent_request)
        
        # Control buttons frame
        control_frame = tk.Frame(main_frame, bg='#f0f0f0')
        control_frame.pack(fill=tk.X, pady=5)
        
        # Left column buttons
        left_buttons = tk.Frame(control_frame, bg='#f0f0f0')
        left_buttons.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Button(left_buttons, text="Re-Parse", command=self.reparse_content,
                 width=18, font=('Arial', 10)).pack(pady=2)
        tk.Button(left_buttons, text="Handle Unknowns", command=self.handle_unknowns,
                 width=18, font=('Arial', 10)).pack(pady=2)
        tk.Button(left_buttons, text="Add Clauses To All", command=self.add_clauses,
                 width=18, font=('Arial', 10)).pack(pady=2)
        tk.Button(left_buttons, text="Remove Duplicates", command=self.remove_duplicates,
                 width=18, font=('Arial', 10)).pack(pady=2)
        
        # Right column buttons  
        right_buttons = tk.Frame(control_frame, bg='#f0f0f0')
        right_buttons.pack(side=tk.RIGHT, fill=tk.Y)
        
        tk.Button(right_buttons, text="Load Word File", command=self.load_word_file,
                 width=18, font=('Arial', 10)).pack(pady=2)
        tk.Button(right_buttons, text="Verify All Parents", command=self.verify_parents,
                 width=18, font=('Arial', 10)).pack(pady=2)
        tk.Button(right_buttons, text="Solve Ambiguity", command=self.solve_ambiguity,
                 width=18, font=('Arial', 10)).pack(pady=2)
        tk.Button(right_buttons, text="Ambiguity File", command=self.load_ambiguity,
                 width=18, font=('Arial', 10)).pack(pady=2)
        
        # Output frame
        output_frame = tk.LabelFrame(main_frame, text="Output", bg='#f0f0f0', font=('Arial', 10, 'bold'))
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.output_text = self.add_text_widget(output_frame, 0, 0, 1, 15)
        
        # Status bar
        status_frame = tk.Frame(main_frame, bg='#f0f0f0')
        status_frame.pack(fill=tk.X, pady=2)
        
        status_label = tk.Label(status_frame, textvariable=self.status_text,
                              bg='#f0f0f0', font=('Arial', 9), anchor="w")
        status_label.pack(fill=tk.X, padx=5)
        
        # Button frame
        self.create_button_frame()
        
    def on_gpt_request(self, event):
        """Handle GPT request (Enter key)."""
        query = self.gpt_input.get().strip()
        if not query:
            return
            
        self.status_text.set("Processing GPT request...")
        self.window.update()
        
        try:
            if self.module and hasattr(self.module, 'process_gpt_query'):
                result = self.module.process_gpt_query(query)
                self.output_text.insert(tk.END, f"Query: {query}\\n")
                self.output_text.insert(tk.END, f"Result: {result}\\n\\n")
                self.status_text.set("GPT request completed")
            else:
                self.output_text.insert(tk.END, f"GPT Query: {query}\\n")
                self.output_text.insert(tk.END, "Result: [Simulated response - module not connected]\\n\\n")
                self.status_text.set("Simulated response")
                
            self.output_text.see(tk.END)
            self.gpt_input.set("")
            
        except Exception as e:
            self.output_text.insert(tk.END, f"Error: {e}\\n\\n")
            self.status_text.set(f"Error: {e}")
            
    def on_parent_request(self, event):
        """Handle parent-only request (Up arrow)."""
        query = self.gpt_input.get().strip()
        if not query:
            return
            
        self.status_text.set("Processing parent request...")
        self.window.update()
        
        try:
            if self.module and hasattr(self.module, 'get_parent_info'):
                result = self.module.get_parent_info(query)
                self.output_text.insert(tk.END, f"Parent Query: {query}\\n")
                self.output_text.insert(tk.END, f"Parents: {result}\\n\\n")
                self.status_text.set("Parent request completed")
            else:
                self.output_text.insert(tk.END, f"Parent Query: {query}\\n")
                self.output_text.insert(tk.END, "Parents: [Simulated response]\\n\\n")
                self.status_text.set("Simulated response")
                
            self.output_text.see(tk.END)
            self.gpt_input.set("")
            
        except Exception as e:
            self.output_text.insert(tk.END, f"Error: {e}\\n\\n")
            self.status_text.set(f"Error: {e}")
            
    def reparse_content(self):
        """Re-parse existing content."""
        self.execute_command("reparse")
        
    def handle_unknowns(self):
        """Handle unknown entities."""
        self.execute_command("handle_unknowns")
        
    def add_clauses(self):
        """Add clauses to all entities."""
        self.execute_command("add_clauses")
        
    def remove_duplicates(self):
        """Remove duplicate entries."""
        self.execute_command("remove_duplicates")
        
    def verify_parents(self):
        """Verify all parent relationships."""
        self.execute_command("verify_parents")
        
    def solve_ambiguity(self):
        """Solve ambiguity issues."""
        self.execute_command("solve_ambiguity")
        
    def load_word_file(self):
        """Load a word file."""
        filename = filedialog.askopenfilename(
            title="Select Word File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.output_text.insert(tk.END, f"Loaded file: {filename}\\n")
                self.output_text.insert(tk.END, f"Content preview: {content[:200]}...\\n\\n")
                self.status_text.set(f"Loaded {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {e}")
                
    def load_ambiguity(self):
        """Load ambiguity file.""" 
        filename = filedialog.askopenfilename(
            title="Select Ambiguity File",
            filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.output_text.insert(tk.END, f"Ambiguity file loaded: {filename}\\n\\n")
            self.status_text.set(f"Loaded ambiguity file: {Path(filename).name}")
            
    def execute_command(self, command: str):
        """Execute a command and display results."""
        self.status_text.set(f"Executing {command}...")
        self.window.update()
        
        try:
            if self.module and hasattr(self.module, command):
                result = getattr(self.module, command)()
                self.output_text.insert(tk.END, f"Command: {command}\\n")
                self.output_text.insert(tk.END, f"Result: {result}\\n\\n")
                self.status_text.set(f"Command {command} completed")
            else:
                self.output_text.insert(tk.END, f"Executed: {command} [Simulated]\\n\\n")
                self.status_text.set(f"Simulated: {command}")
                
            self.output_text.see(tk.END)
            
        except Exception as e:
            self.output_text.insert(tk.END, f"Error executing {command}: {e}\\n\\n")
            self.status_text.set(f"Error: {e}")
            
    def load_module_parameters(self):
        """Load parameters from the GPT module."""
        if self.module:
            # Load any existing state or configuration
            pass
            
    def validate_inputs(self) -> bool:
        """Validate inputs."""
        return True
        
    def apply_changes(self):
        """Apply changes to the GPT module."""
        self.result = {
            'output': self.output_text.get(1.0, tk.END)
        }


class ModuleAddCountsDialog(ModuleBaseDialog):
    """Configuration dialog for ModuleAddCounts."""
    
    def __init__(self, parent: Optional[tk.Tk] = None, module: Optional[ModuleAddCounts] = None):
        super().__init__(parent, module)
        
        self.count_limit = tk.StringVar(value="100")
        self.reset_counts = tk.BooleanVar()
        
    def setup_ui(self):
        """Setup the add counts module dialog UI."""
        self.create_dialog("Add Counts Module Configuration", 400, 300)
        
        # Main frame
        main_frame = tk.Frame(self.window, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Parameters frame
        params_frame = tk.LabelFrame(main_frame, text="Count Parameters", bg='#f0f0f0', font=('Arial', 10, 'bold'))
        params_frame.pack(fill=tk.X, pady=10)
        
        self.add_label(params_frame, "Count Limit:", 0)
        self.add_entry(params_frame, self.count_limit, 0, width=15)
        
        # Options frame
        options_frame = tk.LabelFrame(main_frame, text="Options", bg='#f0f0f0', font=('Arial', 10, 'bold'))
        options_frame.pack(fill=tk.X, pady=10)
        
        self.add_checkbutton(options_frame, "Reset counts on start", self.reset_counts, 0)
        
        # Information frame
        info_frame = tk.LabelFrame(main_frame, text="Information", bg='#f0f0f0', font=('Arial', 10, 'bold'))
        info_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        info_text = tk.Text(info_frame, height=6, wrap=tk.WORD, font=('Arial', 9))
        info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        info_text.insert(1.0, 
            "The Add Counts module tracks numerical counting for UKS entities.\\n\\n"
            "It maintains counters and provides increment/decrement functionality "
            "for various knowledge management operations.\\n\\n"
            "Set the count limit to control maximum count values."
        )
        info_text.config(state=tk.DISABLED)
        
        # Button frame
        self.create_button_frame()
        
    def load_module_parameters(self):
        """Load parameters from the module."""
        if self.module and hasattr(self.module, 'get_parameters'):
            params = self.module.get_parameters()
            self.count_limit.set(str(params.get('count_limit', 100)))
            self.reset_counts.set(params.get('reset_counts', False))
            
    def validate_inputs(self) -> bool:
        """Validate inputs."""
        try:
            limit = int(self.count_limit.get())
            if limit <= 0:
                messagebox.showerror("Invalid Input", "Count limit must be positive")
                return False
            return True
        except ValueError:
            messagebox.showerror("Invalid Input", "Count limit must be a number")
            return False
            
    def apply_changes(self):
        """Apply changes to the module."""
        if self.module and hasattr(self.module, 'set_parameters'):
            params = {
                'count_limit': int(self.count_limit.get()),
                'reset_counts': self.reset_counts.get()
            }
            self.module.set_parameters(params)
            
        self.result = {
            'count_limit': int(self.count_limit.get()),
            'reset_counts': self.reset_counts.get()
        }


class DialogManager:
    """Manager for module configuration dialogs."""
    
    # Mapping of module types to their dialog classes
    DIALOG_CLASSES = {
        'ModuleVision': ModuleVisionDialog,
        'ModuleGPTInfo': ModuleGPTInfoDialog,
        'ModuleAddCounts': ModuleAddCountsDialog,
        # Can be extended with more module dialogs
    }
    
    @classmethod
    def get_dialog_for_module(cls, module: ModuleBase, parent: Optional[tk.Tk] = None) -> Optional[ModuleBaseDialog]:
        """Get the appropriate dialog for a module instance."""
        module_class_name = module.__class__.__name__
        dialog_class = cls.DIALOG_CLASSES.get(module_class_name)
        
        if dialog_class:
            return dialog_class(parent, module)
        return None
        
    @classmethod
    def show_module_dialog(cls, module: ModuleBase, parent: Optional[tk.Tk] = None) -> Dict[str, Any]:
        """Show the configuration dialog for a module."""
        dialog = cls.get_dialog_for_module(module, parent)
        if dialog:
            return dialog.show()
        else:
            messagebox.showinfo("Info", f"No configuration dialog available for {module.__class__.__name__}")
            return {}
            
    @classmethod
    def register_dialog(cls, module_class_name: str, dialog_class: type):
        """Register a new dialog class for a module type."""
        cls.DIALOG_CLASSES[module_class_name] = dialog_class