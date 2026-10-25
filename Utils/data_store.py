"""JSON-Speicher, atomare Schreibvorgänge und verschlüsselte Zugangsdaten."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from Models.models import Player, Preset, Task


class DataStore:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        configured_backup = os.getenv("FOOTBALLTASKER_BACKUP")
        if configured_backup:
            self.backup_dir = Path(configured_backup)
        elif os.getenv("FLET_APP_STORAGE_DATA"):
            self.backup_dir = self.directory / "BACKUP"
        else:
            self.backup_dir = Path(__file__).resolve().parents[3] / "BACKUP" / "FootballTasker"

    def _snapshot(self, names: tuple[str, ...]) -> None:
        existing = [self.directory / name for name in names if (self.directory / name).exists()]
        if not existing:
            return
        snapshot = self.backup_dir / "data" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        snapshot.mkdir(parents=True, exist_ok=True)
        for path in existing:
            shutil.copy2(path, snapshot / path.name)
        with (self.backup_dir / "change-log.md").open("a", encoding="utf-8") as log:
            log.write(f"\n- {datetime.now().isoformat(timespec='seconds')}: Vor Änderung gesichert: {', '.join(path.name for path in existing)} → `{snapshot}`.\n")

    def _atomic_write(self, name: str, content: bytes) -> None:
        path = self.directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        self._snapshot((name,))
        fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise

    def _write_json(self, name: str, data: dict) -> None:
        self._atomic_write(name, json.dumps(data, ensure_ascii=False, indent=4).encode("utf-8"))

    def load_data(self) -> tuple[list[Player], list[Task], list[Preset], list[dict]]:
        path = self.directory / "data.json"
        if not path.exists():
            return [], [], [], []
        raw = json.loads(path.read_text(encoding="utf-8"))
        return (
            [Player.from_dict(item) for item in raw.get("players", [])],
            [Task.from_dict(item) for item in raw.get("tasks", [])],
            [Preset.from_dict(item) for item in raw.get("presets", [])],
            raw.get("groups", []),
        )

    def save_data(self, players: list[Player], tasks: list[Task], presets: list[Preset], groups: list[dict]) -> None:
        self._write_json("data.json", {
            "players": [player.to_dict() for player in players],
            "tasks": [task.to_dict() for task in tasks],
            "groups": groups,
            "presets": [preset.to_dict() for preset in presets],
        })

    def load_settings(self) -> dict:
        try:
            data = json.loads((self.directory / "settings.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        selected = data.get("start_tab", {}).get("selected", "pla_main")
        allowed = {"pla_main", "pl_main", "t_main", "pr_main", "s_main"}
        return {"start_tab": {"selected": selected if selected in allowed else "pla_main"}}

    def save_settings(self, settings: dict) -> None:
        self._write_json("settings.json", settings)

    def save_credentials(self, data: dict) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        key_path = self.directory / "secret.key"
        encrypted_path = self.directory / "credentials.bin"
        key = key_path.read_bytes() if key_path.exists() else Fernet.generate_key()
        encrypted = Fernet(key).encrypt(json.dumps(data).encode("utf-8"))
        if not key_path.exists():
            self._atomic_write("secret.key", key)
        self._atomic_write("credentials.bin", encrypted)

    def load_credentials(self) -> dict | None:
        key_path, encrypted_path = self.directory / "secret.key", self.directory / "credentials.bin"
        if not key_path.exists() or not encrypted_path.exists():
            return None
        try:
            return json.loads(Fernet(key_path.read_bytes()).decrypt(encrypted_path.read_bytes()).decode("utf-8"))
        except (OSError, ValueError, InvalidToken):
            return None


