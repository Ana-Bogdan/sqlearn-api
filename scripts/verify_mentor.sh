#!/usr/bin/env bash
# Manual end-to-end verification for Milestone 13 (AI Mentor).
#
# Walks through:
#   1. Login (registers a fresh test account if needed)
#   2. Picks a published exercise
#   3. POSTs to /api/mentor/explain-error/ — expects available=true
#   4. POSTs 4× to /api/mentor/hint/  — expects levels 1, 2, 3 then hint_cap_reached
#   5. POSTs to /api/mentor/nl-to-sql/ — expects available=true
#   6. Promotes the test user to admin and lists /api/admin/mentor-logs/
#
# Usage:   bash scripts/verify_mentor.sh
# Cleanup: docker-compose exec api python manage.py shell -c \
#          "from django.contrib.auth import get_user_model; \
#           get_user_model().objects.filter(email='mentor-verify@example.com').delete()"

set -uo pipefail

API="${API:-http://localhost:8000}"
EMAIL="mentor-verify@example.com"
PASSWORD="Verify-Pass-1!"
COOKIES="$(mktemp -t sqlearn.cookies.XXXX)"
trap 'rm -f "$COOKIES"' EXIT

# --- pretty output --------------------------------------------------------
GREEN="\033[32m"; RED="\033[31m"; DIM="\033[2m"; RESET="\033[0m"
pass() { printf "  ${GREEN}✓${RESET} %s\n" "$1"; }
fail() { printf "  ${RED}✗${RESET} %s\n" "$1"; FAILED=$((FAILED+1)); }
hdr()  { printf "\n${DIM}── %s ──${RESET}\n" "$1"; }
FAILED=0

require_cmd() {
  command -v "$1" >/dev/null || { echo "Missing: $1"; exit 1; }
}
require_cmd curl
require_cmd python3

read_csrf_token() {
  # Pull the csrftoken value out of the curl Netscape cookie jar (col 7)
  awk '$6 == "csrftoken" {print $7}' "$COOKIES" | tail -n1
}

http() {
  # http METHOD PATH [JSON_BODY]
  # Automatically attaches X-CSRFToken on unsafe methods so authenticated
  # POSTs pass CookieJWTAuthentication.enforce_csrf().
  local method="$1" path="$2" body="${3-}"
  local args=(-s -o /tmp/_mentor_resp.json -w "%{http_code}" -X "$method"
              -c "$COOKIES" -b "$COOKIES"
              -H "Content-Type: application/json"
              -H "Referer: $API/")
  if [ "$method" != "GET" ] && [ "$method" != "HEAD" ]; then
    local token
    token=$(read_csrf_token)
    [ -n "$token" ] && args+=(-H "X-CSRFToken: $token")
  fi
  args+=("$API$path")
  [ -n "$body" ] && args+=(-d "$body")
  curl "${args[@]}"
}

json_field() {
  # Read a top-level key out of /tmp/_mentor_resp.json, e.g. json_field available
  python3 - "$1" <<'PY'
import json, sys
key = sys.argv[1]
try:
    val = json.load(open("/tmp/_mentor_resp.json")).get(key)
    print("<missing>" if val is None else val)
except Exception:
    print("<unparseable>")
PY
}

