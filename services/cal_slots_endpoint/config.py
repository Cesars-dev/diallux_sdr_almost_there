import json
import os

_CAL_ACCOUNTS_RAW = os.environ.get("CAL_ACCOUNTS", "")
_CAL_ACCOUNTS: dict = {}


def retell_badge_keys() -> list[str]:
    """Return the set of Retell webhook-badge API keys the service will accept.

    Production-ready: accepts MANY badge keys (one per calling Retell account/workspace)
    via `RETELL_API_KEYS` (JSON array). Falls back to the legacy single `RETELL_API_KEY`.
    This mirrors CAL_ACCOUNTS (multi Cal.com key) — here it's multi Retell key.
    """
    keys: list[str] = []
    raw = os.environ.get("RETELL_API_KEYS", "")
    if raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                keys = [str(k).strip() for k in parsed if str(k).strip()]
        except json.JSONDecodeError:
            # tolerate a comma-separated list too
            keys = [k.strip() for k in raw.split(",") if k.strip()]
    legacy = os.environ.get("RETELL_API_KEY", "")
    if legacy and legacy not in keys:
        keys.append(legacy)
    return keys

if _CAL_ACCOUNTS_RAW:
    try:
        _CAL_ACCOUNTS = json.loads(_CAL_ACCOUNTS_RAW)
    except json.JSONDecodeError:
        raise SystemExit("cal_slots: CAL_ACCOUNTS env is not valid JSON")


def resolve(account_id: str | None = None) -> dict:
    if _CAL_ACCOUNTS:
        key = account_id or next(iter(_CAL_ACCOUNTS))
        if key not in _CAL_ACCOUNTS:
            return None
        acct = _CAL_ACCOUNTS[key]
        return {
            "account_id": key,
            "cal_api_key": acct["cal_api_key"],
            "event_type_id": str(acct["event_type_id"]),
            "timezone": acct.get("timezone", "Europe/London"),
            "duration": int(acct.get("duration", os.environ.get("SLOT_DURATION_MIN", "60"))),
            "include_iso": acct.get("include_iso", True),
            "attendee_email": acct.get("attendee_email", os.environ.get("ATTENDEE_EMAIL", "jaydiallux@gmail.com")),
        }
    return {
        "account_id": None,
        "cal_api_key": os.environ.get("CAL_COM_API_KEY", ""),
        "event_type_id": os.environ.get("EVENT_TYPE_ID", ""),
        "timezone": os.environ.get("TIMEZONE", "Europe/London"),
        "duration": int(os.environ.get("SLOT_DURATION_MIN", "60")),
        "attendee_email": os.environ.get("ATTENDEE_EMAIL", "jaydiallux@gmail.com"),
    }


def default_account_id() -> str | None:
    if _CAL_ACCOUNTS:
        return next(iter(_CAL_ACCOUNTS))
    return None
