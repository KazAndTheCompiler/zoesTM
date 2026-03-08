from fastapi import FastAPI


def get_openapi_payload(app: FastAPI):
    return {
        'version': 'v1',
        'spec': app.openapi(),
    }
