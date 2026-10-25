"""Spielerverwaltung."""

import flet as ft
from .common import entity_list


class PlayersScreen:
    def __init__(self, app):
        self.app = app

    def build(self):
        return entity_list(
            self.app, "Spieler", "Kader, Rückennummern und SpielerPlus-Namen verwalten.",
            self.app.players, self.app.player_editor, ft.Icons.PEOPLE_OUTLINE,
            "Lege Spieler mit Name, Rückennummer und optionalem SpielerPlus-Namen an.",
            self.app.describe,
        )
