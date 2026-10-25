"""Aufgabenverwaltung."""

import flet as ft
from .common import entity_list


class TasksScreen:
    def __init__(self, app):
        self.app = app

    def build(self):
        return entity_list(
            self.app, "Aufgaben", "Aufgaben mit Mindest- und Maximalbesetzung festlegen.",
            self.app.tasks, self.app.task_editor, ft.Icons.CHECKLIST_OUTLINED,
            "Lege Aufgaben an und bestimme, wie viele Spieler mindestens und höchstens zugeteilt werden.",
            self.app.describe,
        )
