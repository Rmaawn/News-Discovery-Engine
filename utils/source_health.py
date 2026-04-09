# utils/source_health.py
from datetime import datetime, timedelta

_state = {}  # {source_name: {"fails": int, "blocked_until": datetime | None}}

FAIL_THRESHOLD = 3
BLOCK_MINUTES = 45


def is_blocked(source_name: str) -> bool:
    st = _state.get(source_name)
    if not st:
        return False
    bu = st.get("blocked_until")
    return bool(bu and datetime.now() < bu)


def mark_success(source_name: str):
    _state[source_name] = {"fails": 0, "blocked_until": None}


def mark_fail(source_name: str):
    st = _state.get(source_name, {"fails": 0, "blocked_until": None})
    st["fails"] += 1
    if st["fails"] >= FAIL_THRESHOLD:
        st["blocked_until"] = datetime.now() + timedelta(minutes=BLOCK_MINUTES)
        st["fails"] = 0
    _state[source_name] = st
