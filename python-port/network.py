"""Network utilities and core simulation engine for the BrainSimIII port.

This module originally started life as a tiny wrapper around a few pieces of
the C# :file:`Network.cs` file which handled UDP communication.  The real
project, however, also defines a *neural network* consisting of neurons and
weighted synapses with a cyclic update loop.  To move the Python port closer
to feature parity we now provide a small, self‑contained implementation of
those data structures alongside the existing UDP helpers.

Over time this module has grown to mirror more of the original C# feature set:

* A layer based architecture allowing feed‑forward networks where neurons in
  lower layers update before those in higher layers.
* Built‑in activation functions and support for several neuron "types".
* An optional asynchronous update loop with timing control driven by a worker
  thread.  The loop can be started and stopped at runtime.
* A very small Hebbian style learning rule which adjusts synapse weights based
  on the activity of connected neurons.

The networking helpers remain intentionally lightweight and are sufficient for
unit tests and local communication.  The neural network implementation is
designed to be easy to understand while still supporting the essential
behaviour required by modules built on top of it.
"""
from __future__ import annotations

import socket
import math
import threading
import time
import json
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

try:  # optional vectorised maths
    import numpy as np  # type: ignore
    _HAVE_NUMPY = True
except Exception:  # pragma: no cover - optional dependency
    _HAVE_NUMPY = False

UDP_RECEIVE_PORT = 3333
UDP_SEND_PORT = 3333


