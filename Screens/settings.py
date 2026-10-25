"""App- und SpielerPlus-Einstellungen."""

import json

import flet as ft
from .common import page_heading
from .registry import SCREEN_DEFINITIONS
from Utils.data_transfer import build_import_data, create_export_data
from Utils.updater import check_for_update, download_and_install_update, is_android_runtime
from Utils.version import APP_VERSION


class SettingsScreen:
    def __init__(self, app):
        self.app = app

    def build(self):
        selected = self.app.settings["start_tab"]["selected"]
        start = ft.Dropdown(
            label="Startbereich",
            value=selected,
            options=[ft.dropdown.Option(key, label) for key, label, _ in SCREEN_DEFINITIONS],
            expand=True,
        )
        general = ft.Card(
            variant=ft.CardVariant.OUTLINED,
            elevation=0,
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Text("Allgemein", size=18, weight=ft.FontWeight.W_600),
                    ft.Text("Lege fest, welcher Bereich beim Start geöffnet wird.", color=ft.Colors.ON_SURFACE_VARIANT),
                    start,
                    ft.Row([ft.FilledButton("Speichern", icon=ft.Icons.SAVE_OUTLINED, on_click=lambda _: self.app.store_start(start.value))], alignment=ft.MainAxisAlignment.END),
                ], spacing=14),
            ),
        )
        login = ft.Card(
            variant=ft.CardVariant.OUTLINED,
            elevation=0,
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Row([ft.Icon(ft.Icons.SYNC_ALT, color=ft.Colors.PRIMARY), ft.Text("SpielerPlus", size=18, weight=ft.FontWeight.W_600)], spacing=10),
                    ft.Text("Zugangsdaten werden verschlüsselt lokal gespeichert. Der Test prüft den Login unabhängig vom nächsten Spiel.", color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text("Zugangsdaten sind eingerichtet." if self.app.store.load_credentials() else "Noch keine Zugangsdaten gespeichert.", color=ft.Colors.PRIMARY),
                    ft.Text(
                        self.app.presence_status,
                        color=ft.Colors.ERROR if self.app.presence_status_error else ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Row([
                        ft.OutlinedButton("Zugangsdaten einrichten und testen", icon=ft.Icons.KEY_OUTLINED, on_click=self.app.credentials_dialog),
                        ft.FilledButton("Anwesenheit aktualisieren", icon=ft.Icons.REFRESH, on_click=self.app.refresh_presence),
                    ], wrap=True),
                ], spacing=14),
            ),
        )
        updater = ft.Card(
            variant=ft.CardVariant.OUTLINED,
            elevation=0,
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.SYSTEM_UPDATE, color=ft.Colors.PRIMARY),
                        ft.Text("App-Updates", size=18, weight=ft.FontWeight.W_600),
                    ], spacing=10),
                    ft.Text(f"Installierte Version: {APP_VERSION}"),
                    ft.Text(
                        "Updates werden über GitHub-Releases geprüft und als Android-App installiert.",
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Row([
                        ft.OutlinedButton(
                            "Nach Updates suchen",
                            icon=ft.Icons.SYSTEM_UPDATE,
                            on_click=self.check_updates,
                        ),
                    ], alignment=ft.MainAxisAlignment.END),
                ], spacing=12),
            ),
        )
        data_transfer = ft.Card(
            variant=ft.CardVariant.OUTLINED,
            elevation=0,
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.SWAP_HORIZ, color=ft.Colors.PRIMARY),
                        ft.Text("Daten sichern", size=18, weight=ft.FontWeight.W_600),
                    ], spacing=10),
                    ft.Text(
                        "Spieler, Aufgaben, Presets und Gruppen als JSON sichern oder aus einem Export wiederherstellen. Zugangsdaten und Einstellungen werden nicht exportiert.",
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Row([
                        ft.OutlinedButton("Daten importieren", icon=ft.Icons.FILE_OPEN, on_click=self.import_data),
                        ft.FilledButton("Daten exportieren", icon=ft.Icons.DOWNLOAD, on_click=self.export_data),
                    ], wrap=True, alignment=ft.MainAxisAlignment.END),
                ], spacing=12),
            ),
        )
        return ft.Column(
            [page_heading("Einstellungen", "App-Start, SpielerPlus, Updates und Datensicherung einrichten."), general, login, updater, data_transfer],
            expand=True, spacing=20, scroll=ft.ScrollMode.AUTO,
        )

    async def export_data(self, _=None):
        try:
            payload = create_export_data(self.app.players, self.app.tasks, self.app.presets, self.app.groups)
            content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            path = await self.app.file_picker.save_file(
                dialog_title="FootballTasker-Daten exportieren",
                file_name="footballtasker_export.json",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["json"],
                src_bytes=content,
            )
            if path:
                self.app.message("Datenexport wurde erstellt.")
        except Exception as error:
            self.app.log(f"Datenexport fehlgeschlagen: {error}")
            self.app.message(f"Datenexport fehlgeschlagen: {error}", error=True)

    async def import_data(self, _=None):
        try:
            files = await self.app.file_picker.pick_files(
                dialog_title="FootballTasker-Daten importieren",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["json"],
                allow_multiple=False,
                with_data=True,
            )
            if not files:
                return
            if not files[0].bytes:
                raise ValueError("Die ausgewählte Datei konnte nicht gelesen werden.")
            payload = json.loads(files[0].bytes.decode("utf-8-sig"))
            imported = build_import_data(payload)
            self._confirm_import(imported)
        except Exception as error:
            self.app.log(f"Datenimport fehlgeschlagen: {error}")
            self.app.message(f"Datenimport fehlgeschlagen: {error}", error=True)

    def _confirm_import(self, imported):
        players, tasks, presets, groups = imported
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Daten ersetzen?"),
            content=ft.Text(
                f"Der Import ersetzt die aktuellen Daten durch {len(players)} Spieler, {len(tasks)} Aufgaben, "
                f"{len(presets)} Presets und {len(groups)} Gruppen."
            ),
            actions=[
                ft.TextButton("Abbrechen", on_click=lambda _: self.app.close_dialog()),
                ft.FilledButton("Importieren", on_click=lambda _: self._apply_import(dialog, imported)),
            ],
        )
        self.app.page.show_dialog(dialog)

    def _apply_import(self, dialog, imported):
        previous = (self.app.players, self.app.tasks, self.app.presets, self.app.groups)
        self.app.players, self.app.tasks, self.app.presets, self.app.groups = imported
        try:
            self.app.save_data()
        except Exception as error:
            self.app.players, self.app.tasks, self.app.presets, self.app.groups = previous
            self.app.close_dialog()
            self.app.log(f"Speichern importierter Daten fehlgeschlagen: {error}")
            self.app.message(f"Import konnte nicht gespeichert werden: {error}", error=True)
            return
        self.app.presence = set()
        self.app.presence_loaded = False
        self.app.presence_attempted = False
        self.app.manual_presence_selection = None
        self.app.presence_status = "Daten importiert. SpielerPlus-Anwesenheit bei Bedarf neu laden."
        self.app.presence_status_error = False
        self.app.close_dialog()
        self.app.render()
        self.app.message("Datenimport erfolgreich.")

    async def check_updates(self, event=None):
        button = event.control if event and hasattr(event, "control") else None
        if button:
            button.disabled = True
            button.update()
        try:
            self.app.message("Suche nach FootballTasker-Updates …")
            update = await check_for_update()
            if update is None:
                self.app.message(f"FootballTasker ist aktuell (Version {APP_VERSION}).")
                return
            self.app.message(f"Update verfügbar: Version {update['version']}.")
            self.show_update_dialog(update)
        except Exception as error:
            self.app.log(f"Updateprüfung fehlgeschlagen: {error}")
            self.app.message(f"Updateprüfung fehlgeschlagen: {error}", error=True)
        finally:
            if button:
                button.disabled = False
                button.update()

    def show_update_dialog(self, update: dict):
        android = is_android_runtime()
        content = [ft.Text(update["changelog"], selectable=True)]
        if not android:
            content.append(ft.Text(
                "Die APK-Installation ist nur in der Android-App verfügbar.",
                color=ft.Colors.ON_SURFACE_VARIANT,
            ))
        actions = [ft.TextButton("Später", on_click=lambda _: self.app.close_dialog())]
        if android:
            async def install_update(_):
                await self.download_update(update["download_url"])

            actions.append(ft.FilledButton(
                "Update installieren",
                icon=ft.Icons.SYSTEM_UPDATE,
                on_click=install_update,
            ))
        self.app.page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Update verfügbar: {update['version']}"),
            content=ft.Column(content, tight=True, scroll=ft.ScrollMode.AUTO),
            actions=actions,
        ))

    async def download_update(self, download_url: str):
        self.app.close_dialog()
        self.app.message("Update wird vorbereitet …")
        try:
            apk_path = await download_and_install_update(download_url)
            if apk_path is None:
                self.app.message(
                    "Android hat die Berechtigungseinstellungen geöffnet. Erlaube dort die Installation und starte das Update erneut."
                )
                return
            self.app.message("APK geladen. Bitte die Installation im Android-Dialog bestätigen.")
        except Exception as error:
            self.app.log(f"Android-Update fehlgeschlagen: {error}")
            self.app.message(f"Update fehlgeschlagen: {error}", error=True)
