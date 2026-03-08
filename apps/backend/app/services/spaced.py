def compute_next_interval(state: str, rating: str, interval: int | None, ease_factor: float, reviews_done: int) -> dict:
    """
    Compute next interval and state based on SM-2 algorithm.
    Args:
      state: current card state ('new', 'learning', 'review', 'relearn')
      rating: one of 'again', 'hard', 'good', 'easy'
      interval: previous interval in days (None for new cards)
      ease_factor: current EF (typically 2.5)
      reviews_done: count of successful reviews so far
    Returns:
      dict with keys: new_state, new_interval, new_ease_factor, lapse_increment (bool)
    """
    if interval is None:
        interval = 1

    # Default outputs
    new_state = state
    new_interval = interval
    new_ease = ease_factor
    lapse_inc = False

    if rating == 'again':
        lapse_inc = True
        if state in ('review', 'relearn'):
            new_state = 'relearn'
        else:
            new_state = 'learning'
        new_interval = 1
        new_ease = max(1.3, ease_factor - 0.20)

    elif rating == 'hard':
        # Hard: slight interval increase, small EF decrease.
        # If the card was in relearn, graduate it back to review.
        new_state = 'review' if state == 'relearn' else state
        new_interval = max(1, int(interval * 1.2))
        new_ease = max(1.3, ease_factor - 0.15)

    elif rating == 'good':
        new_state = 'review'
        # For cards in learning, good graduates to review with ease-based interval
        new_interval = max(1, int(interval * ease_factor))
        # ease_factor unchanged

    elif rating == 'easy':
        new_state = 'review'
        new_interval = max(1, int(interval * ease_factor * 1.3))
        new_ease = min(2.5, max(1.3, ease_factor + 0.15))

    else:
        raise ValueError(f'invalid rating: {rating}')

    return {
        'new_state': new_state,
        'new_interval': new_interval,
        'new_ease_factor': new_ease,
        'lapse_increment': lapse_inc,
    }

# Backward-compatible wrapper for the old simple interface
def next_interval(state: str, rating: str, interval: int = 1) -> tuple[str, int]:
    """Legacy simple scheduler (used by some tests and preview)."""
    # Use default ease 2.5 and 0 reviews for backward compatibility
    result = compute_next_interval(state, rating, interval, 2.5, 0)
    return (result['new_state'], result['new_interval'])


