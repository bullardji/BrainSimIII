import argparse
import json
from pathlib import Path

from modules.module_handler import ModuleHandler
from network import Network
from uks.thing_labels import ThingLabels
from xml_utils import load_xml


def load_project(path: Path, network: Network, handler: ModuleHandler) -> None:
    if path.suffix.lower() == ".xml":
        data = load_xml(path)
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
    network.from_dict(data.get("network", {}))
    handler.the_uks.from_dict(data.get("uks", {}))
    handler.load_active(data.get("modules", []))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BrainSimIII console launcher")
    parser.add_argument("project", nargs="?", help="Project file to load")
    parser.add_argument("--ticks", type=int, default=0,
                        help="Number of simulation ticks to run before exiting")
    args = parser.parse_args(argv)

    handler = ModuleHandler()
    network = Network()
    uks = handler.the_uks

    if args.project:
        load_project(Path(args.project), network, handler)
    else:
        ThingLabels.clear_label_list()

    for _ in range(args.ticks):
        handler.fire_modules()
        network.step()

    network.stop()
    handler.reset_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
