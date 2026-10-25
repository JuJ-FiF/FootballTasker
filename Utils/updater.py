"""GitHub-Release-Prüfung und Android-APK-Installation."""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import tempfile
import zipfile
from urllib.error import HTTPError
from pathlib import Path
from urllib.request import Request, urlopen

from Utils.version import APP_VERSION

GITHUB_OWNER = "JuJ-FiF"
GITHUB_REPOSITORY = "FootballTasker"
APK_FILE_NAME = "FootballTasker-update.apk"
USER_AGENT = "FootballTasker"


def version_tuple(version: str) -> tuple[int, int, int, int]:
    """Unterstützt v1.2.3 und optionale Tags wie 1.2.3-HotFix#4."""
    value = str(version).strip().removeprefix("v").removeprefix("V")
    match = re.fullmatch(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:-HotFix#(\d+))?", value, re.I)
    if not match:
        raise ValueError(f"Ungültige Versionsnummer: {version}")
    return tuple(int(part or 0) for part in match.groups())


def is_newer_version(current_version: str, latest_version: str) -> bool:
    return version_tuple(latest_version) > version_tuple(current_version)


def is_android_runtime() -> bool:
    return sys.platform == "android" or "ANDROID_ARGUMENT" in os.environ


async def check_for_update() -> dict | None:
    """Liest das neueste GitHub-Release und sucht darin nach einer APK."""
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPOSITORY}/releases/latest"
    request = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT})

    def load_release() -> dict:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        release = await asyncio.to_thread(load_release)
    except HTTPError as error:
        if error.code == 404:
            raise RuntimeError(
                "Kein öffentliches GitHub-Release gefunden. Prüfe, ob das Repository öffentlich ist "
                "und bereits ein Release mit APK enthält."
            ) from error
        raise
    latest = str(release.get("tag_name", "")).strip()
    if not latest:
        raise ValueError("Das GitHub-Release enthält keinen Versions-Tag.")
    version_tuple(latest)
    if not is_newer_version(APP_VERSION, latest):
        return None

    asset = next(
        (item for item in release.get("assets", []) if str(item.get("name", "")).lower().endswith(".apk")),
        None,
    )
    download_url = asset.get("browser_download_url") if asset else None
    if not download_url:
        raise ValueError(f"Für Version {latest} wurde keine APK im Release gefunden.")
    return {
        "version": latest,
        "name": release.get("name") or f"FootballTasker {latest}",
        "changelog": release.get("body") or "Keine Release-Notizen vorhanden.",
        "download_url": download_url,
    }


def get_update_file_path() -> Path:
    directory = Path(os.environ.get("FLET_APP_STORAGE_DATA") or Path.cwd())
    directory.mkdir(parents=True, exist_ok=True)
    return directory / APK_FILE_NAME


def download_apk(download_url: str) -> Path:
    """Lädt eine APK in eine temporäre Datei und ersetzt erst danach die alte."""
    path = get_update_file_path()
    request = Request(download_url, headers={"User-Agent": USER_AGENT, "Accept": "application/octet-stream"})
    descriptor, temporary = tempfile.mkstemp(prefix="footballtasker-update-", suffix=".apk", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as output, urlopen(request, timeout=120) as response:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        if not zipfile.is_zipfile(temporary):
            raise RuntimeError("Die heruntergeladene Datei ist keine gültige APK/ZIP-Datei.")
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return path


def request_install_permission() -> bool:
    """Öffnet bei Bedarf Androids Berechtigung für App-Installationen."""
    from jnius import autoclass, cast

    activity_class = autoclass("com.flet.serious_python_android.PythonActivity")
    activity = cast("android.app.Activity", activity_class.mActivity)
    if activity is None:
        raise RuntimeError("Die Android Activity ist nicht verfügbar.")
    if activity.getPackageManager().canRequestPackageInstalls():
        return True

    Intent = autoclass("android.content.Intent")
    Uri = autoclass("android.net.Uri")
    Settings = autoclass("android.provider.Settings")
    intent = Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES)
    intent.setData(Uri.parse("package:" + activity.getPackageName()))
    activity.startActivity(intent)
    return False


def start_android_update(apk_path: Path) -> None:
    """Öffnet den nativen Android-Installer für die heruntergeladene APK."""
    from jnius import autoclass, cast

    path = Path(apk_path)
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("Die heruntergeladene APK fehlt oder ist leer.")
    activity_class = autoclass("com.flet.serious_python_android.PythonActivity")
    activity = cast("android.app.Activity", activity_class.mActivity)
    if activity is None:
        raise RuntimeError("Die Android Activity ist nicht verfügbar.")

    Intent = autoclass("android.content.Intent")
    File = autoclass("java.io.File")
    FileProvider = autoclass("androidx.core.content.FileProvider")
    if not request_install_permission():
        raise RuntimeError("Die Berechtigung zur Installation unbekannter Apps wurde nicht erteilt.")

    apk_uri = FileProvider.getUriForFile(
        activity,
        activity.getPackageName() + ".updateprovider",
        File(str(path)),
    )
    intent = Intent(Intent.ACTION_INSTALL_PACKAGE)
    intent.setDataAndType(apk_uri, "application/vnd.android.package-archive")
    intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    activity.startActivity(intent)


async def download_and_install_update(download_url: str) -> Path | None:
    """Fordert Installationsrecht an und lädt/öffnet danach die APK."""
    can_install = await asyncio.to_thread(request_install_permission)
    if not can_install:
        return None
    apk_path = await asyncio.to_thread(download_apk, download_url)
    await asyncio.to_thread(start_android_update, apk_path)
    return apk_path
