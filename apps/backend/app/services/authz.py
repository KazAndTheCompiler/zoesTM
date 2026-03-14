import json
import os
import uuid
from urllib.parse import urlparse
from fastapi import Header, HTTPException, Request
from ..db import tx


def _audit_failure(details: dict):
    with tx() as c:
        c.execute(
            "INSERT INTO audit_logs(id,category,details_json) VALUES(?,?,?)",
            (str(uuid.uuid4()), 'auth.failure', json.dumps(details)),
        )


def _is_local_origin(value: str | None) -> bool:
    if not value:
        return False
    if value.startswith('app://') or value.startswith('file://'):
        return True
    try:
        parsed = urlparse(value)
    except Exception:
        return False
    host = (parsed.hostname or '').lower()
    return host in {'127.0.0.1', 'localhost'}


def _trust_local_client(request: Request) -> bool:
    trust_local = os.getenv('ZOESTM_TRUST_LOCAL_CLIENTS', '1') == '1'
    enforce_auth = os.getenv('ZOESTM_ENFORCE_AUTH', '0') == '1'
    if not trust_local or enforce_auth:
        return False

    origin = request.headers.get('origin')
    referer = request.headers.get('referer')
    host = request.headers.get('host', '')
    if origin:
        return _is_local_origin(origin)
    if referer:
        return _is_local_origin(referer)
    if host.startswith('127.0.0.1:') or host.startswith('localhost:'):
        return True
    return False


def require_scopes(required: set[str]):
    async def dep(request: Request, x_token_scopes: str | None = Header(default="")):
        # Explicit dev bypass for local skeleton runs
        if os.getenv('ZOESTM_DEV_AUTH', '0') == '1':
            return True

        # First-party local clients can use the shared local trust boundary unless auth enforcement is enabled.
        if _trust_local_client(request):
            return True

        given = {s.strip() for s in (x_token_scopes or '').split(',') if s.strip()}
        if not required.issubset(given):
            details = {
                'required': sorted(required),
                'given': sorted(given),
                'origin': request.headers.get('origin', ''),
                'host': request.headers.get('host', ''),
            }
            _audit_failure(details)
            raise HTTPException(status_code=403, detail='forbidden')
        return True

    return dep
