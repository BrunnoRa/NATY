from __future__ import annotations

from datetime import datetime


PRIORITY = {"high": 35.0, "normal": 20.0, "low": 8.0}


def task_score(task: dict, now: datetime | None = None) -> float:
    """Prazo (0..60) + prioridade (8..35) + atraso (25) + adiamentos (0..15) - duração (0..10)."""
    now = now or datetime.now().astimezone()
    score = PRIORITY.get(task.get("priority", "normal"), 20.0)
    due = task.get("due_at")
    if due:
        try:
            due_dt = datetime.fromisoformat(due)
            if due_dt.tzinfo is None: due_dt = due_dt.replace(tzinfo=now.tzinfo)
            hours = (due_dt - now).total_seconds() / 3600
            if hours < 0: score += 60
            elif hours <= 24: score += 50
            elif hours <= 72: score += 35
            elif hours <= 168: score += 20
            else: score += 5
        except ValueError: pass
    score += min(int(task.get("postpone_count") or 0) * 5, 15)
    duration = int(task.get("estimated_minutes") or 30)
    score -= min(duration / 12, 10)
    return round(score, 2)