# -------------------------------------------------------------------------
# 1. Login (or register)
# -------------------------------------------------------------------------
hdr "1. Auth"
code=$(http POST /api/auth/login/ "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
if [ "$code" != "200" ]; then
  printf "  login → %s, registering...\n" "$code"
  code=$(http POST /api/auth/register/ \
    "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"first_name\":\"Verify\",\"last_name\":\"Bot\"}")
  if [ "$code" = "200" ] || [ "$code" = "201" ]; then
    pass "registered"
  else
    fail "register returned $code"
    cat /tmp/_mentor_resp.json; exit 1
  fi
else
  pass "logged in"
fi

# Fetch a fresh csrftoken so authenticated POSTs pass CookieJWTAuthentication.enforce_csrf().
# Django rotates the token on login, so we must re-fetch it after auth.
http GET /api/auth/csrf/ >/dev/null
if [ -n "$(read_csrf_token)" ]; then
  pass "csrftoken cookie obtained"
else
  fail "csrftoken cookie missing — POSTs will fail with 403 CSRF"
fi

# Wipe prior mentor logs for this test user so the hint cap, rate limit,
# and admin row count all start from a clean slate. Without this, re-runs
# fail because the service correctly remembers prior hints across runs.
docker-compose exec -T api python manage.py shell -c "
from apps.mentor.models import AIRequestLog
from django.contrib.auth import get_user_model
u = get_user_model().objects.filter(email='$EMAIL').first()
if u:
    n, _ = AIRequestLog.objects.filter(user=u).delete()
    print(f'wiped {n} prior log rows')
" >/tmp/_mentor_wipe.log 2>&1 && pass "$(cat /tmp/_mentor_wipe.log | tail -1)" || fail "couldn't wipe prior logs"

# -------------------------------------------------------------------------
# 2. Pick an exercise from /api/chapters/ → /api/chapters/{id}/ → /api/lessons/{id}/
# -------------------------------------------------------------------------
hdr "2. Exercise lookup"
code=$(http GET /api/chapters/)
CH_ID=$(python3 - <<'PY'
import json
d = json.load(open('/tmp/_mentor_resp.json'))
chapters = d if isinstance(d, list) else d.get('results', [])
print(chapters[0]['id'] if chapters else '')
PY
)
if [ -z "$CH_ID" ]; then
  fail "no chapters returned — did you run 'python manage.py seed_curriculum'?"
  cat /tmp/_mentor_resp.json; exit 1
fi

# Walk chapters until we find one with a lesson that has at least one exercise
EX_ID=""
for offset in 0 1 2 3 4 5 6 7; do
  CH_ID=$(python3 - "$offset" <<'PY'
import json, sys
d = json.load(open('/tmp/_mentor_resp.json'))
chapters = d if isinstance(d, list) else d.get('results', [])
i = int(sys.argv[1])
print(chapters[i]['id'] if i < len(chapters) else '')
PY
)
  [ -z "$CH_ID" ] && break
  http GET "/api/chapters/$CH_ID/" >/dev/null
  LESSON_IDS=$(python3 - <<'PY'
import json
d = json.load(open('/tmp/_mentor_resp.json'))
print(' '.join(str(l['id']) for l in d.get('lessons', [])))
PY
)
  for LESSON_ID in $LESSON_IDS; do
    http GET "/api/lessons/$LESSON_ID/" >/dev/null
    EX_ID=$(python3 - <<'PY'
import json
d = json.load(open('/tmp/_mentor_resp.json'))
for ex in d.get('exercises', []):
    print(ex['id']); break
PY
)
    [ -n "$EX_ID" ] && break
  done
  [ -n "$EX_ID" ] && break
  # Re-fetch the chapters list for the next iteration
  http GET /api/chapters/ >/dev/null
done

if [ -z "$EX_ID" ]; then
  fail "couldn't find any exercise — is the curriculum seeded with published exercises?"
  exit 1
fi
pass "using exercise id=$EX_ID (chapter $CH_ID, lesson $LESSON_ID)"

# -------------------------------------------------------------------------
# 3. Explain-error
# -------------------------------------------------------------------------
hdr "3. /api/mentor/explain-error/"
body=$(printf '{"exercise_id":%s,"sql_text":"SELECT * FORM students;","error_message":"syntax error at or near \\"FORM\\""}' "$EX_ID")
for attempt in 1 2 3; do
  code=$(http POST /api/mentor/explain-error/ "$body")
  [ "$code" = "200" ] || { fail "HTTP $code"; cat /tmp/_mentor_resp.json; break; }
  avail=$(json_field available)
  if [ "$avail" = "True" ]; then
    pass "available=true (Gemini responded)"
    break
  fi
  if [ "$attempt" = "3" ]; then
    fail "available=$avail after 3 attempts — Gemini is flaky right now (or check GEMINI_API_KEY)"
  else
    printf "    ${DIM}attempt $attempt fell back, retrying in 2s...${RESET}\n"
    sleep 2
  fi
done
msg_excerpt=$(python3 -c "import json; print(json.load(open('/tmp/_mentor_resp.json')).get('message',''))" | head -c 120)
printf "    ${DIM}preview: %s…${RESET}\n" "$msg_excerpt"

# -------------------------------------------------------------------------
# 4. Hints — levels 1, 2, 3, then cap
# -------------------------------------------------------------------------
hdr "4. /api/mentor/hint/  (4 calls)"
for i in 1 2 3; do
  # Retry up to 3 times if Gemini falls back (e.g. transient 503 that
  # squeaks past the service-side retry). Fallback responses don't
  # increment the hint counter, so re-trying keeps us on track to assert
  # the level progression.
  for attempt in 1 2 3; do
    code=$(http POST /api/mentor/hint/ "{\"exercise_id\":$EX_ID,\"sql_text\":\"\"}")
    avail=$(json_field available)
    level=$(json_field hint_level)
    remaining=$(json_field hints_remaining)
    if [ "$avail" = "True" ] && [ "$level" = "$i" ]; then
      pass "hint $i → level=$level, remaining=$remaining"
      break
    fi
    if [ "$attempt" = "3" ]; then
      fail "hint $i → expected available=true level=$i, got available=$avail level=$level"
    else
      printf "    ${DIM}hint $i attempt $attempt fell back (avail=$avail), retrying...${RESET}\n"
      sleep 2
    fi
  done
done
# 4th — should be capped
code=$(http POST /api/mentor/hint/ "{\"exercise_id\":$EX_ID,\"sql_text\":\"\"}")
avail=$(json_field available)
outcome=$(json_field outcome)
if [ "$avail" = "False" ] && [ "$outcome" = "hint_cap_reached" ]; then
  pass "hint 4 correctly capped (available=false, outcome=hint_cap_reached)"
else
  fail "hint 4 should be capped — got available=$avail outcome=$outcome"
fi

# -------------------------------------------------------------------------
# 5. NL → SQL
# -------------------------------------------------------------------------
hdr "5. /api/mentor/nl-to-sql/"
body=$(printf '{"exercise_id":%s,"natural_language":"give me everything in the first table"}' "$EX_ID")
for attempt in 1 2 3; do
  code=$(http POST /api/mentor/nl-to-sql/ "$body")
  avail=$(json_field available)
  if [ "$avail" = "True" ]; then
    pass "available=true"
    break
  fi
  if [ "$attempt" = "3" ]; then
    fail "available=$avail after 3 attempts — Gemini is flaky right now"
  else
    printf "    ${DIM}attempt $attempt fell back, retrying in 2s...${RESET}\n"
    sleep 2
  fi
done

# -------------------------------------------------------------------------
# 6. Admin endpoint — promote, re-login, list logs
# -------------------------------------------------------------------------
hdr "6. /api/admin/mentor-logs/"
docker-compose exec -T api python manage.py shell -c "
from django.contrib.auth import get_user_model
u = get_user_model().objects.get(email='$EMAIL')
u.role = 'admin'; u.is_staff = True; u.is_superuser = True; u.save()
" >/dev/null 2>&1 && pass "promoted to admin" || fail "couldn't promote — is docker-compose available?"

# Re-login so the JWT carries the admin role, then refresh the csrftoken
http POST /api/auth/login/ "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" >/dev/null
http GET /api/auth/csrf/ >/dev/null

code=$(http GET "/api/admin/mentor-logs/?page_size=20")
count=$(json_field count)
if [ "$code" = "200" ] && [ -n "$count" ] && [ "$count" != "<missing>" ]; then
  pass "admin endpoint OK — $count log rows recorded"
else
  fail "admin endpoint HTTP $code count=$count"
fi

# -------------------------------------------------------------------------
hdr "Result"
if [ "$FAILED" = "0" ]; then
  printf "${GREEN}All checks passed.${RESET}\n"
  exit 0
else
  printf "${RED}%s checks failed.${RESET}\n" "$FAILED"
  exit 1
fi
