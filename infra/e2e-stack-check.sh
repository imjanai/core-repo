#!/usr/bin/env bash
#
# infra/e2e-stack-check.sh — end-to-end-verificatie van de draaiende stack.
#
# Voorwaarde: de stack draait al, bv.:
#     docker compose -f infra/docker-compose.yml up -d --build
#
# Wat er bewezen wordt:
#   A. Upload van een DXF → Celery-worker draait de pipeline → run slaagt,
#      project heeft symbolen én materialen.
#   B. Sweeper: een gezaaide "gestrande" run met max hervatpogingen wordt
#      definitief gefaald met de verwachte melding.
#   C. Handmatig hervatten: POST .../pipeline/resume op een gefaalde run
#      geeft 202 en de hervatte run voltooit alsnog.
#   D. Sweeper-herstel: een verse gestrande run wordt automatisch opgepakt
#      en alsnog voltooid.
#
# Draai vanaf de repo-root. Sluit af met `docker compose -f
# infra/docker-compose.yml down` als je de stack wilt stoppen.
set -euo pipefail

COMPOSE_FILE="infra/docker-compose.yml"
API="http://localhost:8080"
POLL_API="${POLL_API:-300}"    # max seconden voor een pipeline-run
POLL_SWEEP="${POLL_SWEEP:-120}"  # max seconden voor een sweeper-tick

log()  { printf '\n== %s\n' "$*"; }
fail() { printf 'MISLUKT: %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || fail "docker niet gevonden; installeer Docker of draai dit op een machine met Docker."
docker compose version >/dev/null 2>&1 || fail "docker compose-plugin ontbreekt."
command -v curl >/dev/null 2>&1 || fail "curl niet gevonden."

COMPOSE=(docker compose -f "$COMPOSE_FILE")

# JSON uitlezen met de Python ín de api-container (geen jq/python op de host nodig).
api_py() { "${COMPOSE[@]}" exec -T api python -c "$1"; }
db_sql() { "${COMPOSE[@]}" exec -T db psql -U elektro -d elektro -tA -c "$1"; }

log "Wachten tot de API gezond is..."
for _ in $(seq 1 60); do
    if curl -sf "$API/health" | grep -q '"db": *"ok"'; then break; fi
    sleep 2
done
curl -sf "$API/health" | grep -q '"db": *"ok"' || fail "API wordt niet gezond op $API."

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# --------------------------------------------------------------------------- A
log "A: DXF genereren en uploaden..."
"${COMPOSE[@]}" exec -T api python - <<'PY' > "$TMP/demo.dxf"
import io
import ezdxf

doc = ezdxf.new("R2010")
doc.units = ezdxf.units.MM  # millimeter — anders interpreteert ezdxf dit als meter
msp = doc.modelspace()
blk = doc.blocks.new("WCD_STANDAARD")
blk.add_circle((0, 0), radius=10)
msp.add_blockref("WCD_STANDAARD", (1000.0, 1000.0))
msp.add_blockref("WCD_STANDAARD", (1400.0, 1000.0))
msp.add_text("Woonkamer", dxfattribs={"insert": (1200.0, 1200.0)})
msp.add_text("G1", dxfattribs={"insert": (1050.0, 1050.0)})
buf = io.StringIO()
doc.write(buf)
print(buf.getvalue(), end="")
PY
[ -s "$TMP/demo.dxf" ] || fail "DXF-generatie leverde een leeg bestand op."

resp="$(curl -sf -F "file=@$TMP/demo.dxf;filename=demo.dxf" "$API/projects")" \
    || fail "Upload endpoint gaf geen succes."
project_id="$(printf '%s' "$resp" | api_py 'import json,sys; print(json.load(sys.stdin)["id"])')"
[ -n "$project_id" ] || fail "Geen project-id teruggekregen."
echo "project_id=$project_id"

log "A: wachten tot de pipeline voltooid is (max ${POLL_API}s)..."
state=""
for _ in $(seq 1 "$POLL_API"); do
    state="$(curl -sf "$API/projects/$project_id/pipeline" \
        | api_py 'import json,sys; print(json.load(sys.stdin)["state"])' || echo onbereikbaar)"
    case "$state" in succeeded|failed|cancelled) break ;; esac
    sleep 1
