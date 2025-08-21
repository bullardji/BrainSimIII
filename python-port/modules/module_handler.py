"""Module loading and execution support."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Type, Any
import importlib
import inspect
import pkgutil

from .module_base import ModuleBase
from .module_description import ModuleDescription
from uks import UKS


@dataclass
class RegisteredModule:
    name: str
    cls: Type[ModuleBase]
    description: ModuleDescription


class ModuleHandler:
    """Manage active modules and dispatch their ``fire`` methods."""

    def __init__(self) -> None:
        self.registry: Dict[str, RegisteredModule] = {}
        self.active_modules: List[ModuleBase] = []
        self.the_uks = UKS()
        self.discover()

    # -- registration --------------------------------------------------
    def register(self, cls: Type[ModuleBase], description: str = "") -> None:
        desc = ModuleDescription(name=cls.__name__, description=description)
        self.registry[cls.__name__] = RegisteredModule(cls.__name__, cls, desc)
        self.the_uks.get_or_add_thing(cls.__name__)

    def discover(self, package: str = __package__ or "modules") -> None:
        """Dynamically discover and register modules in *package*."""
        try:
            pkg = importlib.import_module(package)
        except Exception:  # pragma: no cover - invalid package
            return
        for _, modname, _ in pkgutil.iter_modules(pkg.__path__):
            module = importlib.import_module(f"{package}.{modname}")
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, ModuleBase) and obj is not ModuleBase:
                    self.register(obj)

    # -- activation ----------------------------------------------------
    def activate(self, name: str) -> ModuleBase:
        reg = self.registry.get(name)
        if reg is None:
            raise KeyError(f"Unknown module: {name}")
        module = reg.cls()
        module.set_uks(self.the_uks)
        module._ensure_initialized()
        self.active_modules.append(module)
        return module

    def deactivate(self, label: str) -> None:
        self.active_modules = [m for m in self.active_modules if m.label != label]

    # -- execution -----------------------------------------------------
    def fire_modules(self) -> None:
        for module in list(self.active_modules):
            if module.is_enabled:
                module.pre_step()
                module.fire()
                module.post_step()

    # -- lifecycle utilities -----------------------------------------
    def reset_all(self) -> None:
        for module in self.active_modules:
            module.reset()

    # -- parameter serialisation -------------------------------------
    def serialize_active(self) -> List[Dict[str, Any]]:
        return [m.serialize() for m in self.active_modules]

    def load_active(self, data: List[Dict[str, Any]]) -> None:
        self.active_modules = []
        for mdata in data:
            name = mdata.get("class")
            reg = self.registry.get(name)
            if not reg:
                continue
            module = reg.cls(label=mdata.get("label"))
            module.set_uks(self.the_uks)
            module._ensure_initialized()
            module.set_parameters(mdata.get("params", {}))
            self.active_modules.append(module)
