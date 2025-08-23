"""Module scaffolding generator for BrainSimIII Python port.

Creates a new module file with a basic skeleton extending ``ModuleBase``.
"""
from __future__ import annotations

from pathlib import Path
import re
from typing import Optional

TEMPLATE = """from modules import ModuleBase, ModuleDescription


class Module{class_name}(ModuleBase):
    '''Auto-generated module {class_name}.'''
    description = ModuleDescription(
        name="{class_name}",
        description="Auto-generated module {class_name}"
    )

    def step(self):
        '''Override with module behavior.'''
        pass
"""


def _snake_case(name: str) -> str:
    """Convert ``CamelCase`` or mixed names to ``snake_case``."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    snake = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).replace("-", "_")
    return snake.lower()


def create_module(name: str, dest: Path | str, *, exist_ok: bool = False) -> Path:
    """Create a new module skeleton.

    Parameters
    ----------
    name:
        The base name for the module (CamelCase recommended).
    dest:
        Destination directory for the generated file.
    exist_ok:
        If ``False`` (default), raise ``FileExistsError`` if the file exists.

    Returns
    -------
    Path to the created module file.
    """
    dest_path = Path(dest)
    dest_path.mkdir(parents=True, exist_ok=True)
    module_filename = f"module_{_snake_case(name)}.py"
    file_path = dest_path / module_filename
    if file_path.exists() and not exist_ok:
        raise FileExistsError(file_path)
    file_content = TEMPLATE.format(class_name=name)
    file_path.write_text(file_content)
    return file_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate a BrainSimIII module skeleton")
    parser.add_argument("name", help="Module class name (CamelCase)")
    parser.add_argument("dest", nargs="?", default=".", help="Destination directory")
    args = parser.parse_args()
    path = create_module(args.name, Path(args.dest))
    print(f"Created {path}")
