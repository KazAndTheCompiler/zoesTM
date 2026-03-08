from fastapi import APIRouter
from ..repositories import predownload_repo
from ..repositories import player_queue_repo
from ..services.player import rotate_queue
import subprocess
import shutil
import sys

router = APIRouter()


@router.post('/resolve-url')
def resolve_url(url: str = '', body: dict = {}):
    """Use yt-dlp to extract a direct stream URL from a YouTube link.
    Returns the best audio stream URL so the frontend <audio> tag can play it directly.
    No download — just URL extraction.
    """
    target = url or body.get('url', '')
    if not target:
        return {'error': 'no url provided', 'stream_url': None}

    yt_dlp = shutil.which('yt-dlp')
    cmd_prefix = [yt_dlp] if yt_dlp else [sys.executable, '-m', 'yt_dlp']

    try:
        result = subprocess.run(
            [*cmd_prefix, '-f', 'bestaudio', '-g', '--no-playlist', target],
            capture_output=True, text=True, timeout=15
        )
        stream_url = result.stdout.strip().splitlines()[0] if result.returncode == 0 else None
        error = result.stderr.strip() if not stream_url else None
        hint = 'Install yt-dlp in backend venv: .venv/bin/pip install yt-dlp' if (not stream_url and 'No module named yt_dlp' in (error or '')) else None
        return {'stream_url': stream_url, 'error': error, 'hint': hint}
    except subprocess.TimeoutExpired:
        return {'error': 'yt-dlp timed out', 'stream_url': None}
    except Exception as e:
        return {'error': str(e), 'stream_url': None}


@router.post('/predownload/enqueue')
def enqueue(track_ref: str):
    return predownload_repo.enqueue(track_ref)


@router.get('/predownload/status')
def status(limit: int = 100):
    return {'items': predownload_repo.list_jobs(limit)}


@router.post('/predownload/retry/{job_id}')
def retry(job_id: str):
    return predownload_repo.retry_failed(job_id)


@router.post('/predownload/tick/{job_id}')
def tick(job_id: str):
    job = predownload_repo.advance_job(job_id)
    return {'job': job, 'progression': predownload_repo.progression_states()}


@router.post('/queue')
def replace_local_queue(items: list[str]):
    rotated = rotate_queue(items, max_items=20)
    saved = player_queue_repo.replace(rotated, max_items=20)
    return {'items': saved, 'count': len(saved)}


@router.get('/queue')
def get_local_queue():
    items = player_queue_repo.list_items()
    return {'items': items, 'count': len(items)}


@router.post('/queue/next')
def pop_local_queue():
    now_playing = player_queue_repo.pop_next()
    remaining = player_queue_repo.list_items()
    return {'now_playing': now_playing, 'remaining': remaining}


# Endpoints map:
# Owner: player-domain
# POST /player/predownload/enqueue?track_ref=...
# GET /player/predownload/status?limit=100
# POST /player/predownload/retry/{job_id}
# POST /player/predownload/tick/{job_id}
# POST /player/queue
# GET /player/queue
# POST /player/queue/next
