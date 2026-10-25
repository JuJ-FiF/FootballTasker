"""Datenmodelle für Spieler, Aufgaben und Presets."""

from dataclasses import dataclass, field


@dataclass
class Player:
    name: str
    number: int | None = None
    gets_task: bool = True
    player_plus_name: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        number = data.get("number")
        return cls(
            name=str(data.get("name", "")),
            number=int(number) if number not in (None, "") else None,
            gets_task=bool(data.get("gets_task", True)),
            player_plus_name=str(data.get("player_plus_name", "")),
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "player_plus_name": self.player_plus_name,
            "number": self.number,
            "gets_task": self.gets_task,
        }


@dataclass
class Task:
    name: str
    min: int = 1
    max: int = 3
    prio: str = "Niedrig"

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            str(data.get("name", "")),
            int(data.get("min", 1)),
            int(data.get("max", 3)),
            str(data.get("prio", "Niedrig")),
        )

    def to_dict(self) -> dict:
        return {"name": self.name, "min": self.min, "max": self.max, "prio": self.prio}


@dataclass
class Preset:
    name: str
    tasks: list[Task] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Preset":
        return cls(str(data.get("name", "")), [Task.from_dict(task) for task in data.get("tasks", [])])

    def to_dict(self) -> dict:
        return {"name": self.name, "tasks": [task.to_dict() for task in self.tasks]}
