"""GUI components for BrainSimIII Python port.

This package provides Tkinter-based dialog windows for module configuration,
replacing the WPF/XAML dialogs from the C# version.
"""

from .module_dialogs import *

__all__ = [
    "ModuleBaseDialog",
    "ModuleVisionDialog",
    "ModuleGPTInfoDialog", 
    "ModuleUKSDialog",
    "ModuleAddCountsDialog",
    "DialogManager"
]