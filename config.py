"""Chargement/sauvegarde de projects.json."""

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "projects.json"

DEFAULT_CONFIG = {"last_project": None, "projects": []}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_CONFIG)
    data.setdefault("last_project", None)
    data.setdefault("projects", [])
    return data


def save_config(config: dict) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_project(config: dict, name: str) -> dict | None:
    for project in config["projects"]:
        if project["name"] == name:
            return project
    return None


def set_last_project(config: dict, name: str) -> None:
    config["last_project"] = name
    save_config(config)
