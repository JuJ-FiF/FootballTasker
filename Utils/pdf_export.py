"""Erzeugung der Aufgabenverteilung und Trikot-Checkliste als PDF."""

from __future__ import annotations

import io

from Models.models import Player


def create_pdf(assignment: dict[str, list[str]], players: list[Player], opponent: str) -> bytes:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    task_image = _table_image(assignment, opponent, plt)
    checklist_players = sorted(
        (player for player in players if player.number is not None),
        key=lambda player: player.number,
    )
    checklist_image = _checklist_image(checklist_players, plt)

    task = Image.open(task_image).convert("RGB")
    checklist = Image.open(checklist_image).convert("RGB")
    combined = Image.new("RGB", (max(task.width, checklist.width), task.height + checklist.height), "white")
    combined.paste(task, (0, 0))
    combined.paste(checklist, (0, task.height))
    output = io.BytesIO()
    combined.save(output, "PDF", resolution=100.0)
    return output.getvalue()


def save_pdf_to_downloads(pdf_bytes: bytes, filename: str) -> str | None:
    """Speichert unter Android 10+ ohne Dateisystemberechtigung in Downloads."""
    from jnius import autoclass, jarray, cast

    BuildVersion = autoclass("android.os.Build$VERSION")
    if BuildVersion.SDK_INT < 29:
        return None

    activity_class = autoclass("com.flet.serious_python_android.PythonActivity")
    activity = cast("android.app.Activity", activity_class.mActivity)
    if activity is None:
        raise RuntimeError("Die Android Activity ist nicht verfügbar.")

    MediaStoreDownloads = autoclass("android.provider.MediaStore$Downloads")
    ContentValues = autoclass("android.content.ContentValues")
    resolver = activity.getContentResolver()
    values = ContentValues()
    values.put("_display_name", filename)
    values.put("mime_type", "application/pdf")
    values.put("relative_path", "Download/FootballTasker")
    values.put("is_pending", 1)
    uri = resolver.insert(MediaStoreDownloads.EXTERNAL_CONTENT_URI, values)
    if uri is None:
        raise RuntimeError("Android konnte keinen Eintrag im Download-Ordner anlegen.")

    try:
        stream = resolver.openOutputStream(uri)
        if stream is None:
            raise RuntimeError("Android konnte die PDF-Datei nicht öffnen.")
        try:
            data = jarray("b", [byte if byte < 128 else byte - 256 for byte in pdf_bytes])
            stream.write(data)
            stream.flush()
        finally:
            stream.close()

        completed = ContentValues()
        completed.put("is_pending", 0)
        resolver.update(uri, completed, None, None)
        return str(uri.toString())
    except Exception:
        resolver.delete(uri, None, None)
        raise


def _table_image(assignment: dict[str, list[str]], opponent: str, plt) -> io.BytesIO:
    rows = [[name, ", ".join(map(str, names)) if names else "-"] for name, names in assignment.items()]
    fig, axis = plt.subplots(figsize=(5, len(rows) * 0.5 + 1))
    axis.axis("off")
    axis.set_title(opponent, fontsize=14, fontweight="bold", color="black", pad=20)
    axis.text(0.02, 0.9, "Aufgabenverteilung", ha="left", va="top", fontsize=10,
              color="black", transform=axis.transAxes)
    table = axis.table(cellText=rows, colLabels=["Aufgabe", "Verantwortliche/r"], cellLoc="left", loc="center")
    _style_table(table)
    fig.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", dpi=200, transparent=True)
    plt.close(fig)
    buffer.seek(0)
    return buffer


def _checklist_image(players: list[Player], plt) -> io.BytesIO:
    rows = [[str(player.number), "☐", "☐"] for player in players]
    fig, axis = plt.subplots(figsize=(5, len(rows) * 0.5 + 1))
    axis.axis("off")
    axis.text(0.02, 0.87, "Trikot-Checkliste", ha="left", va="top", fontsize=10,
              color="black", transform=axis.transAxes)
    table = axis.table(cellText=rows, colLabels=["Nummer", "Trikot", "Hose"], cellLoc="center", loc="center")
    _style_table(table)
    fig.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", dpi=200, transparent=True)
    plt.close(fig)
    buffer.seek(0)
    return buffer


def _style_table(table) -> None:
    for (row, _), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight="bold", color="white")
            cell.set_facecolor("#40466e")
        else:
            cell.set_facecolor("#f1f1f2")
    table.scale(1, 1.5)




