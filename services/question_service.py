import json
import os
import re
from pathlib import Path
from typing import List


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'


def _class_level_aliases(class_level: str) -> List[str]:
    if class_level == 'dropper':
        return ['dropper', 'droppers']
    return [class_level]


def get_available_sets(class_level, stream):
    aliases = _class_level_aliases(class_level)
    stream_name = stream or 'general'
    found_sets = set()

    for alias in aliases:
        pattern = re.compile(rf'^questions_{re.escape(alias)}_{re.escape(stream_name)}_([a-z])\\.json$')
        try:
            for name in os.listdir(DATA_DIR):
                match = pattern.match(name)
                if match:
                    found_sets.add(match.group(1))
        except FileNotFoundError:
            pass

    if found_sets:
        return sorted(found_sets)
    return ['a', 'b', 'c', 'd']


def load_questions(class_level, stream, set_name):
    aliases = _class_level_aliases(class_level)
    stream_name = stream or 'general'

    for alias in aliases:
        set_path = DATA_DIR / f'questions_{alias}_{stream_name}_{set_name}.json'
        if set_path.exists():
            with open(set_path, 'r', encoding='utf-8') as fh:
                return json.load(fh)

    for alias in aliases:
        shared_path = DATA_DIR / f'questions_{alias}_{stream_name}.json'
        if shared_path.exists():
            with open(shared_path, 'r', encoding='utf-8') as fh:
                return json.load(fh)

    available_sets = get_available_sets(class_level, stream_name)
    for fallback_set in available_sets:
        for alias in aliases:
            fallback_path = DATA_DIR / f'questions_{alias}_{stream_name}_{fallback_set}.json'
            if fallback_path.exists():
                with open(fallback_path, 'r', encoding='utf-8') as fh:
                    return json.load(fh)

    return []
