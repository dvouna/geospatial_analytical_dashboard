"""
utils/device.py
---------------
Server-side mobile device detection for the FLC26 dashboard.

Exposes two public functions:

  is_mobile_device() -> bool
      Reads the HTTP User-Agent header from the active WebSocket connection.
      Returns True when the UA string matches common mobile patterns.

  get_is_mobile() -> bool
      Session-state-cached wrapper around is_mobile_device().
      The header lookup fires once per browser session; subsequent Streamlit
      reruns read from st.session_state["is_mobile"] without any network call.

Notes
-----
- Uses the internal Streamlit API
  ``streamlit.web.server.websocket_headers._get_websocket_headers``.
  This has been stable across Streamlit 1.30–1.50.  The try/except block
  ensures the function defaults to desktop behaviour if the API ever changes.
- Detection is UA-string based and therefore a best-effort heuristic.
  It is used only to branch *component structure* (Python layout decisions).
  Visual styling uses CSS media queries which are independent of this utility.
"""

from __future__ import annotations

import streamlit as st

# Mobile UA substrings to match (case-insensitive)
_MOBILE_TOKENS = ("mobile", "android", "iphone", "ipad", "phone")


def is_mobile_device() -> bool:
    """Return True if the active browser session appears to be a mobile device.

    Reads the HTTP ``User-Agent`` header via Streamlit's internal WebSocket
    header API.  Falls back to ``False`` (desktop) on any exception so that
    a future Streamlit API change never breaks the dashboard.
    """
    try:
        from streamlit.web.server.websocket_headers import _get_websocket_headers

        headers = _get_websocket_headers()
        if headers:
            ua = headers.get("User-Agent", "").lower()
            return any(token in ua for token in _MOBILE_TOKENS)
    except Exception:
        pass
    return False


def get_is_mobile() -> bool:
    """Return the cached mobile-device flag for the current session.

    On the first call per browser session the UA header is inspected and the
    result is stored in ``st.session_state["is_mobile"]``.  All subsequent
    calls within the same session read from session state, avoiding repeated
    header lookups on every Streamlit rerun.
    """
    if "is_mobile" not in st.session_state:
        st.session_state["is_mobile"] = is_mobile_device()
    return st.session_state["is_mobile"]
