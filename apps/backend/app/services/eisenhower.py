def quadrant(priority:int, due_soon:bool):
    """Categorize a task by importance and urgency (Eisenhower Matrix).

    Args:
        priority: 1 for high priority, other values for lower priority
        due_soon: True if task is due soon, False otherwise

    Returns:
        One of: 'do', 'schedule', 'delegate', 'eliminate'
    """
    important = priority==1
    urgent = due_soon
    if urgent and important: return 'do'
    if not urgent and important: return 'schedule'
    if urgent and not important: return 'delegate'
    return 'eliminate'
