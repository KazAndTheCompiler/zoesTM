from random import choice
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse


router = APIRouter()

QUOTES = [
    "Stop waiting for motivation. Build systems that expose your excuses.",
    "Accountability is the mirror most people avoid because it tells the truth.",
    "Callous your mind by doing the work you keep negotiating with.",
    "You do not need a better mood. You need better standards.",
    "The truth is simple: you keep quitting when it gets inconvenient.",
    "Discipline is choosing the hard thing before life chooses it for you.",
    "If you need hype to start, you are still owned by comfort.",
    "Your feelings are not a project manager. Finish the task anyway.",
    "Every excuse you protect becomes a ceiling you live under.",
    "The weak look for inspiration. The strong audit their habits.",
    "You are not overworked. You are under-disciplined in the moments that matter.",
    "Confidence comes from receipts, not affirmations.",
    "The calloused mind is built in the reps nobody claps for.",
    "Most people want relief. Very few want responsibility.",
    "Get honest about your habits and the story changes fast.",
    "You keep saying later because later lets you avoid judgment now.",
    "Being soft is expensive. You pay for it in every missed standard.",
    "Real growth starts when you stop asking your mood for permission.",
    "Comfort is a slow addiction that makes average feel normal.",
    "When you face the truth daily, excuses lose oxygen.",
]

STATIC_DIR = Path(__file__).resolve().parents[2] / "static"
GOGGINS_MP3 = STATIC_DIR / "goggins.mp3"


@router.get("/quote")
def random_quote():
    return {"quote": choice(QUOTES)}


@router.post("/trigger")
def trigger_goggins():
    if not GOGGINS_MP3.exists():
        raise HTTPException(status_code=404, detail="Goggins audio not found")
    return FileResponse(GOGGINS_MP3, media_type="audio/mpeg", filename="goggins.mp3")


# Endpoints map:
# Owner: zoestm-goggins-domain
# GET  /goggins/quote
# POST /goggins/trigger
