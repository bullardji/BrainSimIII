import sys
import time
from pathlib import Path
import sys
import time

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from network import Network


def test_simple_propagation():
    net = Network()
    net.add_neuron("a")
    net.add_neuron("b")
    net.connect("a", "b", 0.5)
    net.set_input("a", 1.0)
    net.step()
    assert net.neurons["b"].value == 0.5


def test_simultaneous_update():
    net = Network()
    net.add_neuron("a")
    net.add_neuron("b")
    net.connect("a", "b", 1.0)
    net.connect("b", "a", 1.0)
    net.set_input("a", 1.0)
    net.set_input("b", 0.0)
    net.step()
    assert net.neurons["b"].value == 1.0
    assert net.neurons["a"].value == 0.0


def test_layered_step():
    net = Network()
    net.add_neuron("a", layer=0)
    net.add_neuron("b", layer=1)
    net.add_neuron("c", layer=2)
    net.connect("a", "b", 1.0)
    net.connect("b", "c", 1.0)
    net.set_input("a", 1.0)
    net.step()
    assert net.neurons["b"].value == 1.0
    assert net.neurons["c"].value == 1.0


def test_async_run_and_stop():
    net = Network()
    net.add_neuron("a")
    net.add_neuron("b")
    net.connect("a", "b", 1.0)
    net.set_input("a", 1.0)
    net.run(tick_rate=100)
    try:
        time.sleep(0.05)
    finally:
        net.stop()
    assert net.neurons["b"].value == 1.0


def test_hebbian_learning():
    net = Network()
    net.add_neuron("a")
    net.add_neuron("b")
    net.connect("a", "b", weight=0.5, learning_rate=0.1)
    net.set_input("a", 1.0)
    net.step()
    syn = net._incoming["b"][0]
    assert syn.weight == pytest.approx(0.55)


def test_inhibitory_neuron():
    net = Network()
    net.add_neuron("a", kind="inhibitory")
    net.add_neuron("b")
    net.connect("a", "b", 1.0)
    net.set_input("a", 1.0)
    net.step()
    assert net.neurons["b"].value == -1.0


def test_global_clock_and_tick():
    net = Network()
    net.add_neuron("a")
    net.step(0.05)
    net.step(0.05)
    assert net.time == pytest.approx(0.1)


def test_pause_and_resume():
    net = Network()
    net.add_neuron("a")
    net.add_neuron("b")
    net.connect("a", "b", 1.0)
    net.set_input("a", 1.0)
    net.run(tick_rate=50)
    try:
        time.sleep(0.05)
        net.pause()
        val = net.neurons["b"].value
        time.sleep(0.05)
        assert net.neurons["b"].value == val
        net.resume()
        time.sleep(0.05)
    finally:
        net.stop()
    assert net.neurons["b"].value >= 1.0


def test_stdp_learning():
    net = Network()
    net.add_neuron("a")  # pre
    net.add_neuron("b")  # post
    net.add_neuron("drive")  # external driver for b
    net.connect("drive", "b", 1.0)
    syn = net.connect("a", "b", weight=0.5, stdp_rate=0.1, stdp_tau=1.0)
    # pre fires before post
    net.set_input("a", 1.0)
    net.set_input("drive", 0.0)
    net.step(0.1)  # a fires, b should not
    net.set_input("a", 0.0)
    net.set_input("drive", 1.0)
    net.step(0.1)  # b fires due to driver
    w1 = syn.weight
    assert w1 > 0.5
    # post before pre
    net.set_input("drive", 1.0)
    net.set_input("a", 0.0)
    net.step(0.1)  # b fires first
    net.set_input("drive", 0.0)
    net.set_input("a", 1.0)
    net.step(0.1)  # a fires later
    assert syn.weight < w1


def test_spiking_neuron_with_refractory():
    net = Network()
    net.add_neuron("input")
    net.add_neuron("spike", kind="spiking", spike_threshold=0.5, refractory=0.2)
    net.connect("input", "spike", 1.0)
    net.set_input("input", 1.0)
    net.step(0.1)
    assert net.neurons["spike"].value == 1.0
    net.set_input("input", 1.0)
    net.step(0.1)
    assert net.neurons["spike"].value == 0.0
    net.set_input("input", 0.0)
    net.step(0.2)
    net.set_input("input", 1.0)
    net.step(0.1)
    assert net.neurons["spike"].value == 1.0


def test_network_save_and_load(tmp_path):
    net = Network()
    net.add_neuron("a", bias=0.1)
    net.add_neuron("b", layer=1)
    net.connect("a", "b", weight=0.5, learning_rate=0.05)
    net.set_input("a", 1.0)
    net.step()
    path = tmp_path / "net.json"
    net.save(path)
    net.step()
    expected = net.neurons["b"].value

    net2 = Network()
    net2.load(path)
    assert net2.time == pytest.approx(net.time - 1.0)  # time before extra step
    assert net2.neurons["a"].bias == pytest.approx(0.1)
    assert net2.neurons["a"].value == pytest.approx(1.0)
    assert net2._incoming["b"][0].weight == pytest.approx(0.525)
    net2.step()
    assert net2.neurons["b"].value == pytest.approx(expected)


def test_disconnect_and_remove():
    net = Network()
    net.add_neuron("a")
    net.add_neuron("b")
    net.connect("a", "b", 1.0)
    net.disconnect("a", "b")
    assert net._incoming["b"] == []
    net.connect("a", "b", 1.0)
    net.remove_neuron("a")
    assert "a" not in net.neurons
    assert net._incoming["b"] == []


def test_tick_rate_change():
    net = Network()
    net.add_neuron("a")
    net.run(tick_rate=20)
    try:
        time.sleep(0.11)
        net.set_tick_rate(100)
        time.sleep(0.05)
    finally:
        net.stop()
    # Allow generous tolerance due to scheduling jitter
    assert 0.12 <= net.time <= 0.18


def test_clear_resets_state():
    net = Network()
    net.add_neuron("a")
    net.add_neuron("b")
    net.connect("a", "b")
    net.step()
    assert net.time > 0
    net.clear()
    assert net.neurons == {}
    assert net.time == 0.0