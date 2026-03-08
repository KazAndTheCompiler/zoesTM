from pydantic import BaseModel, Field
from typing import Optional, List


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    due_at: Optional[str] = None
    priority: int = 2
    tags: List[str] = Field(default_factory=list)
    recurrence_rule: Optional[str] = None
    recurrence_parent_id: Optional[str] = None


class TaskOut(BaseModel):
    id: str
    title: str
    due_at: Optional[str] = None
    priority: int = 2
    tags: List[str] = Field(default_factory=list)
    done: bool = False


class TaskPatch(BaseModel):
    title: Optional[str] = None
    due_at: Optional[str] = None
    priority: Optional[int] = None
    tags: Optional[List[str]] = None


class QuickAddIn(BaseModel):
    text: str = Field(min_length=1, max_length=280)
    commit: bool = False


class QuickAddOut(BaseModel):
    title: str
    due_at: Optional[str] = None
    priority: int = 2
    tags: List[str] = Field(default_factory=list)
    confidence: float


import re

_TIME_RE = re.compile(r'^\d{1,2}:\d{2}$')
_ISO_RE  = re.compile(r'^\d{4}-\d{2}-\d{2}')

class AlarmIn(BaseModel):
    at: str = Field(..., description="'HH:MM' for daily or ISO 8601 for one-shot (e.g. '07:30' or '2026-03-05T07:30:00')")
    muted: bool = False
    kind: str = 'alarm'
    title: str = ''
    tts_text: str = ''
    youtube_link: str = ''

    def model_post_init(self, __context):
        at = (self.at or '').strip()
        if not at:
            raise ValueError("'at' is required — use 'HH:MM' or ISO 8601 datetime")
        if not (_TIME_RE.match(at) or _ISO_RE.match(at)):
            raise ValueError(f"'at' must be 'HH:MM' or ISO 8601 — got '{at}'")
        if _TIME_RE.match(at):
            hh, mm = at.split(':')
            if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
                raise ValueError(f"'at' time is out of range — got '{at}' (use 00-23 for hours, 00-59 for minutes)")
        self.at = at


class OpsImportIn(BaseModel):
    package: str
    checksum: str
    dry_run: bool = True


class CommandIn(BaseModel):
    text: str = Field(min_length=1, max_length=280)
    confirm: bool = False
