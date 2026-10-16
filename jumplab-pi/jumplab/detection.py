"""Explicit absence is preferable to an unvalidated contact detector."""

def propose():
    return {'available': False, 'method': None, 'events': None,
            'reason': 'No validated lightweight detector in version 0.1. Use manual contact inspection.',
            'tracking': 'not_run'}
