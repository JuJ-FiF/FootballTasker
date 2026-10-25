"""App- und SpielerPlus-Einstellungen."""

import flet as ft
from .common import page_heading
from .registry import SCREEN_DEFINITIONS
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
        return ft.Column(
            [page_heading("Einstellungen", "App-Start, SpielerPlus und Updates einrichten."), general, login, updater],
            expand=True, spacing=20, scroll=ft.ScrollMode.AUTO,
        )

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
