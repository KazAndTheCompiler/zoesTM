_CONNECTORS = {
    'local-calendar': {'name': 'local-calendar', 'auth': 'none', 'health': 'ok'},
    'desktop-player': {'name': 'desktop-player', 'auth': 'token', 'health': 'ok'},
}
_SYNC_STATE = {k: 'idle' for k in _CONNECTORS}
_LOCKS = set()


def list_connectors():
    return [{**v, 'sync_state': _SYNC_STATE.get(k, 'idle')} for k, v in _CONNECTORS.items()]


def run_sync(connector: str):
    if connector not in _CONNECTORS:
        return {'connector': connector, 'state': 'missing'}
    if connector in _LOCKS:
        return {'connector': connector, 'state': 'running'}
    _LOCKS.add(connector)
    try:
        _SYNC_STATE[connector] = 'running'
        _SYNC_STATE[connector] = 'idle'
        return {'connector': connector, 'state': 'idle', 'result': 'ok'}
    except Exception as exc:  # pragma: no cover
        _SYNC_STATE[connector] = 'failed'
        return {'connector': connector, 'state': 'failed', 'error': str(exc)}
    finally:
        _LOCKS.discard(connector)
