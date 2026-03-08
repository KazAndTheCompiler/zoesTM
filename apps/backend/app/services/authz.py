import json
import os
import uuid
from fastapi import Header, HTTPException
from ..db import tx


def _audit_failure(details: dict):
    with tx() as c:
        c.execute(
            "INSERT INTO audit_logs(id,category,details_json) VALUES(?,?,?)",
            (str(uuid.uuid4()), 'auth.failure', json.dumps(details)),
        )


def require_scopes(required: set[str]):
    async def dep(x_token_scopes: str | None = Header(default="")):
        # Dev bypass for local skeleton runs
        if os.getenv('ZOESTM_DEV_AUTH', '0') == '1':
            return True

        given = {s.strip() for s in (x_token_scopes or '').split(',') if s.strip()}
        if not required.issubset(given):
            details = {'required': sorted(required), 'given': sorted(given)}
            _audit_failure(details)
            raise HTTPException(status_code=403, detail='forbidden')
        return True

    return dep