def _create_udp_socket(broadcast: bool = False) -> socket.socket:
    """Create a UDP socket optionally configured for broadcast."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if broadcast:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    return s


def broadcast(message: str, port: int = UDP_SEND_PORT, address: Optional[str] = None) -> None:
    """Send *message* as a UDP broadcast.

    Parameters
    ----------
    message:
        The string message to send.
    port:
        The UDP port to broadcast on.  Defaults to :data:`UDP_SEND_PORT`.
    address:
        Optional address to broadcast to.  If omitted, ``'<broadcast>'`` is used
        which lets the OS determine the correct broadcast address.
    """
    data = message.encode("utf-8")
    addr = address or "<broadcast>"
    with _create_udp_socket(broadcast=True) as s:
        s.sendto(data, (addr, port))


def udp_send(message: str, ip: str, port: int) -> None:
    """Send *message* to ``ip``/``port`` via UDP."""
    data = message.encode("utf-8")
    with _create_udp_socket() as s:
        s.sendto(data, (ip, port))


# ---------------------------------------------------------------------------
# Neural network simulation
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Synapse:
    """Connection between two neurons with an associated ``weight``.

    Parameters
    ----------
    pre, post:
        Identifiers of the pre‑ and post‑synaptic neurons.
    weight:
        Synaptic strength used when propagating signals.
    learning_rate:
        If non‑zero the synapse weight is adjusted after each update using a
        basic Hebbian rule ``w += lr * pre_value * post_value``.
    stdp_rate/stdp_tau:
        Parameters for a very small spike‑timing dependent plasticity rule.
        When both neurons have recently fired within ``stdp_tau`` seconds the
        weight is adjusted by ``± stdp_rate * exp(-|Δt|/stdp_tau)`` depending on
        the order of firing.
    """

    pre: str
    post: str
    weight: float = 1.0
    learning_rate: float = 0.0
    stdp_rate: float = 0.0
    stdp_tau: float = 1.0


def _identity(x: float) -> float:
    return x


def _relu(x: float) -> float:
    return x if x > 0 else 0.0


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


_ACTIVATIONS: Dict[str, Callable[[float], float]] = {
    "linear": _identity,
    "relu": _relu,
    "sigmoid": _sigmoid,
}


@dataclass(slots=True)
class Neuron:
    """A neuron used by :class:`Network`.

    Parameters
    ----------
    id:
        Identifier for the neuron.  Used when creating connections.
    bias:
        Constant value added to the neuron's input each update.
    activation:
        Activation function name or callable.  ``'linear'`` (identity) is used
        by default.
    layer:
        Execution layer used when performing a feed‑forward step.  Neurons in a
        lower layer are updated before those in higher layers.  When all
        neurons have ``layer=0`` the behaviour is the same as a classic
        synchronous update.
    kind:
        Either ``'excitatory'`` or ``'inhibitory'``.  Inhibitory neurons invert
        the sign of their outgoing signals.
    spike_threshold:
        Value above which the neuron is considered to have "fired".  The most
        recent firing time is stored in :attr:`last_spike` for use by the STDP
        learning rule.
    """

    id: str
    value: float = 0.0
    bias: float = 0.0
    activation: Callable[[float], float] = _identity
    layer: int = 0
    kind: str = "excitatory"  # or "inhibitory" or "spiking"
    spike_threshold: float = 1.0
    refractory: float = 0.0
    last_spike: Optional[float] = None


class Network:
    """A very small neural network engine.

    Neurons are stored by ``id`` and connections are represented by
    :class:`Synapse` instances.  The :meth:`step` method performs a synchronous
    update across all neurons so that each cycle uses the output values from
    the previous cycle, matching the behaviour of the original C# engine.
    """

    def __init__(self) -> None:
        self.neurons: Dict[str, Neuron] = {}
        self._incoming: Dict[str, List[Synapse]] = {}
        self.layers: Dict[int, List[str]] = {}
        self._synapses: List[Synapse] = []
        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self.time: float = 0.0
        self._dt: float = 1.0
        self.profiler: Optional[Callable[[float], None]] = None

    # -- construction -------------------------------------------------
    def add_neuron(
        self,
        neuron_id: str,
        *,
        bias: float = 0.0,
        activation: Optional[Callable[[float], float]] | str = None,
        layer: int = 0,
        kind: str = "excitatory",
        spike_threshold: float = 1.0,
        refractory: float = 0.0,
    ) -> Neuron:
        """Create a neuron and add it to the network.

        ``activation`` may be either a callable or the name of one of the
        built‑in activation functions (``'linear'``, ``'relu'`` or
        ``'sigmoid'``).  ``kind`` specifies whether the neuron is excitatory or
        inhibitory.
        """

        if neuron_id in self.neurons:
            raise ValueError(f"Neuron '{neuron_id}' already exists")

        if isinstance(activation, str):
            act_fn = _ACTIVATIONS[activation]
        else:
            act_fn = activation or _identity

        neuron = Neuron(
            neuron_id,
            bias=bias,
            activation=act_fn,
            layer=layer,
            kind=kind,
            spike_threshold=spike_threshold,
            refractory=refractory,
        )
        self.neurons[neuron_id] = neuron
        self._incoming[neuron_id] = []
        self.layers.setdefault(layer, []).append(neuron_id)
        return neuron

    def connect(
        self,
        pre: str,
        post: str,
        weight: float = 1.0,
        *,
        learning_rate: float = 0.0,
        stdp_rate: float = 0.0,
        stdp_tau: float = 1.0,
    ) -> Synapse:
        """Create a synapse from ``pre`` to ``post`` with ``weight``.

        ``learning_rate`` enables the simple Hebbian weight update rule.
        ``stdp_rate`` and ``stdp_tau`` control spike‑timing dependent
        plasticity.
        """

        if pre not in self.neurons or post not in self.neurons:
            raise KeyError("Both neurons must be added before connecting")
        syn = Synapse(pre, post, weight, learning_rate, stdp_rate, stdp_tau)
        self._incoming[post].append(syn)
        self._synapses.append(syn)
        return syn

    # -- runtime ------------------------------------------------------
    def set_input(self, neuron_id: str, value: float) -> None:
        """Directly set the output value of ``neuron_id``."""
        with self._lock:
            self.neurons[neuron_id].value = value

    def step(self, dt: float = 1.0) -> None:
        """Advance the simulation by one cycle.

        The update proceeds layer by layer.  Neurons in a lower ``layer`` are
        evaluated first and the resulting values immediately committed so that
        subsequent layers operate on the most recent outputs.  If all neurons
        reside in the same layer the behaviour degenerates to a synchronous
        update matching the original simple engine.

        ``dt`` specifies the simulated time delta added to :attr:`time` and is
        also used by the STDP learning rule.
        """

        start = time.perf_counter()
        with self._lock:
            self.time += dt
            for layer in sorted(self.layers.keys()):
                next_values: Dict[str, float] = {}
                for neuron_id in self.layers[layer]:
                    neuron = self.neurons[neuron_id]
                    if not self._incoming[neuron_id]:
                        next_values[neuron_id] = neuron.value
                        continue

                    # respect refractory period for spiking neurons
                    if (
                        neuron.kind == "spiking"
                        and neuron.last_spike is not None
                        and self.time - neuron.last_spike < neuron.refractory
                    ):
                        next_values[neuron_id] = 0.0
                        continue

                    total = neuron.bias
                    synapses = self._incoming[neuron_id]
                    if _HAVE_NUMPY and synapses:
                        pre_vals = np.array(
                            [
                                self.neurons[s.pre].value
                                * (1.0 if self.neurons[s.pre].kind == "excitatory" else -1.0)
                                for s in synapses
                            ],
                            dtype=float,
                        )
                        weights = np.array([s.weight for s in synapses], dtype=float)
                        total += float(np.dot(pre_vals, weights))
                    else:
                        for syn in synapses:
                            sign = 1.0 if self.neurons[syn.pre].kind == "excitatory" else -1.0
                            total += self.neurons[syn.pre].value * syn.weight * sign

                    value = neuron.activation(total)
                    if neuron.kind == "spiking":
                        next_values[neuron_id] = 1.0 if value >= neuron.spike_threshold else 0.0
                    else:
                        next_values[neuron_id] = value
                for neuron_id, value in next_values.items():
                    neuron = self.neurons[neuron_id]
                    neuron.value = value
                    if value >= neuron.spike_threshold:
                        neuron.last_spike = self.time

            # -- learning ---------------------------------------------
            for syn in self._synapses:
                pre_val = self.neurons[syn.pre].value
                post_val = self.neurons[syn.post].value
                if syn.learning_rate != 0.0:
                    syn.weight += syn.learning_rate * pre_val * post_val
                if syn.stdp_rate != 0.0:
                    pre_t = self.neurons[syn.pre].last_spike
                    post_t = self.neurons[syn.post].last_spike
                    if pre_t is not None and post_t is not None:
                        dt_spike = post_t - pre_t
                        if abs(dt_spike) <= syn.stdp_tau:
                            delta = syn.stdp_rate * math.exp(-abs(dt_spike) / syn.stdp_tau)
                            if dt_spike > 0:
                                syn.weight += delta
                            elif dt_spike < 0:
                                syn.weight -= delta

        if self.profiler:
            self.profiler(time.perf_counter() - start)

    # -- asynchronous execution -------------------------------------
    def run(self, tick_rate: float = 10.0) -> None:
        """Start an asynchronous update loop.

        Parameters
        ----------
        tick_rate:
            Number of :meth:`step` executions per second.  The inverse is used
            as ``dt`` for both timing and the simulated :attr:`time`.
        """

        if self._running:
            return

        self._dt = 1.0 / tick_rate
        with self._lock:
            self._running = True
            self._paused = False

        def loop() -> None:
            next_time = time.perf_counter()
            while self._running:
                if not self._paused:
                    self.step(self._dt)
                    next_time += self._dt
                sleep = next_time - time.perf_counter()
                if sleep > 0:
                    time.sleep(sleep)
                else:
                    next_time = time.perf_counter()

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def pause(self) -> None:
        """Temporarily pause the asynchronous update loop."""
        with self._lock:
            self._paused = True

    def resume(self) -> None:
        """Resume a paused asynchronous update loop."""
        with self._lock:
            self._paused = False

    def stop(self) -> None:
        """Stop the asynchronous update loop started by :meth:`run`."""

        with self._lock:
            self._running = False
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    # -- persistence -------------------------------------------------
    def save(self, path: str) -> None:
        """Serialise the network to *path* in JSON format."""

        data = {
            "time": self.time,
            "neurons": [
                {
                    "id": nid,
                    "value": n.value,
                    "bias": n.bias,
                    "activation": next(
                        (name for name, fn in _ACTIVATIONS.items() if fn is n.activation),
                        None,
                    ),
                    "layer": n.layer,
                    "kind": n.kind,
                    "spike_threshold": n.spike_threshold,
                    "refractory": n.refractory,
                    "last_spike": n.last_spike,
                }
                for nid, n in self.neurons.items()
            ],
            "synapses": [
                {
                    "pre": s.pre,
                    "post": s.post,
                    "weight": s.weight,
                    "learning_rate": s.learning_rate,
                    "stdp_rate": s.stdp_rate,
                    "stdp_tau": s.stdp_tau,
                }
                for s in self._synapses
            ],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def load(self, path: str) -> None:
        """Load network state previously written by :meth:`save`."""

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.neurons.clear()
        self._incoming.clear()
        self.layers.clear()
        self._synapses.clear()

        self.time = data.get("time", 0.0)
        for nd in data.get("neurons", []):
            activation = nd.get("activation")
            act = activation if activation in _ACTIVATIONS else None
            self.add_neuron(
                nd["id"],
                bias=nd.get("bias", 0.0),
                activation=act,
                layer=nd.get("layer", 0),
                kind=nd.get("kind", "excitatory"),
                spike_threshold=nd.get("spike_threshold", 1.0),
                refractory=nd.get("refractory", 0.0),
            )
            neuron = self.neurons[nd["id"]]
            neuron.value = nd.get("value", 0.0)
            neuron.last_spike = nd.get("last_spike")

        for sd in data.get("synapses", []):
            self.connect(
                sd["pre"],
                sd["post"],
                weight=sd.get("weight", 1.0),
                learning_rate=sd.get("learning_rate", 0.0),
                stdp_rate=sd.get("stdp_rate", 0.0),
                stdp_tau=sd.get("stdp_tau", 1.0),
            )

