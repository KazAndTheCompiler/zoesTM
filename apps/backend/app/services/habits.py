from datetime import datetime, timedelta


def _date_from_logged_at(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
    except Exception:
        try:
            return datetime.fromisoformat(value.split(' ')[0]).date()
        except Exception:
            return None


def _recent_streak_score(logs, days: int = 7):
    # Practical skeleton metric: count successful checkins within recent window.
    # (keeps behavior stable for current test expectations while avoiding all-time inflation)
    cutoff = datetime.now().date() - timedelta(days=days)
    score = 0
    for log in logs:
        if not bool(log.get('done')):
            continue
        d = _date_from_logged_at(log.get('logged_at'))
        if d and d >= cutoff:
            score += 1
    return score


def weekly_overview(logs):
    logs = [log for log in logs if log.get('habit_name')]
    total_logs = len(logs)
    done_logs = sum(1 for log in logs if log.get('done'))
    completion_pct = round((done_logs / total_logs) * 100, 1) if total_logs else 0.0
    streak = _recent_streak_score(logs, days=7)
    misses = total_logs - done_logs

    habits = sorted(set(log['habit_name'] for log in logs if 'habit_name' in log and log['habit_name']))

    log_map = {}
    for log in logs:
        habit = log.get('habit_name')
        ts = log.get('logged_at')
        if not habit or not ts:
            continue
        if isinstance(ts, str):
            date_part = ts.split('T')[0].split(' ')[0]
        else:
            continue
        if date_part not in log_map:
            log_map[date_part] = {}
        if habit not in log_map[date_part]:
            log_map[date_part][habit] = bool(log.get('done'))

    today = datetime.now().date()
    days = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        date_str = date.isoformat()
        label = date.strftime('%a')
        checkins = {h: log_map.get(date_str, {}).get(h, False) for h in habits}
        days.append({'date': date_str, 'label': label, 'checkins': checkins})

    consistency = 'high' if completion_pct >= 80 else 'medium' if completion_pct >= 50 else 'low'

    return {
        'completion_pct': completion_pct,
        'streak': streak,
        'misses': misses,
        'habits': habits,
        'days': days,
        'consistency': consistency,
    }
