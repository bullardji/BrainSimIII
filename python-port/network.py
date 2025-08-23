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
from typing import Any, Callable, Dict, List, Optional

try:  # optional vectorised maths
    import numpy as np  # type: ignore
    _HAVE_NUMPY = True
except Exception:  # pragma: no cover - optional dependency
    _HAVE_NUMPY = False

UDP_RECEIVE_PORT = 3333
UDP_SEND_PORT = 3333

TCP_PORT = 54321
SUBSCRIPTION_PORT = 9090
AUDIO_PORT = 666

# globals used for device pairing similar to the C# Network.cs helper
pod_paired: bool = False
the_tcp_stream_in: Optional[socket.socket] = None
the_tcp_stream_out: Optional[socket.socket] = None
_broadcast_address: Optional[str] = None


def _create_udp_socket(broadcast: bool = False) -> socket.socket:
    """Create a UDP socket optionally configured for broadcast."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if broadcast:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    return s


def udp_send(message: str, ip: str, port: int) -> None:
    """Send *message* to ``ip``/``port`` via UDP."""
    data = message.encode("utf-8")
    with _create_udp_socket() as s:
        s.sendto(data, (ip, port))


def udp_setup_send(message: str, ip: str, port: int, *, local_port: int = 9090) -> bool:
    """Send *message* from a specific local UDP ``local_port``.

    This mirrors the ``UDP_Setup_Send`` helper in the C# code which is used
    during hardware pairing.  Returns ``True`` if the datagram was sent.
    """
    try:
        data = message.encode("utf-8")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind(("", local_port))
            s.sendto(data, (ip, port))
        return True
    except OSError:
        return False


def set_broadcast_address() -> str:
    """Determine the local network broadcast address.

    The implementation mimics the simplistic approach used by the C# project
    which replaces the final octet of the first IPv4 address with ``255``.
    The result is cached and returned.
    """
    global _broadcast_address
    if _broadcast_address:
        return _broadcast_address
    host = socket.gethostbyname_ex(socket.gethostname())[2]
    for ip in host:
        if "." in ip:
            parts = ip.split(".")
            _broadcast_address = ".".join(parts[:3] + ["255"])
            return _broadcast_address
    raise RuntimeError("No IPv4 address found for broadcast computation")


def broadcast(message: str, port: int = UDP_SEND_PORT, address: Optional[str] = None) -> None:
    """Send *message* as a UDP broadcast."""
    data = message.encode("utf-8")
    addr = address or set_broadcast_address()
    with _create_udp_socket(broadcast=True) as s:
        s.sendto(data, (addr, port))


# ---------------------------------------------------------------------------
# TCP helpers
# ---------------------------------------------------------------------------


def tcp_listen(port: int = TCP_PORT) -> socket.socket:
    """Return a listening TCP socket bound to *port*.

    The caller is responsible for closing the returned socket when finished.
    """

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("", port))
    server.listen(1)
    return server


def tcp_connect(host: str, port: int = TCP_PORT, *, timeout: float = 5.0) -> socket.socket:
    """Connect to a TCP server and return the connected socket."""

    client = socket.create_connection((host, port), timeout=timeout)
    return client


def tcp_accept(server: socket.socket, *, timeout: float = 15.0) -> socket.socket:
    """Accept a connection from ``server`` and return the client socket."""

    server.settimeout(timeout)
    conn, _ = server.accept()
    return conn


def tcp_send(sock: socket.socket, message: str) -> None:
    """Send *message* over the TCP connection ``sock``."""

    data = (message + "\n").encode("utf-8")
    sock.sendall(data)


def tcp_receive(sock: socket.socket, bufsize: int = 4096) -> str:
    """Receive a line of text from ``sock``."""

    data = sock.recv(bufsize)
    return data.decode("utf-8")


def init_tcp(pod_ip: str, port: int = TCP_PORT, timeout: float = 15.0) -> bool:
    """Listen for a TCP connection from ``pod_ip`` and establish streams.

    This mirrors the pairing handshake used by hardware pods.  A listening
    socket is opened on ``port`` and a connection from the device is awaited up
    to ``timeout`` seconds.  ``pod_paired`` is set to ``True`` on success and
    the incoming/outgoing sockets are stored for later use by
    :func:`send_string_to_pod_tcp`.
    """
    global pod_paired, the_tcp_stream_in, the_tcp_stream_out
    server = tcp_listen(port)
    server.settimeout(timeout)
    try:
        conn, addr = server.accept()
    except Exception:
        server.close()
        return False
    if addr[0] != pod_ip and pod_ip != "0.0.0.0":
        conn.close()
        server.close()
        return False
    the_tcp_stream_in = conn
    the_tcp_stream_out = conn
    pod_paired = True
    server.close()
    return True


def send_string_to_pod_tcp(message: str) -> None:
    """Send ``message`` over the paired TCP connection if available."""
    if not pod_paired or the_tcp_stream_out is None:
        return
    try:
        tcp_send(the_tcp_stream_out, message)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def http_get(url: str, *, timeout: float = 2.0) -> str:
    """Return the body of ``url`` via a simple HTTP GET request."""

    from urllib.request import urlopen

    with urlopen(url, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def http_post(url: str, data: str, *, timeout: float = 2.0) -> str:
    """Send ``data`` to ``url`` via HTTP POST and return the response body."""

    from urllib.request import Request, urlopen

    req = Request(url, data=data.encode("utf-8"), method="POST")
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


# ---------------------------------------------------------------------------
# Audio UDP helpers
# ---------------------------------------------------------------------------


def audio_broadcast(payload: bytes, port: int = AUDIO_PORT, address: Optional[str] = None) -> None:
    """Broadcast raw ``payload`` bytes over UDP on ``port``.

    Used by audio modules which stream waveform samples.  ``address`` defaults to
    the broadcast address but may be a specific IP for testing.
    """

    addr = address or "<broadcast>"
    with _create_udp_socket(broadcast=address is None) as s:
        s.sendto(payload, (addr, port))


# ---------------------------------------------------------------------------
# Subscription socket
# ---------------------------------------------------------------------------


class SubscriptionServer:
    """Simple UDP based publish/subscribe message router.

    Clients subscribe by sending the literal string ``"SUBSCRIBE"`` to the
    server's port.  Subsequent datagrams sent to the server are forwarded to all
    subscribed clients.
    """

    def __init__(self, port: int = SUBSCRIPTION_PORT) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", port))
        self.port = self.sock.getsockname()[1]
        self.subscribers: set[tuple[str, int]] = set()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while self._running:
            try:
                data, addr = self.sock.recvfrom(65535)
            except OSError:
                break
            if data == b"SUBSCRIBE":
                self.subscribers.add(addr)
            else:
                for sub in list(self.subscribers):
                    try:
                        self.sock.sendto(data, sub)
                    except OSError:
                        self.subscribers.discard(sub)

    def stop(self) -> None:
        self._running = False
        try:
            # send dummy packet to wake recvfrom
            self.sock.sendto(b"", ("127.0.0.1", self.port))
        except OSError:
            pass
        self.sock.close()
        self._thread.join()


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
        self.tick_rate: float = 1.0
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

    def disconnect(self, pre: str, post: str) -> None:
        """Remove the synapse from ``pre`` to ``post`` if present."""

        with self._lock:
            self._incoming[post] = [s for s in self._incoming.get(post, []) if not (s.pre == pre and s.post == post)]
            self._synapses = [s for s in self._synapses if not (s.pre == pre and s.post == post)]

    def remove_neuron(self, neuron_id: str) -> None:
        """Remove ``neuron_id`` and all connected synapses."""

        if neuron_id not in self.neurons:
            return
        with self._lock:
            del self.neurons[neuron_id]
            del self._incoming[neuron_id]
            for syn_list in self._incoming.values():
                syn_list[:] = [s for s in syn_list if s.pre != neuron_id]
            self._synapses = [s for s in self._synapses if s.pre != neuron_id and s.post != neuron_id]
            for ids in self.layers.values():
                if neuron_id in ids:
                    ids.remove(neuron_id)

    def clear(self) -> None:
        """Remove all neurons and synapses, resetting time to zero."""

        with self._lock:
            self.neurons.clear()
            self._incoming.clear()
            self.layers.clear()
            self._synapses.clear()
            self.time = 0.0

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

        with self._lock:
            self.tick_rate = tick_rate
            self._dt = 1.0 / tick_rate
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

    def set_tick_rate(self, tick_rate: float) -> None:
        """Change the tick rate used by the asynchronous update loop."""

        with self._lock:
            self.tick_rate = tick_rate
            self._dt = 1.0 / tick_rate

    # -- persistence -------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON‑serialisable representation of the network."""

        return {
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

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Populate the network using data produced by :meth:`to_dict`."""

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

    def save(self, path: str) -> None:
        """Serialise the network to *path* in JSON format."""

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f)

    def load(self, path: str) -> None:
        """Load network state previously written by :meth:`save`."""

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.from_dict(data)

    # -- XML persistence --------------------------------------------
    def save_xml(self, path: str) -> None:
        """Save the network to *path* in XML format."""
        from xml_utils import save_xml

        save_xml(path, self.to_dict(), root_tag="Network")

    def load_xml(self, path: str) -> None:
        """Load network state from an XML file."""
        from xml_utils import load_xml

        data = load_xml(path)
        self.from_dict(data)


__all__ = [
    "broadcast",
    "udp_send",
    "udp_setup_send",
    "tcp_listen",
    "tcp_connect",
    "tcp_accept",
    "tcp_send",
    "tcp_receive",
    "init_tcp",
    "send_string_to_pod_tcp",
    "http_get",
    "http_post",
    "audio_broadcast",
    "SubscriptionServer",
    "Network",
]

