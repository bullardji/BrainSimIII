import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[1]))

import app


class DummyMenu:
    def __init__(self, master=None, tearoff=0):
        self.master = master
        self.commands = []

    def add_command(self, **kwargs):
        self.commands.append(kwargs)

    def add_separator(self):
        pass

    def add_cascade(self, **kwargs):
        pass

    def config(self, **kwargs):
        pass


class DummyRoot:
    def __init__(self):
        self.menu = None
        self.titled = None
        self.tk = self

    def title(self, t):
        self.titled = t

    def config(self, **kwargs):
        self.menu = kwargs.get("menu")

    def destroy(self):
        pass


class DummyWidget:
    def __init__(self, *args, **kwargs):
        pass

    def pack(self, *args, **kwargs):
        pass


@patch("tkinter.Button", DummyWidget)
@patch("tkinter.Frame", DummyWidget)
@patch("tkinter.PhotoImage", lambda *a, **k: object())
@patch("tkinter.Menu", DummyMenu)
@patch("tkinter.Tk", DummyRoot)
def test_save_and_load_project(tmp_path):
    application = app.BrainSimApp()

    # populate some data
    application.network.add_neuron("A")
    application.network.add_neuron("B")
    application.network.connect("A", "B", 0.5)
    application.uks.add_relationship("A", "is", "B")

    project = tmp_path / "proj.json"
    application.save_project(str(project))

    # reset everything
    application.new_project()
    assert not application.network.neurons
    assert all(t.Label != "A" for t in application.uks.UKSList)

    # reload
    application.open_project(str(project))
    assert "A" in application.network.neurons
    assert any(t.Label == "A" for t in application.uks.UKSList)
