"""Simple XML persistence helpers for the BrainSimIII Python port.

These utilities convert between nested dictionaries/lists and XML documents.
The aim is to provide a lightweight mirror of the C# `XmlFile` helper so that
projects can be saved to and restored from XML as well as JSON.
"""
from __future__ import annotations

from xml.etree.ElementTree import Element, ElementTree
from typing import Any, Dict


def _dict_to_xml(key: str, value: Any) -> Element:
    elem = Element(key)
    if isinstance(value, dict):
        for k, v in value.items():
            elem.append(_dict_to_xml(str(k), v))
    elif isinstance(value, list):
        for item in value:
            elem.append(_dict_to_xml("item", item))
    else:
        elem.text = str(value)
    return elem


def _xml_to_dict(elem: Element) -> Any:
    children = list(elem)
    if not children:
        text = (elem.text or "").strip()
        if text.lower() in {"true", "false"}:
            return text.lower() == "true"
        try:
            if "." in text:
                return float(text)
            return int(text)
        except ValueError:
            return text
    if all(c.tag == "item" for c in children):
        return [_xml_to_dict(c) for c in children]
    result: Dict[str, Any] = {}
    for child in children:
        value = _xml_to_dict(child)
        if child.tag in result:
            if not isinstance(result[child.tag], list):
                result[child.tag] = [result[child.tag]]
            result[child.tag].append(value)
        else:
            result[child.tag] = value
    return result


def save_xml(path: str, data: Dict[str, Any], root_tag: str = "BrainSimProject") -> None:
    """Serialise ``data`` to ``path`` using ``root_tag`` as the document root."""
    root = _dict_to_xml(root_tag, data)
    ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def load_xml(path: str) -> Dict[str, Any]:
    """Load and return a dictionary previously written by :func:`save_xml`."""
    tree = ElementTree()
    tree.parse(path)
    return _xml_to_dict(tree.getroot())


__all__ = ["save_xml", "load_xml"]
