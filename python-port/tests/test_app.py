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

    def delete(self, *args, **kwargs):
        pass

    application = app.BrainSimApp()

    # populate some data
    application.network.add_neuron("A")
    application.network.add_neuron("B")
    application.network.connect("A", "B", 0.5)
    application.uks.add_relationship("A", "is", "B")

    project = tmp_path / "proj.json"
    application.save_project(str(project))
    assert application.mru[0] == project

    # reset everything
    application.new_project()
    assert not application.network.neurons
    assert all(t.Label != "A" for t in application.uks.UKSList)

    # reload
    application.open_project(str(project))
    assert "A" in application.network.neurons
    assert any(t.Label == "A" for t in application.uks.UKSList)
