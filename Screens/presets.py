"""Verwaltung von Presets aus Aufgaben."""

import flet as ft
from .common import entity_list


class PresetsScreen:
    def __init__(self, app):
        self.app = app

    def build(self):
        return entity_list(
            self.app, "Presets", "Häufige Aufgabensätze für die Verteilung zusammenstellen.",
            self.app.presets, self.app.preset_editor, ft.Icons.LIST_ALT,
            "Ein Preset bündelt die Aufgaben für eine Verteilung.",
            self.app.describe,
        )
