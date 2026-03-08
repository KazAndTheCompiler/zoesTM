"""
Cross-platform TTS service.
- Linux:   espeak-ng (apt install espeak-ng)
- macOS:   say (built-in)
- Windows: PowerShell Add-Type speech (built-in)

Runs in a background thread so it never blocks the API.
"""
import logging
import platform
import shutil
import subprocess
import threading

logger = logging.getLogger(__name__)


def _speak_linux(text: str):
    cmd = shutil.which('espeak-ng') or shutil.which('espeak')
    if not cmd:
        logger.warning('[tts] espeak-ng not found — install with: sudo apt install espeak-ng')
        return
    subprocess.run([cmd, text], timeout=30)


def _speak_macos(text: str):
    subprocess.run(['say', text], timeout=30)


def _speak_windows(text: str):
    # Use PowerShell's built-in speech synthesizer
    script = f'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{text}")'
    subprocess.run(['powershell', '-Command', script], timeout=30)


def speak(text: str):
    """Speak text aloud in a background thread — non-blocking."""
    if not text or not text.strip():
        return

    def _run():
        try:
            system = platform.system()
            if system == 'Linux':
                _speak_linux(text)
            elif system == 'Darwin':
                _speak_macos(text)
            elif system == 'Windows':
                _speak_windows(text)
            else:
                logger.warning(f'[tts] unknown platform: {system}')
        except subprocess.TimeoutExpired:
            logger.warning('[tts] speech timed out')
        except Exception as e:
            logger.error(f'[tts] error: {e}')

    t = threading.Thread(target=_run, daemon=True)
    t.start()
