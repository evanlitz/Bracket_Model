import json
from pathlib import Path

_MAP_PATH = Path(__file__).parent.parent / 'config' / 'name_map.json'

# Load once at import time; skip the _comment key.
_NAME_MAP: dict[str, str] = {
    k: v
    for k, v in json.loads(_MAP_PATH.read_text(encoding='utf-8')).items()
    if not k.startswith('_')
}


def normalize_name(name: str) -> str:
    """Return the canonical team name for *name*.

    Strips surrounding whitespace, then looks up the result in name_map.json.
    If no mapping exists the stripped name is returned unchanged.
    Both KenPom and bracket loaders call this before any join.
    """
    name = name.strip()
    return _NAME_MAP.get(name, name)
