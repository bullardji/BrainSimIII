import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from network import Network
from xml_utils import load_xml


def test_network_xml_roundtrip(tmp_path):
    net = Network()
    net.add_neuron("A")
    net.add_neuron("B")
    net.connect("A", "B", weight=0.5)
    path = tmp_path / "net.xml"
    net.save_xml(str(path))

    net2 = Network()
    net2.load_xml(str(path))
    assert set(net2.neurons.keys()) == {"A", "B"}
    assert net2._incoming["B"][0].weight == 0.5
    # verify file can be parsed with generic loader too
    data = load_xml(str(path))
    assert "neurons" in data