done
[ "$state" = "succeeded" ] || fail "Pipeline eindigde in state '$state' (verwacht: succeeded)."
echo "state=succeeded ✓"

counts="$(curl -sf "$API/projects/$project_id" \
    | api_py 'import json,sys; d=json.load(sys.stdin); print(len(d["symbols"]), len(d["materials"]))')"
symbols="${counts%% *}"; materials="${counts##* }"
[ "$symbols" -ge 1 ] || fail "Geen symbolen in het project."
[ "$materials" -ge 1 ] || fail "Geen materialen berekend."
echo "symbolen=$symbols materialen=$materials ✓"

# --------------------------------------------------------------------------- B
log "B: gezaaide gestrande run (max hervatpogingen) moet de sweeper laten opgeven..."
stuck_giveup="$(db_sql "INSERT INTO pipeline_runs (run_id, project_id, state, error, stages, project_snapshot, payload, created_at, updated_at)
    VALUES (gen_random_uuid(), '$project_id', 'pending', 'e2e-gezaaid', '[]', '{}', '{\"resume_count\": 3}', now(), now() - interval '1 hour')
    RETURNING run_id;")"
echo "run_id=$stuck_giveup"
result=""
for _ in $(seq 1 "$POLL_SWEEP"); do
    result="$(db_sql "SELECT state || '|' || coalesce(error, '') FROM pipeline_runs WHERE run_id = '$stuck_giveup';")"
    case "$result" in pending*|running*) sleep 1 ;; *) break ;; esac
done
case "$result" in
    failed\|*"handmatige inspectie"*) echo "$result ✓" ;;
    *) fail "Sweeper gaf de run niet definitief op (kreeg: '$result')." ;;
esac

# --------------------------------------------------------------------------- C
log "C: gefaalde run handmatig hervatten via de API..."
resumable="$(db_sql "INSERT INTO pipeline_runs (run_id, project_id, state, error, stages, project_snapshot, payload, created_at, updated_at)
    VALUES (gen_random_uuid(), '$project_id', 'failed', 'e2e-gezaaid', '[]', '{}', '{}', now(), now() - interval '1 hour')
    RETURNING run_id;")"
resume_resp="$(curl -sf -X POST "$API/projects/$project_id/pipeline/resume")" \
    || fail "Resume-endpoint gaf geen succes."
resume_ids="$(printf '%s' "$resume_resp" | api_py 'import json,sys; d=json.load(sys.stdin); assert d["state"]=="queued", d; print(d["run_id"], d["task_id"] or "")')"
resumed_id="${resume_ids%% *}"
task_id="${resume_ids##* }"
[ "$resumed_id" = "$resumable" ] || fail "Resume pakte run '$resumed_id' in plaats van de gezaaide '$resumable'."
[ -n "$task_id" ] || fail "Resume gaf geen Celery-taak-id."
echo "202 + task_id=$task_id ✓"

state=""
for _ in $(seq 1 "$POLL_API"); do
    result="$(db_sql "SELECT state FROM pipeline_runs WHERE run_id = '$resumable';")"
    case "$result" in succeeded|failed|cancelled) state="$result"; break ;; esac
    sleep 1
done
[ "$state" = "succeeded" ] || fail "Hervatte run eindigde in '$state' (verwacht: succeeded)."
echo "hervat tot succeeded ✓"

# --------------------------------------------------------------------------- D
log "D: verse gestrande run moet de sweeper automatisch laten herstellen..."
stuck_reclaim="$(db_sql "INSERT INTO pipeline_runs (run_id, project_id, state, error, stages, project_snapshot, payload, created_at, updated_at)
    VALUES (gen_random_uuid(), '$project_id', 'pending', 'e2e-gezaaid', '[]', '{}', '{}', now(), now() - interval '1 hour')
    RETURNING run_id;")"
result=""
for _ in $(seq 1 "$POLL_API"); do
    result="$(db_sql "SELECT state FROM pipeline_runs WHERE run_id = '$stuck_reclaim';")"
    case "$result" in pending*|running*) sleep 1 ;; *) break ;; esac
done
[ "$result" = "succeeded" ] || fail "Sweeper-herstel eindigde in '$result' (verwacht: succeeded)."
echo "automatisch hersteld tot succeeded ✓"

log "Alle vier de e2e-controles geslaagd."
