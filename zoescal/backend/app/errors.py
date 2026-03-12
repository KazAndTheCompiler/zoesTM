from dataclasses import dataclass
from typing import Any


@dataclass
class ApiError(Exception):
    code: str
    message: str
    status_code: int = 400
    details: Any | None = None


def error_payload(code: str, message: str, details: Any | None = None) -> dict:
    payload = {
        'code': code,
        'message': message,
    }
    if details is not None:
        payload['details'] = details
    return {'error': payload}


def bad_request(code: str, message: str, details: Any | None = None) -> ApiError:
    return ApiError(code=code, message=message, status_code=400, details=details)


def not_found(code: str, message: str, details: Any | None = None) -> ApiError:
    return ApiError(code=code, message=message, status_code=404, details=details)


def conflict(code: str, message: str, details: Any | None = None) -> ApiError:
    return ApiError(code=code, message=message, status_code=409, details=details)
