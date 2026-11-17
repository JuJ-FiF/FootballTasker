"""SpielerPlus-Login und Abruf der Anwesenheiten."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

PLAYERPLUS_LOGIN_URL = "https://www.spielerplus.de/site/login"
PLAYERPLUS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Upgrade-Insecure-Requests": "1",
}


def fetch_presence(credentials: dict) -> set[str]:
    """Kompatibilitätsfunktion: liest die Zusagen für das nächste Spiel."""
    present, _, _ = fetch_presence_with_opponent(credentials)
    return present


def fetch_presence_with_opponent(credentials: dict) -> tuple[set[str], str | None, str | None]:
    """Liest Zusagen, Gegner und Heim-/Auswärtsstatus des nächsten Spiels."""
    import requests
    from bs4 import BeautifulSoup

    with requests.Session() as session:
        response = _playerplus_login(session, credentials)
        soup = BeautifulSoup(response.text, "html.parser")
        team = soup.find("a", class_="list-item-link")
        match = re.search(r"[?&]id=(\d+)", team.get("href", "")) if team else None
        if not match:
            raise ValueError("Nach der Anmeldung wurde kein Team gefunden.")

        switch_url = urljoin(response.url, f"/site/switch-user?id={match.group(1)}")
        response = session.get(
            switch_url,
            headers=_request_headers(referer=response.url),
            timeout=20,
        )
        _raise_for_status(response, "Teamwechsel")

        event = BeautifulSoup(response.text, "html.parser").find(
            "div", id=re.compile(r"event-game-\d+")
        )
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

        participations_url = urljoin(response.url, "/events/ajax-participations")
        response = session.post(
            participations_url,
            headers=_request_headers(referer=response.url, ajax=True),
            timeout=20,
            data={"eventType": "game", "eventId": event_match.group(1)},
        )
        _raise_for_status(response, "Anwesenheitsabruf")
        html = response.json().get("html", "")
        soup = BeautifulSoup(html, "html.parser")
        present = {
            label.get_text(strip=True)
            for item in soup.select("div.list-item")
            if item.find("i", class_="fa-thumbs-up")
            if (label := item.find("div", class_="list-label"))
        }
        return present, opponent or None, home_away


def _request_headers(referer: str, ajax: bool = False) -> dict[str, str]:
    """Ergänzt Browser- und Sitzungsheader für Folgeanfragen."""
    origin = urlsplit(referer)
    headers = {
        **PLAYERPLUS_HEADERS,
        "Referer": referer,
        "Origin": f"{origin.scheme}://{origin.netloc}",
    }
    if ajax:
        headers.update({
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
        })
    return headers


def _raise_for_status(response, step: str) -> None:
    import requests

    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        if response.status_code == 403:
            raise RuntimeError(
                f"SpielerPlus hat den Schritt „{step}“ abgewiesen (HTTP 403, {response.url})."
            ) from error
        raise


def _playerplus_login(session, credentials: dict):
    """Meldet eine bestehende HTTP-Session an und gibt die Antwort zurück."""
    from bs4 import BeautifulSoup

    response = session.get(PLAYERPLUS_LOGIN_URL, headers=PLAYERPLUS_HEADERS, timeout=20)
    _raise_for_status(response, "Laden der Login-Seite")
    soup = BeautifulSoup(response.text, "html.parser")
    csrf = soup.find("input", {"name": "_csrf"})
    if not csrf:
        raise ValueError("SpielerPlus hat kein Anmelde-Token geliefert.")

    form = csrf.find_parent("form")
    login_url = urljoin(response.url, form.get("action")) if form and form.get("action") else response.url
    response = session.post(
        login_url,
        headers=_request_headers(referer=response.url),
        timeout=20,
        data={
            "_csrf": csrf.get("value", ""),
            "LoginForm[email]": credentials["email"],
            "LoginForm[password]": credentials["password"],
        },
    )
    _raise_for_status(response, "Absenden der Anmeldung")
    if "site/login" in response.url:
        raise ValueError("SpielerPlus-Login fehlgeschlagen. E-Mail und Passwort prüfen.")
    return response


def test_playerplus_login(credentials: dict) -> None:
    """Prüft nur den Login, unabhängig davon, ob ein kommendes Spiel existiert."""
    import requests

    with requests.Session() as session:
        _playerplus_login(session, credentials)
