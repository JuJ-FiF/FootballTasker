"""Validierung sowie JSON-Import und -Export der FootballTasker-Daten."""

from __future__ import annotations

from Models.models import Player, Preset, Task

FORMAT_NAME = "footballtasker-data"
FORMAT_VERSION = 1


def create_export_data(players: list[Player], tasks: list[Task], presets: list[Preset], groups: list[dict]) -> dict:
    """Erstellt einen portablen Export ohne Zugangsdaten oder lokale Einstellungen."""
    return {
        "format": FORMAT_NAME,
        "format_version": FORMAT_VERSION,
        "players": [player.to_dict() for player in players],
        "tasks": [task.to_dict() for task in tasks],
        "presets": [preset.to_dict() for preset in presets],
        "groups": groups,
    }


def build_import_data(data: object) -> tuple[list[Player], list[Task], list[Preset], list[dict]]:
    """Prüft und baut alle importierten Objekte, bevor App-Daten geändert werden."""
    if not isinstance(data, dict) or data.get("format") != FORMAT_NAME:
        raise ValueError("Die Datei ist kein FootballTasker-Datenexport.")
    if data.get("format_version") != FORMAT_VERSION:
        raise ValueError("Diese Exportversion wird nicht unterstützt.")

    sections = ("players", "tasks", "presets", "groups")
    for section in sections:
        if not isinstance(data.get(section), list):
            raise ValueError(f"Der Bereich „{section}“ fehlt oder ist keine Liste.")
    if any(not isinstance(item, dict) for section in sections for item in data[section]):
        raise ValueError("Die Datei enthält einen ungültigen Datensatz.")
    for preset in data["presets"]:
        if not isinstance(preset.get("tasks"), list) or any(not isinstance(item, dict) for item in preset["tasks"]):
            raise ValueError("Ein Preset enthält eine ungültige Aufgabenliste.")
    players = [Player.from_dict(item) for item in data["players"]]
    tasks = [Task.from_dict(item) for item in data["tasks"]]
    presets = [Preset.from_dict(item) for item in data["presets"]]
    groups = data["groups"]

    _validate_names("Spieler", [player.name for player in players])
    _validate_names("Aufgaben", [task.name for task in tasks])
    _validate_names("Presets", [preset.name for preset in presets])
    for task in tasks:
        _validate_task(task)
    for preset in presets:
        if not preset.name.strip():
            raise ValueError("Ein Preset hat keinen Namen.")
        for task in preset.tasks:
            _validate_task(task)
    return players, tasks, presets, groups


def _validate_names(kind: str, names: list[str]) -> None:
    cleaned = [name.strip().casefold() for name in names]
    if any(not name for name in cleaned):
        raise ValueError(f"Mindestens ein Eintrag bei „{kind}“ hat keinen Namen.")
    if len(cleaned) != len(set(cleaned)):
        raise ValueError(f"Der Export enthält doppelte Namen bei „{kind}“.")


def _validate_task(task: Task) -> None:
    if not task.name.strip() or task.min < 1 or task.max < task.min:
        raise ValueError(f"Die Aufgabe „{task.name}“ hat ungültige Angaben.")
    if task.prio not in {"Niedrig", "Mittel", "Hoch"}:
        raise ValueError(f"Die Aufgabe „{task.name}“ hat eine ungültige Priorität.")
