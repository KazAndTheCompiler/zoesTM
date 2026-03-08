import re
from datetime import datetime, timedelta, UTC

PRIORITY_MAP = {"!high": 1, "!1": 1, "!med": 2, "!2": 2, "!low": 3, "!3": 3}
MAX_LEN = 280


def _parse_time_expr(text: str) -> tuple[int, int] | None:
    """Parse explicit time like '9pm', '09:30', '21:00'. Returns (hour, minute) in 24h."""
    # 24h style: HH:MM
    m = re.search(r"(\d{1,2}):(\d{2})\b", text, flags=re.IGNORECASE)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2))
        return (hour, minute)
    # 12h style with am/pm
    m = re.search(r"(\d{1,2})\s*(am|pm)\b", text, flags=re.IGNORECASE)
    if m:
        hour = int(m.group(1))
        minute = 0
        ampm = m.group(2).lower()
        if ampm == 'pm' and hour != 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0
        return (hour, minute)
    return None


def _parse_due(text: str, now: datetime):
    low = text.lower()
    candidates = []
    explicit_time = _parse_time_expr(text)

    if 'tomorrow' in low or 'tmrw' in low:
        base = now + timedelta(days=1)
        if explicit_time:
            hour, minute = explicit_time
            candidates.append(base.replace(hour=hour, minute=minute, second=0, microsecond=0))
        else:
            candidates.append(base.replace(hour=9, minute=0, second=0, microsecond=0))

    if 'fri eve' in low:
        days = (4 - now.weekday()) % 7 or 7
        base = now + timedelta(days=days)
        if explicit_time:
            hour, minute = explicit_time
            candidates.append(base.replace(hour=hour, minute=minute, second=0, microsecond=0))
        else:
            candidates.append(base.replace(hour=19, minute=0, second=0, microsecond=0))

    if re.search(r'\b(next\s+)?friday\b', low) and 'fri eve' not in low:
        days = (4 - now.weekday()) % 7 or 7
        base = now + timedelta(days=days)
        if explicit_time:
            hour, minute = explicit_time
            candidates.append(base.replace(hour=hour, minute=minute, second=0, microsecond=0))
        else:
            candidates.append(base.replace(hour=9, minute=0, second=0, microsecond=0))

    m = re.search(r"in\s+(\d+)h", low)
    if m:
        candidates.append(now + timedelta(hours=int(m.group(1))))
    m = re.search(r"in\s+(\d+)min", low)
    if m:
        candidates.append(now + timedelta(minutes=int(m.group(1))))
    return candidates


def parse_quick_add(text: str):
    text = (text or '').strip()[:MAX_LEN]
    tags = re.findall(r"#(\w+)", text)
    priority = 2
    for k, v in PRIORITY_MAP.items():
        if k in text.lower():
            priority = v

    now = datetime.now(UTC)
    due_candidates = _parse_due(text, now)
    due = due_candidates[0].isoformat().replace('+00:00', 'Z') if due_candidates else None
    ambiguity = len(due_candidates) > 1

    title = re.sub(r"#\w+|!high|!med|!low|![123]|tomorrow|tmrw|fri eve|(next\s+)?friday\b|in\s+\d+h|in\s+\d+min|\d{1,2}(:\d{2})?\s*(am|pm)?", "", text, flags=re.I).strip()
    conf = 0.5 + (0.1 if tags else 0) + (0.2 if due else 0) + (0.1 if priority != 2 else 0)
    if ambiguity:
        conf -= 0.15

    result = {
        "title": title or text,
        "due_at": due,
        "priority": priority,
        "tags": tags,
        "confidence": round(max(0.0, min(conf, 0.98)), 2),
        "ambiguity": ambiguity,
        "candidates": [d.isoformat().replace('+00:00', 'Z') for d in due_candidates],
    }
    if result['confidence'] < 0.4:
        result['fallback'] = 'manual_review_required'
    return result
