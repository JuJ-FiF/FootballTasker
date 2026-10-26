"""Auswahl der anwesenden Spieler für die Verteilung."""

import flet as ft

from .common import empty_state, page_heading


class AllocationScreen:
    def __init__(self, app):
        self.app = app

    def build(self):
        if not self.app.players:
            return ft.Column(
                [
                    page_heading("Aufgabenverteilung", "Spieler auswählen und die Verteilung als PDF speichern."),
                    empty_state(
                        ft.Icons.PEOPLE_OUTLINE,
                        "Noch keine Spieler",
                        "Füge zuerst Spieler hinzu.",
                        ft.FilledButton("Spieler verwalten", on_click=lambda _: self.app.change_screen("pl_main")),
                    ),
                ],
                expand=True,
                spacing=20,
            )

        players = sorted(self.app.players, key=lambda player: player.name.casefold())
        checks = []
        for player in players:
            plus_name = " ".join(player.player_plus_name.split()).casefold()
            selected = (
                player.name in self.app.manual_presence_selection
                if self.app.manual_presence_selection is not None
                else plus_name in self.app.presence
                if self.app.presence_loaded
                else not self.app.presence_attempted
            )
            checks.append(ft.Checkbox(value=selected, data=player))

        count = ft.Text()

        def update_count(_=None):
            count.value = f"{sum(bool(control.value) for control in checks)} von {len(checks)} ausgewählt"
            self.app.manual_presence_selection = {
                control.data.name for control in checks if control.value
            }
            self.app.page.update()

        def select_all(_=None):
            selected = not all(bool(control.value) for control in checks)
            for control in checks:
                control.value = selected
            update_count()

        for control in checks:
            control.on_change = update_count
        update_count()

        rows = [
            ft.Card(
                variant=ft.CardVariant.FILLED,
                elevation=0,
                content=ft.Container(
                    height=56,
                    padding=ft.Padding.symmetric(horizontal=14, vertical=2),
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.PEOPLE_OUTLINE, color=ft.Colors.PRIMARY),
                            ft.Text(control.data.name, expand=True),
                            control,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                ),
            )
            for control in checks
        ]
        source = self.app.presence_status
        status_color = ft.Colors.ERROR if self.app.presence_status_error else ft.Colors.ON_SURFACE_VARIANT
        info = ft.Card(
            variant=ft.CardVariant.FILLED,
            elevation=0,
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.ERROR_OUTLINE if self.app.presence_status_error else ft.Icons.INFO_OUTLINE,
                                    color=status_color,
                                ),
                                ft.Text(source, expand=True, color=status_color),
                            ],
                            spacing=12,
                        ),
                        ft.Row(
                            [ft.OutlinedButton("SpielerPlus laden", icon=ft.Icons.SYNC, on_click=self.app.refresh_presence)],
                            alignment=ft.MainAxisAlignment.END,
                        ),
                    ],
                    spacing=10,
                ),
            ),
        )

        return ft.Column(
            [
                page_heading("Aufgabenverteilung", "Anwesende Spieler auswählen und eine PDF-Verteilung erstellen."),
                info,
                ft.Row(
                    [count, ft.TextButton("Alle auswählen / abwählen", on_click=select_all)],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    wrap=True,
                ),
                ft.Container(
                    expand=True,
                    content=ft.ListView(controls=rows, expand=True, spacing=6),
                ),
                ft.Row(
                    [ft.FilledButton(
                        "Weiter zur PDF",
                        icon=ft.Icons.ARROW_FORWARD,
                        on_click=lambda _: self.app.create_player_distribution(
                            [item.data for item in checks if item.value]
                        ),
                    )],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            expand=True,
            spacing=12,
        )
