def rotate_queue(items: list[str], max_items: int = 20):
    clean: list[str] = []
    seen: set[str] = set()
    for raw in items:
        track = (raw or '').strip()
        if not track or track in seen:
            continue
        clean.append(track)
        seen.add(track)
        if len(clean) >= max_items:
            break
    return clean
