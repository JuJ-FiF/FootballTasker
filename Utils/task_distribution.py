"""Automatische Verteilung von Spielern auf Aufgaben."""

from __future__ import annotations

import random

from Models.models import Player, Task


def distribute_tasks(players: list[Player], tasks: list[Task]) -> dict[str, list[str]]:
    available = [player.name for player in players if player.gets_task]
    random.shuffle(available)
    ordered = sorted(tasks, key=lambda task: {"Hoch": 0, "Mittel": 1, "Niedrig": 2}.get(task.prio, 2))
    assigned = {task.name: [] for task in ordered}
    for limit in ("min", "max"):
        for task in ordered:
            while available and len(assigned[task.name]) < getattr(task, limit):
                assigned[task.name].append(available.pop())
    return {
        task.name: sorted(assigned[task.name], key=str.casefold)
        for task in sorted(ordered, key=lambda item: item.name.casefold())
    }


