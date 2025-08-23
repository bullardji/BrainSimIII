"""Base class for BrainSimIII modules.

This module mirrors the responsibilities of the original C# ``ModuleBase``
type, providing lifecycle hooks such as ``initialize``, ``fire`` and
``reset``.  Modules derive from this class and gain a ``label`` plus access to
the shared :class:`~uks.UKS` instance used for knowledge storage.  Additional
hooks ``pre_step`` and ``post_step`` are invoked around each ``fire`` call to
allow fine‑grained control over execution.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from uks import UKS


class ModuleBase:
    """Abstract base class for all modules with lifecycle hooks."""

    def __init__(self, label: Optional[str] = None) -> None:
        self.label = label or self.__class__.__name__
        self.is_enabled: bool = True
        self.initialized: bool = False
        self.the_uks: Optional[UKS] = None
        # Track background worker threads so ``reset`` or ``on_stop`` can
        # perform a graceful shutdown.  Modules can spawn workers via
        # :meth:`start_worker`.
        self._workers: list[threading.Thread] = []

    # -- lifecycle -----------------------------------------------------
    def initialize(self) -> None:  # pragma: no cover - to be overridden
        """Perform one-time module setup."""
        raise NotImplementedError

    def on_start(self) -> None:
        """Hook executed when the module is activated."""

    def on_stop(self) -> None:
        """Hook executed when the module is deactivated.

        The default implementation joins all worker threads started via
        :meth:`start_worker`.
        """
        for t in list(self._workers):
            t.join(timeout=0.1)
        self._workers.clear()

    def reset(self) -> None:
        """Reset module state for a fresh run."""
        self.on_stop()
        self.initialized = False

    def pre_step(self) -> None:
        """Hook executed before each :meth:`fire` call."""

    def fire(self) -> None:  # pragma: no cover - to be overridden
        """Execute the module's behaviour for one simulation step."""
        raise NotImplementedError

    def post_step(self) -> None:
        """Hook executed after each :meth:`fire` call."""

    # -- parameter serialisation --------------------------------------
    def get_parameters(self) -> Dict[str, Any]:
        """Return serialisable module parameters."""
        return {}

    def set_parameters(self, params: Dict[str, Any]) -> None:
        """Restore parameters previously produced by :meth:`get_parameters`."""

    def serialize(self) -> Dict[str, Any]:
        return {"class": self.__class__.__name__, "label": self.label, "params": self.get_parameters()}

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "ModuleBase":
        obj = cls(label=data.get("label"))
        obj.set_parameters(data.get("params", {}))
        return obj

    # -- helpers -------------------------------------------------------
    def _ensure_initialized(self) -> None:
        if not self.initialized:
            self.initialize()
            self.initialized = True

    def set_uks(self, uks: UKS) -> None:
        """Assign the shared :class:`UKS` instance."""
        self.the_uks = uks

    # -- worker utilities ---------------------------------------------
    def start_worker(self, target, *args, daemon: bool = True, **kwargs) -> threading.Thread:
        """Start a background thread and track it for cleanup."""
        thread = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=daemon)
        thread.start()
        self._workers.append(thread)
        return thread

