import re


def parse_intent(text: str):
    low = text.lower().strip()
    intents = []
    reasons = []
    confidence = 0.5

    parts = [p.strip() for p in re.split(r"\bthen\b", low) if p.strip()]
    for part in parts:
        if part.startswith('add task'):
            intents.append('task.create')
        elif part.startswith('start pomodoro') or part.startswith('focus'):
            intents.append('focus.start')
        elif part.startswith('break'):
            intents.append('focus.break')
        elif part.startswith('set alarm'):
            intents.append('alarm.create')
        elif part.startswith('review'):
            intents.append('review.start')
        elif part.startswith('play') or part.startswith('queue'):
            intents.append('player.play')
        elif part.startswith('delete'):
            intents.append('danger.delete')
        else:
            reasons.append(f'unrecognized segment: {part}')

    if not intents:
        return {
            'intent': 'unknown',
            'intents': [],
            'confidence': 0.1,
            'reasons': reasons or ['no intent matched'],
            'rejected_intents': parts,
        }

    confidence = min(0.95, 0.6 + 0.1 * len(intents))
    return {
        'intent': intents[0],
        'intents': intents,
        'confidence': round(confidence, 2),
        'reasons': reasons,
        'rejected_intents': [],
    }
