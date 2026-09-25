#!/usr/bin/env bash
# revert.sh — one-command revert for the Retell proxy-guard setup.
#
#   revert.sh           -> status/dry-run: show current rules + cron entry
#   revert.sh iptables  -> remove the two Retell REDIRECT rules + persist
#   revert.sh all       -> iptables + remove the hourly guard cron entry
#
# WARNING after `iptables`/`all`: processes outside opencode.slice keep being
# proxied via the catch-all rule, but opencode.slice Retell traffic goes
# DIRECT again (the pre-fix leak this setup was built to close).
set -u

IPT='sudo -n /usr/sbin/iptables'
CRON_MARKER='retell_guard.sh'

show() {
    echo "== Retell rules currently in REDSOCKS chain:"
    $IPT -t nat -S REDSOCKS | grep -E '3\.33\.169\.178|13\.248\.202\.14' || echo "(none)"
    echo "== Guard cron entry:"
    crontab -l 2>/dev/null | grep "$CRON_MARKER" || echo "(none)"
}

case "${1:-check}" in
check)
    show
    ;;
iptables)
    $IPT -t nat -D REDSOCKS -d 3.33.169.178/32 -p tcp -j REDIRECT --to-ports 12345 \
        && echo "removed rule: 3.33.169.178" || echo "rule 3.33.169.178 not present"
    $IPT -t nat -D REDSOCKS -d 13.248.202.14/32 -p tcp -j REDIRECT --to-ports 12345 \
        && echo "removed rule: 13.248.202.14" || echo "rule 13.248.202.14 not present"
    sudo -n /usr/sbin/netfilter-persistent save
    echo "Persisted. NOTE: opencode.slice Retell traffic now goes DIRECT (pre-fix state)."
    show
    ;;
all)
    crontab -l 2>/dev/null | grep -v "$CRON_MARKER" | crontab -
    echo "Guard cron entry removed (all other cron entries untouched)."
    exec "$0" iptables
    ;;
*)
    echo "usage: $0 [check|iptables|all]"
    exit 1
    ;;
esac
