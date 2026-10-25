"""Flet-Oberfläche für die FootballTasker-App."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import re
from datetime import datetime
from pathlib import Path

import flet as ft

from Screens.allocation import AllocationScreen
from Screens.players import PlayersScreen
from Screens.presets import PresetsScreen
from Screens.registry import SCREEN_DEFINITIONS
from Screens.settings import SettingsScreen
from Screens.tasks import TasksScreen
from Models.models import Player, Preset, Task
from Utils.data_store import DataStore
from Utils.pdf_export import create_pdf, save_pdf_to_documents
from Utils.playerplus import fetch_presence_with_opponent, test_playerplus_login
from Utils.task_distribution import distribute_tasks
from Utils.updater import is_android_runtime


class FootballTasksApp:
    def __init__(self, page: ft.Page):
        self.page = page
        project_dir = Path(__file__).resolve().parent
        storage_path = os.getenv("FLET_APP_STORAGE_DATA")
        self.base_dir = Path(storage_path) if storage_path else project_dir
        self._copy_seed_files(project_dir)
        self.store = DataStore(self.base_dir)
        self.players: list[Player] = []
        self.tasks: list[Task] = []
        self.presets: list[Preset] = []
        self.groups: list[dict] = []
        self.presence: set[str] = set()
        self.presence_opponent: str | None = None
        self.presence_home_away: str | None = None
        self.presence_loaded = False
        self.presence_attempted = False
        self.manual_presence_selection: set[str] | None = None
        self.presence_status = "SpielerPlus-Anwesenheit wurde noch nicht abgerufen."
        self.presence_status_error = False
        self.settings = self.store.load_settings()
        self.current = self.settings["start_tab"]["selected"]
        self.load_error = None
        self._load_data()
        self._setup_page()
        if self.load_error:
            self.message(self.load_error, error=True)
        if self.store.load_credentials():
            self.refresh_presence()

    def _copy_seed_files(self, project_dir: Path):
        if self.base_dir == project_dir:
            return
        self.base_dir.mkdir(parents=True, exist_ok=True)
        marker = self.base_dir / ".seed_data_migrated"
        if marker.exists():
            return

        seed_data = project_dir / "data.json"
        target_data = self.base_dir / "data.json"
        has_players = False
        if target_data.exists():
            try:
                has_players = bool(json.loads(target_data.read_text(encoding="utf-8")).get("players"))
            except (OSError, ValueError, AttributeError):
                has_players = False
        if seed_data.exists() and not has_players:
            if target_data.exists():
                DataStore(self.base_dir)._snapshot(("data.json",))
            shutil.copy2(seed_data, target_data)

        source_settings, target_settings = project_dir / "settings.json", self.base_dir / "settings.json"
        if source_settings.exists() and not target_settings.exists():
            shutil.copy2(source_settings, target_settings)
        marker.write_text("Ausgangsdaten geprüft.\n", encoding="utf-8")
    def _load_data(self):
        try:
            self.players, self.tasks, self.presets, self.groups = self.store.load_data()
        except (OSError, ValueError, TypeError, KeyError) as error:
            self.log(f"Datendatei konnte nicht geladen werden: {error}")
            self.load_error = "Die Datendatei konnte nicht gelesen werden. Sie wurde nicht überschrieben."

    def _setup_page(self):
        self.page.title = "FootballTasker"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.AMBER)
        self.page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.AMBER)
        self.page.padding = 0
        self.file_picker = ft.FilePicker()
        self.page.services.append(self.file_picker)
        self.wide_layout = (self.page.width or 0) >= 720
        self.page.appbar = ft.AppBar(
            leading=ft.IconButton(ft.Icons.MENU, tooltip="Navigation", on_click=self.open_drawer),
            title=ft.Row([
                ft.Icon(ft.Icons.SPORTS_SOCCER, color=ft.Colors.PRIMARY),
                ft.Text("FootballTasker", weight=ft.FontWeight.BOLD),
            ], spacing=10),
            bgcolor=ft.Colors.SURFACE,
            elevation=0,
        )
        self.page.drawer = ft.NavigationDrawer(
            width=300,
            on_change=self.drawer_change,
            controls=[
                ft.Container(padding=20, content=ft.Text("FootballTasker", size=20, weight=ft.FontWeight.BOLD)),
                ft.Divider(),
                *[ft.NavigationDrawerDestination(icon=icon, label=label) for _, label, icon in SCREEN_DEFINITIONS],
            ],
        )
        self.content_panel = ft.Container(expand=True, padding=28, bgcolor=ft.Colors.SURFACE, border_radius=20)
        self.navigation = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.SELECTED,
            min_width=84,
            bgcolor=ft.Colors.SURFACE,
            on_change=self.navigation_change,
            destinations=[ft.NavigationRailDestination(icon=icon, label=label) for _, label, icon in SCREEN_DEFINITIONS],
        )
        self.body = ft.Container(expand=True)
        self.page.add(self.body)
        self.page.on_resize = self.on_page_resize
        self.render()

    async def open_drawer(self, _):
        await self.page.show_drawer()

    async def drawer_change(self, event):
        index = event.control.selected_index
        if index is not None and 0 <= index < len(SCREEN_DEFINITIONS):
            self.change_screen(SCREEN_DEFINITIONS[index][0])
        await self.page.close_drawer()

    def navigation_change(self, event):
        index = event.control.selected_index
        if index is not None and 0 <= index < len(SCREEN_DEFINITIONS):
            self.change_screen(SCREEN_DEFINITIONS[index][0])

    def on_page_resize(self, _):
        wide = (self.page.width or 0) >= 720
        if wide != self.wide_layout:
            self.wide_layout = wide
            self.render()

    def render(self):
        screens = {
            "pla_main": AllocationScreen(self),
            "pl_main": PlayersScreen(self),
            "t_main": TasksScreen(self),
            "pr_main": PresetsScreen(self),
            "s_main": SettingsScreen(self),
        }
        index = next((i for i, item in enumerate(SCREEN_DEFINITIONS) if item[0] == self.current), 0)
        self.current = SCREEN_DEFINITIONS[index][0]
        self.navigation.selected_index = index
        self.page.drawer.selected_index = index
        self.content_panel.content = screens[self.current].build()
        self.content_panel.padding = 28 if self.wide_layout else 16
        self.body.content = (
            ft.Row([self.navigation, ft.VerticalDivider(width=1, thickness=1), self.content_panel], expand=True, spacing=0)
            if self.wide_layout else self.content_panel
        )
        self.page.update()

    def change_screen(self, name: str):
        if name in {item[0] for item in SCREEN_DEFINITIONS}:
            self.current = name
            self.render()

    def log(self, message: str):
        path = self.base_dir / "logs" / "project.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(f"{datetime.now().isoformat(timespec='seconds')} {message}\n")

    def message(self, text: str, error: bool = False):
        self.page.show_dialog(ft.SnackBar(
            ft.Text(text),
            bgcolor=ft.Colors.RED_700 if error else None,
            duration=3000,
            behavior=ft.SnackBarBehavior.FLOATING,
        ))

    def save_data(self):
        self.store.save_data(self.players, self.tasks, self.presets, self.groups)

    def describe(self, item) -> str:
        if isinstance(item, Player):
            number = f"Nr. {item.number}" if item.number is not None else "Keine Nummer"
            assignment = "Aufgaben aktiv" if item.gets_task else "ohne Aufgabe"
            plus = " · SpielerPlus verknüpft" if item.player_plus_name else ""
            return f"{number} · {assignment}{plus}"
        if isinstance(item, Task):
            return f"{item.min}–{item.max} Spieler · Priorität {item.prio}"
        return f"{len(item.tasks)} Aufgaben"

    def save_and_refresh(self):
        try:
            self.save_data()
            self.render()
        except OSError as error:
            self.message(f"Speichern fehlgeschlagen: {error}", error=True)

    def editor_dialog(self, title, fields, on_save, on_delete=None):
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Column(fields, tight=True, spacing=12, scroll=ft.ScrollMode.AUTO),
            actions=[],
        )
        actions = [
            ft.TextButton("Abbrechen", on_click=lambda _: self.close_dialog()),
            ft.FilledButton("Speichern", on_click=lambda _: on_save(dialog)),
        ]
        if on_delete:
            actions.insert(0, ft.TextButton("Löschen", on_click=lambda _: on_delete(dialog)))
        dialog.actions = actions
        self.page.show_dialog(dialog)

    def close_dialog(self):
        self.page.pop_dialog()

    def player_editor(self, player: Player | None = None):
        name = ft.TextField(label="Name", value=player.name if player else "", autofocus=True)
        number = ft.TextField(
            label="Rückennummer", value=str(player.number) if player and player.number is not None else "",
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        plus = ft.TextField(label="SpielerPlus-Name", value=player.player_plus_name if player else "")
        gets_task = ft.Checkbox(label="Bei Aufgabenverteilungen berücksichtigen", value=player.gets_task if player else True)

        def save(dialog):
            cleaned = name.value.strip()
            try:
                jersey = int(number.value) if number.value.strip() else None
            except ValueError:
                self.message("Die Rückennummer muss eine ganze Zahl sein.", error=True)
                return
            if not cleaned:
                self.message("Bitte einen Spielernamen eingeben.", error=True)
                return
            if any(item is not player and item.name.casefold() == cleaned.casefold() for item in self.players):
                self.message("Dieser Spielername ist bereits vorhanden.", error=True)
                return
            item = player or Player(cleaned)
            item.name, item.number = cleaned, jersey
            item.player_plus_name = plus.value.strip()
            item.gets_task = bool(gets_task.value)
            if player is None:
                self.players.append(item)
            self.close_dialog()
            self.save_and_refresh()

        delete = (lambda dialog: self.delete_item(dialog, player, self.players)) if player else None
        self.editor_dialog("Spieler bearbeiten" if player else "Spieler anlegen", [name, number, plus, gets_task], save, delete)

    def task_editor(self, task: Task | None = None):
        name = ft.TextField(label="Aufgabenname", value=task.name if task else "", autofocus=True)
        minimum = ft.TextField(label="Mindestanzahl Spieler", value=str(task.min) if task else "1", keyboard_type=ft.KeyboardType.NUMBER)
        maximum = ft.TextField(label="Maximalanzahl Spieler", value=str(task.max) if task else "3", keyboard_type=ft.KeyboardType.NUMBER)
        priority = ft.Dropdown(
            label="Priorität", value=task.prio if task else "Niedrig",
            options=[ft.dropdown.Option(value) for value in ("Niedrig", "Mittel", "Hoch")],
        )

        def save(dialog):
            cleaned = name.value.strip()
            try:
                low, high = int(minimum.value), int(maximum.value)
            except ValueError:
                self.message("Mindest- und Maximalanzahl müssen ganze Zahlen sein.", error=True)
                return
            if not cleaned or low < 1 or high < low:
                self.message("Name oder Spieleranzahl ist ungültig.", error=True)
                return
            if any(item is not task and item.name.casefold() == cleaned.casefold() for item in self.tasks):
                self.message("Dieser Aufgabenname ist bereits vorhanden.", error=True)
                return
            old_name = task.name if task else None
            item = task or Task(cleaned)
            item.name, item.min, item.max, item.prio = cleaned, low, high, priority.value or "Niedrig"
            if task is None:
                self.tasks.append(item)
            elif task is not None:
                for preset in self.presets:
                    for preset_task in preset.tasks:
                        if preset_task.name == old_name:
                            preset_task.name = item.name
                            preset_task.min, preset_task.max, preset_task.prio = item.min, item.max, item.prio
            self.close_dialog()
            self.save_and_refresh()

        delete = (lambda dialog: self.delete_item(dialog, task, self.tasks)) if task else None
        self.editor_dialog("Aufgabe bearbeiten" if task else "Aufgabe anlegen", [name, minimum, maximum, priority], save, delete)

    def preset_editor(self, preset: Preset | None = None):
        name = ft.TextField(label="Presetname", value=preset.name if preset else "", autofocus=True)
        selected_names = {task.name for task in preset.tasks} if preset else set()
        checks = [ft.Checkbox(label=task.name, value=task.name in selected_names, data=task) for task in self.tasks]
        task_list = ft.Column(checks or [ft.Text("Lege zuerst Aufgaben an.", color=ft.Colors.ON_SURFACE_VARIANT)], spacing=4, height=260, scroll=ft.ScrollMode.AUTO)

        def save(dialog):
            cleaned = name.value.strip()
            if not cleaned:
                self.message("Bitte einen Presetnamen eingeben.", error=True)
                return
            if any(item is not preset and item.name.casefold() == cleaned.casefold() for item in self.presets):
                self.message("Dieser Presetname ist bereits vorhanden.", error=True)
                return
            item = preset or Preset(cleaned)
            item.name = cleaned
            item.tasks = [control.data for control in checks if control.value]
            if preset is None:
                self.presets.append(item)
            self.close_dialog()
            self.save_and_refresh()

        delete = (lambda dialog: self.delete_item(dialog, preset, self.presets)) if preset else None
        self.editor_dialog("Preset bearbeiten" if preset else "Preset anlegen", [name, ft.Text("Aufgaben auswählen"), task_list], save, delete)

    def delete_item(self, dialog, item, collection):
        collection.remove(item)
        if isinstance(item, Task):
            for preset in self.presets:
                preset.tasks = [task for task in preset.tasks if task.name != item.name]
        self.close_dialog()
        self.save_and_refresh()

    def store_start(self, value: str):
        self.settings = {"start_tab": {"selected": value}}
        try:
            self.store.save_settings(self.settings)
            self.message("Einstellungen gespeichert.")
        except OSError as error:
            self.message(f"Einstellungen konnten nicht gespeichert werden: {error}", error=True)

    def choose_dialog(self, title, options, callback):
        dialog = None
        choices = [
            ft.ListTile(title=ft.Text(label), on_click=lambda _, value=value: self.select_dialog(dialog, value, callback))
            for label, value in options
        ]
        dialog = ft.AlertDialog(
            modal=True, title=ft.Text(title),
            content=ft.Column(choices, tight=True, scroll=ft.ScrollMode.AUTO),
            actions=[ft.TextButton("Abbrechen", on_click=lambda _: self.close_dialog())],
        )
        self.page.show_dialog(dialog)

    def select_dialog(self, dialog, value, callback):
        self.close_dialog()
        callback(value)

    def create_player_distribution(self, players: list[Player]):
        if not players:
            self.message("Wähle mindestens einen anwesenden Spieler aus.", error=True)
            return
        if not self.presets:
            self.message("Lege zuerst mindestens ein Preset an.", error=True)
            return
        self.choose_dialog(
            "Preset auswählen",
            [(preset.name, preset) for preset in self.presets],
            lambda preset: self.export_details_dialog(players, preset),
        )

    def export_details_dialog(self, players: list[Player], preset: Preset):
        suggested_opponent = self.presence_opponent or ""
        now = datetime.now()
        season_start = now.year if now.month >= 7 else now.year - 1
        season = f"{season_start % 100:02d}_{(season_start + 1) % 100:02d}"
        venue_suffix = f"-{self.presence_home_away}" if self.presence_home_away else ""
        filename_default = f"{venue_suffix}_{season}"
        opponent = ft.TextField(
            label="Gegnername",
            value=suggested_opponent,
            autofocus=not bool(suggested_opponent),
        )
        filename = ft.TextField(label="Dateiname", value=filename_default)

        def create(dialog):
            title = opponent.value.strip()
            name = re.sub(r"[^\w.-]+", "_", filename.value.strip()).strip("._")
            if not title or not name:
                self.message("Bitte Gegnername und Dateiname eingeben.", error=True)
                return
            self.close_dialog()
            try:
                assignment = distribute_tasks(players, preset.tasks)
                pdf_bytes = create_pdf(assignment, players, title)
            except Exception as error:
                self.log(f"PDF konnte nicht erstellt werden: {error}")
                self.message(f"PDF konnte nicht erstellt werden: {error}", error=True)
                return

            async def save_file():
                try:
                    if is_android_runtime():
                        try:
                            uri = save_pdf_to_documents(pdf_bytes, f"{name}.pdf")
                            if uri:
                                self.message("PDF im Ordner Dokumente gespeichert.")
                                return
                        except Exception as error:
                            self.log(f"Android-Speichern in Dokumente fehlgeschlagen; Dateiauswahl wird verwendet: {error}")
                    documents = Path.home() / "Documents"
                    path = await self.file_picker.save_file(
                        dialog_title="PDF speichern",
                        file_name=f"{name}.pdf",
                        initial_directory=str(documents) if documents.is_dir() else None,
                        file_type=ft.FilePickerFileType.CUSTOM,
                        allowed_extensions=["pdf"],
                        src_bytes=pdf_bytes,
                    )
                    if path:
                        self.message("PDF erfolgreich gespeichert.")
                except Exception as error:
                    self.log(f"PDF-Export fehlgeschlagen: {error}")
                    self.message(f"PDF-Export fehlgeschlagen: {error}", error=True)

            self.page.run_task(save_file)

        self.editor_dialog("PDF vorbereiten", [opponent, filename], create)

    def credentials_dialog(self, _=None):
        saved = self.store.load_credentials() or {}
        email = ft.TextField(label="SpielerPlus-E-Mail", value=saved.get("email", ""), keyboard_type=ft.KeyboardType.EMAIL)
        password = ft.TextField(label="Passwort", password=True, can_reveal_password=True)

        def test_and_save(_):
            if not email.value.strip() or not password.value:
                self.message("Bitte E-Mail und Passwort eingeben.", error=True)
                return
            credentials = {"email": email.value.strip(), "password": password.value}
            self.presence_status = "SpielerPlus-Login wird geprüft …"
            self.presence_status_error = False
            self.message("SpielerPlus-Login wird geprüft …")
            self.render()

            async def check():
                try:
                    await asyncio.to_thread(test_playerplus_login, credentials)
                    self.store.save_credentials(credentials)
                    self.presence_loaded = False
                    self.presence_attempted = False
                    self.manual_presence_selection = None
                    self.presence_opponent = None
                    self.presence_home_away = None
                    self.presence_status = "Login erfolgreich. Zugangsdaten gespeichert; Anwesenheit kann jetzt geladen werden."
                    self.presence_status_error = False
                    self.close_dialog()
                    self.message("SpielerPlus-Login erfolgreich. Zugangsdaten wurden gespeichert.")
                    self.render()
                except Exception as error:
                    self.log(f"SpielerPlus-Test fehlgeschlagen: {error}")
                    self.presence_attempted = True
                    self.presence_loaded = False
                    self.manual_presence_selection = set()
                    self.presence_status = f"SpielerPlus-Login fehlgeschlagen: {error}"
                    self.presence_status_error = True
                    self.message(self.presence_status, error=True)
                    self.render()
            self.page.run_task(check)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("SpielerPlus einrichten"),
            content=ft.Column([email, password], tight=True, spacing=12),
            actions=[
                ft.TextButton("Abbrechen", on_click=lambda _: self.close_dialog()),
                ft.FilledButton("Testen und speichern", icon=ft.Icons.SYNC, on_click=test_and_save),
            ],
        )
        self.page.show_dialog(dialog)

    def refresh_presence(self, _=None):
        credentials = self.store.load_credentials()
        self.presence_attempted = True
        self.presence_loaded = False
        self.manual_presence_selection = set()
        self.presence_opponent = None
        self.presence_home_away = None
        if not credentials:
            self.presence_status = "Keine SpielerPlus-Zugangsdaten eingerichtet. Bitte in den Einstellungen anmelden."
            self.presence_status_error = True
            self.message(self.presence_status, error=True)
            self.render()
            self.change_screen("s_main")
            return

        self.presence_status = "Login und Anwesenheit werden bei SpielerPlus abgerufen …"
        self.presence_status_error = False
        self.render()

        async def fetch():
            try:
                present, opponent, home_away = await asyncio.to_thread(fetch_presence_with_opponent, credentials)
                self.presence = {" ".join(name.split()).casefold() for name in present}
                self.presence_opponent = opponent
                self.presence_home_away = home_away
                self.presence_loaded = True
                self.manual_presence_selection = None
                mapped = sum(
                    bool(player.player_plus_name)
                    and " ".join(player.player_plus_name.split()).casefold() in self.presence
                    for player in self.players
                )
                self.presence_status = (
                    f"Login erfolgreich. {len(present)} Zusagen geladen; {mapped} Kaderspieler zugeordnet."
                    + (f" Gegner: {opponent}" if opponent else "")
                    + (f" ({home_away})" if home_away else "")
                    + ("." if opponent or home_away else "")
                )
                self.presence_status_error = False
                self.message(self.presence_status)
                self.render()
            except Exception as error:
                self.log(f"SpielerPlus-Import fehlgeschlagen: {error}")
                self.presence_loaded = False
                self.presence_opponent = None
                self.presence_home_away = None
                self.presence_status = f"SpielerPlus-Import fehlgeschlagen: {error}"
                self.presence_status_error = True
                self.message(self.presence_status, error=True)
                self.render()
        self.page.run_task(fetch)


def main(page: ft.Page):
    FootballTasksApp(page)


if __name__ == "__main__":
    ft.run(main)






