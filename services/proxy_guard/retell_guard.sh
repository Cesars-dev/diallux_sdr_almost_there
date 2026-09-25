#!/usr/bin/env bash
# retell_guard.sh — hourly DNS watch over api.retellai.com (Retell AI).
#
# Policy:
#   - Silent unless something changes. No hourly output, no hourly messages.
#   - IPv4 drift  -> log line in logs/guard.log ONLY (no telegram).
#   - IPv6 change -> log line + ONE Telegram message (deduped until it changes again).
#   - Resolver outage -> log line only, retried next hour.
#
# Usage:
#   retell_guard.sh             # normal run (cron)
#   retell_guard.sh --selftest  # send one labeled TEST telegram to verify the pipe
#
# Blocking is NOT done here — it's the iptables REDSOCKS rules. See README.md.
set -u

GUARD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGS="$GUARD_DIR/logs"
LOG="$LOGS/guard.log"
LAST_RUN="$LOGS/last_run"
LAST_V6="$LOGS/last_alerted_v6"

DOMAIN="api.retellai.com"
RESOLVERS=(1.1.1.1 8.8.8.8)

# Known-good state. Update ONLY after verifying a real change (RUNBOOK.md A/B).
KNOWN_V4="13.248.202.14 3.33.169.178"
KNOWN_V6=""

# Telegram creds are NOT copied into this repo (it's git) — read from Voicemail_drops.
TELEGRAM_ENV="/home/julio/projects/Voicemail_drops/.env"

mkdir -p "$LOGS"
now() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
log() { echo "[$(now)] $*" >> "$LOG"; }

norm() { echo "$1" | tr ' ' '\n' | sed '/^$/d' | sort -u | tr '\n' ' ' | sed 's/ $//'; }

resolve() {
    local type="$1" r out
    for r in "${RESOLVERS[@]}"; do
        out=$(dig +short "@$r" "$DOMAIN" "$type" 2>/dev/null)
        if [ $? -eq 0 ]; then
            echo "$out" | grep -E '^[0-9a-fA-F:.]+$' | sort -u
            return 0
        fi
    done
    return 1
}

telegram() {
    local token chat
    token=$(sed -n 's/^TELEGRAM_BOT_TOKEN=//p' "$TELEGRAM_ENV" 2>/dev/null)
    chat=$(sed -n 's/^TELEGRAM_CHAT_ID=//p' "$TELEGRAM_ENV" 2>/dev/null)
    if [ -z "$token" ] || [ -z "$chat" ]; then
        log "WARN telegram credentials not found in $TELEGRAM_ENV"
        return 1
    fi
    python3 - "$token" "$chat" "$1" <<'PY'
import json, sys, urllib.request
token, chat, text = sys.argv[1], sys.argv[2], sys.argv[3]
data = json.dumps({"chat_id": chat, "text": text}).encode()
req = urllib.request.Request(
    f"https://api.telegram.org/bot{token}/sendMessage",
    data=data, headers={"Content-Type": "application/json"})
print(urllib.request.urlopen(req, timeout=30).status)
PY
}

if [ "${1:-}" = "--selftest" ]; then
    log "SELFTEST sending one-time test telegram"
    if telegram "🧪 TEST retell-guard setup — Telegram pipe works. Real messages fire ONLY if api.retellai.com changes its IPv6 (AAAA) records."; then
        log "SELFTEST telegram sent OK"
        echo "selftest: telegram sent OK"
    else
        log "SELFTEST telegram FAILED"
        echo "selftest: telegram FAILED" >&2
        exit 1
    fi
    exit 0
fi

V4=$(resolve A) || { log "CHECK-FAILED all resolvers unreachable — no alert, retry next hour"; exit 0; }
V6=$(resolve AAAA) || V6=""

N4=$(norm "$V4"); K4=$(norm "$KNOWN_V4")
N6=$(norm "$V6"); K6=$(norm "$KNOWN_V6")

touch "$LAST_RUN"

if [ "$N4" != "$K4" ]; then
    log "V4-DRIFT now=[$N4] expected=[$K4] — log-only per policy, see RUNBOOK.md scenario A"
fi

LAST_ALERTED=$(norm "$(cat "$LAST_V6" 2>/dev/null || true)")
[ -z "$LAST_ALERTED" ] && LAST_ALERTED="$K6"

if [ "$N6" != "$LAST_ALERTED" ]; then
    if [ "$N6" = "$K6" ]; then
        STATUS="RESOLVED — IPv6 records are back to the expected state"
    else
        STATUS="CHANGED — IPv6 can BYPASS the redsocks proxy and leak the direct VPS IP"
    fi
    MSG="🚨 retell-guard: $DOMAIN
IPv6 $STATUS.
now=[$N6] expected=[$K6]
Retell calls could exit via the DIRECT VPS IP instead of the proxy.
→ Run: $GUARD_DIR/RUNBOOK.md (scenario B)"
    log "V6-CHANGE now=[$N6] expected=[$K6] last_alerted=[$LAST_ALERTED] — sending telegram"
    if telegram "$MSG"; then
        echo "$N6" > "$LAST_V6"
        log "V6-CHANGE telegram delivered"
    else
        log "V6-CHANGE telegram FAILED — will retry next run"
    fi
elif [ "$N6" = "$K6" ] && [ -f "$LAST_V6" ]; then
    rm -f "$LAST_V6"
fi

exit 0
