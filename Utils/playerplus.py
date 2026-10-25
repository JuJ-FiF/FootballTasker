"""SpielerPlus-Login und Abruf der Anwesenheiten."""

from __future__ import annotations

import re


def fetch_presence(credentials: dict) -> set[str]:
    """Kompatibilitätsfunktion: liest die Zusagen für das nächste Spiel."""
    present, _, _ = fetch_presence_with_opponent(credentials)
    return present


def fetch_presence_with_opponent(credentials: dict) -> tuple[set[str], str | None, str | None]:
    """Liest Zusagen, Gegner und Heim-/Auswärtsstatus des nächsten Spiels."""
    import requests
    from bs4 import BeautifulSoup

    headers = {"User-Agent": "Mozilla/5.0"}
    login_url = "https://www.spielerplus.de/site/login"
    with requests.Session() as session:
        response = _playerplus_login(session, credentials, headers)
        soup = BeautifulSoup(response.text, "html.parser")
        team = soup.find("a", class_="list-item-link")
        match = re.search(r"[?&]id=(\d+)", team.get("href", "")) if team else None
        if not match:
            raise ValueError("Nach der Anmeldung wurde kein Team gefunden.")
        response = session.get(f"https://www.spielerplus.de/site/switch-user?id={match.group(1)}", headers=headers, timeout=20)
        response.raise_for_status()
        event = BeautifulSoup(response.text, "html.parser").find("div", id=re.compile(r"event-game-\d+"))
        event_match = re.search(r"event-game-(\d+)", event.get("id", "")) if event else None
        if not event_match:
            raise ValueError("SpielerPlus zeigt derzeit kein kommendes Spiel an.")
        opponent_label = event.select_one(".panel-heading-text .panel-subtitle")
        opponent = opponent_label.get_text(" ", strip=True) if opponent_label else None
        heading = event.select_one(".panel-heading-text .panel-title")
        heading_text = heading.get_text(" ", strip=True).casefold() if heading else ""
        if "auswärt" in heading_text or "auswaert" in heading_text:
            home_away = "auswärts"
        elif "heim" in heading_text:
            home_away = "heim"
        else:
            home_away = None
        response = session.post(
            "https://www.spielerplus.de/events/ajax-participations",
            headers=headers,
            timeout=20,
            data={"eventType": "game", "eventId": event_match.group(1)},
        )
        response.raise_for_status()
        html = response.json().get("html", "")
        soup = BeautifulSoup(html, "html.parser")
        present = {
            label.get_text(strip=True)
            for item in soup.select("div.list-item")
            if item.find("i", class_="fa-thumbs-up")
            if (label := item.find("div", class_="list-label"))
        }
        return present, opponent or None, home_away


def _playerplus_login(session, credentials: dict, headers: dict):
    """Meldet eine bestehende HTTP-Session an und gibt die Antwort zurück."""
    from bs4 import BeautifulSoup

    login_url = "https://www.spielerplus.de/site/login"
    response = session.get(login_url, headers=headers, timeout=20)
    response.raise_for_status()
    csrf = BeautifulSoup(response.text, "html.parser").find("input", {"name": "_csrf"})
    if not csrf:
        raise ValueError("SpielerPlus hat kein Anmelde-Token geliefert.")
    response = session.post(login_url, headers=headers, timeout=20, data={
        "_csrf": csrf.get("value", ""),
        "LoginForm[email]": credentials["email"],
        "LoginForm[password]": credentials["password"],
    })
    response.raise_for_status()
    if "site/login" in response.url:
        raise ValueError("SpielerPlus-Login fehlgeschlagen. E-Mail und Passwort prüfen.")
    return response


def test_playerplus_login(credentials: dict) -> None:
    """Prüft nur den Login, unabhängig davon, ob ein kommendes Spiel existiert."""
    import requests

    with requests.Session() as session:
        _playerplus_login(session, credentials, {"User-Agent": "Mozilla/5.0"})


