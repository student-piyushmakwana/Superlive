import logging
from app import create_app
from app.core.config import config

# Logging is already configured in app.core.config subclass instantiation (via import)


import asyncio
if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Patch for WinError 10054 in SelectorEventLoop
        # This suppresses the harmless "ConnectionResetError" spam
        import asyncio.selector_events
        _original_read_from_self = asyncio.selector_events.BaseSelectorEventLoop._read_from_self

        def _read_from_self_patched(self):
            try:
                _original_read_from_self(self)
            except OSError as e:
                # WinError 10054: An existing connection was forcibly closed by the remote host
                if getattr(e, 'winerror', None) != 10054:
                    raise

        asyncio.selector_events.BaseSelectorEventLoop._read_from_self = _read_from_self_patched

app = create_app()

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=config.DEBUG,
        use_reloader=True
    )
