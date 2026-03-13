from fastapi import APIRouter, Request
from ..services.openapi_meta import get_openapi_payload

router = APIRouter()
APP_VERSION = '1.0.0-rc1'


@router.get('')
def meta_summary():
    return {'version': APP_VERSION, 'app_version': APP_VERSION}


@router.get('/openapi')
def openapi_spec(request: Request):
    return get_openapi_payload(request.app)


@router.get('/version')
def version():
    return {'app_version': APP_VERSION}


# Endpoints map:
# Owner: platform-domain
# GET /meta/openapi
# GET /meta/version
