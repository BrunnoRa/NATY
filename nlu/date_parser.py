from __future__ import annotations

from datetime import datetime, timedelta
import re
import unicodedata


WEEKDAYS = {"segunda": 0, "terca": 1, "quarta": 2, "quinta": 3, "sexta": 4, "sabado": 5, "domingo": 6}


def _plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def parse_datetime(text: str, base: datetime | None = None, default_hour: int = 9) -> str | None:
    base = base or datetime.now().astimezone()
    plain = _plain(text)
    target = base
    found_date = False
    if "depois de amanha" in plain:
        target, found_date = base + timedelta(days=2), True
    elif "amanha" in plain:
        target, found_date = base + timedelta(days=1), True
    elif "hoje" in plain:
        found_date = True
    elif "semana que vem" in plain or "proxima semana" in plain:
        target, found_date = base + timedelta(days=7), True
    else:
        iso = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", plain)
        if iso:
            day, month = int(iso.group(1)), int(iso.group(2))
            year = int(iso.group(3)) if iso.group(3) else base.year
            if year < 100: year += 2000
            try:
                target, found_date = base.replace(year=year, month=month, day=day), True
                if not iso.group(3) and target.date() < base.date(): target = target.replace(year=year + 1)
            except ValueError: return None
        else:
            for name, weekday in WEEKDAYS.items():
                if re.search(rf"\b{name}(?:-feira)?\b", plain):
                    delta = (weekday - base.weekday()) % 7
                    if delta == 0 or "proxim" in plain: delta += 7
                    target, found_date = base + timedelta(days=delta), True
                    break
    time_match = re.search(r"\b(?:as\s*)?(\d{1,2})(?::|h)(\d{2})?\b", plain)
    if not time_match:
        time_match = re.search(r"\bas\s+(\d{1,2})\s*(?:horas?)?\b", plain)
    if time_match:
        hour, minute = int(time_match.group(1)), int(time_match.group(2) or 0)
        if hour > 23 or minute > 59: return None
        target = target.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return target.isoformat(timespec="minutes")
    if found_date:
        target = target.replace(hour=default_hour, minute=0, second=0, microsecond=0)
        return target.isoformat(timespec="minutes")
    return None
