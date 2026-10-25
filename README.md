# FootballTasker

Flet-App zur Verwaltung von Spielern, Aufgaben und Presets sowie zur Erstellung einer Aufgabenverteilung als PDF.

## Start

Im Projektordner mit Python 3.11 oder 3.12:

```powershell
python -m pip install -e .
flet run main.py
```

## Bereiche

- **Aufgabenverteilung:** Anwesende Spieler manuell markieren oder über SpielerPlus abrufen, Preset wählen und PDF mit Gegnername und Dateiname erstellen.
- **Spieler:** Name, Rückennummer, SpielerPlus-Name, optionale Gruppe und Teilnahme an Aufgabenverteilungen pflegen.
- **Aufgaben:** Aufgabenname, Mindest- und Maximalzahl sowie Priorität bearbeiten.
- **Presets:** Aufgaben zu wiederverwendbaren Sätzen bündeln.
- **Einstellungen:** Startbereich auswählen, SpielerPlus-Zugangsdaten testen und verschlüsselt speichern, Updates prüfen und Teamdaten importieren/exportieren.

Die Daten aus `TasksApp/data.json` wurden als Ausgangsdaten übernommen. Die alten Gruppen bleiben beim Speichern erhalten; die hier nicht angefragten Gruppenverteilungs-Bildschirme wurden nicht übernommen.

Teamdaten lassen sich in den Einstellungen als JSON-Datei exportieren und wieder importieren. Der Import ersetzt nach Bestätigung Spieler, Aufgaben, Presets und Gruppen. SpielerPlus-Zugangsdaten und lokale Einstellungen sind nicht enthalten. `data.json` und Sicherungskopien werden nicht in die APK aufgenommen; auf einem neuen Gerät können die Teamdaten über den Import geladen werden. Android-PDFs werden nach Möglichkeit ohne zusätzliche Berechtigung in `Downloads/FootballTasker` gespeichert.

## Datensicherung

Vor jedem Speichern von Daten oder Einstellungen legt die App eine Kopie des vorherigen Dateistands unter `C:\FLET\BACKUP\FootballTasker\data` ab und ergänzt `change-log.md`. Die Dateien werden atomar ersetzt. Der Speicherpfad kann über `FOOTBALLTASKER_BACKUP` angepasst werden. Änderungen am Projektcode werden vor jedem Arbeitsschritt als vollständiger Zeitstempel-Snapshot im selben Backup-Ordner abgelegt.

SpielerPlus-Zugangsdaten werden lokal mit Fernet verschlüsselt. Die alte Kivy-Fehlerberichtsfunktion mit eingebetteten Mail-Zugangsdaten wurde nicht übernommen.

## Projektstruktur

- `main.py`: Flet-Einstiegspunkt, Navigation und App-Abläufe.
- `Screens/`: ein Screen pro Anwendungsbereich sowie gemeinsame UI-Bausteine.
- `Models/models.py`: Spieler-, Aufgaben- und Preset-Datenmodelle.
- `Utils/data_store.py`: JSON-Speicher, Sicherungen und verschlüsselte Zugangsdaten.
- `Utils/playerplus.py`: Login-Test und Anwesenheitsabruf.
- `Utils/task_distribution.py`: automatische Aufgabenverteilung.
- `Utils/pdf_export.py`: PDF-Tabellen und Checkliste.
- `Utils/updater.py` und `Utils/version.py`: Android-Updateprüfung über GitHub-Releases und Versionsstand.
- `data.json`, `settings.json`, `credentials.bin`, `secret.key`: lokale App-Daten im Projektordner.
- `logs/`: App-Protokolle.

Der Android-Updater prüft `JuJ-FiF/FootballTasker` auf ein neueres öffentliches GitHub-Release mit APK-Datei. Die App-Version steht in `Utils/version.py` und muss zum Release-Tag passen. Für eine erfolgreiche Installation muss die APK dieselbe Android-App-ID und Signatur wie die installierte App verwenden.
