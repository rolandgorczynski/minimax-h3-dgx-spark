#!/usr/bin/env bash
# One invocation submits one asynchronous comic job; suitable for cron.
set -Eeuo pipefail

if [[ "${1:-}" == '--help' ]]; then
  echo 'Aufruf: trigger_comic.sh ["Thema"]'
  echo 'Ohne Thema erfindet der Automat selbst eine deutsche Geschichte mit 12 Kacheln.'
  echo 'Optional: COMIC_KACHELN, COMIC_STIL, COMIC_KORREKTURRUNDEN, COMIC_AUTOMATION_URL.'
  exit 0
fi
if (( $# > 1 )); then
  echo 'Das Thema als ein Argument in Anführungszeichen übergeben.' >&2
  exit 2
fi

comic_payload=$(python3 - "${1:-}" "${COMIC_KACHELN:-12}" "${COMIC_STIL:-Großstadt-Noir (düster)}" "${COMIC_KORREKTURRUNDEN:-2}" <<'PY'
import json,sys
print(json.dumps({'thema':sys.argv[1],'kacheln':int(sys.argv[2]),'stil':sys.argv[3],
                 'max_korrekturrunden':int(sys.argv[4]),'sprache':'de'},ensure_ascii=False))
PY
)
comic_curl_args=(--fail-with-body --silent --show-error --connect-timeout 5 --max-time 20
  --request POST --header 'Content-Type: application/json')
if [[ -n "${COMIC_AUTOMATION_API_TOKEN:-}" ]]; then
  comic_curl_args+=(--header "Authorization: Bearer ${COMIC_AUTOMATION_API_TOKEN}")
fi
curl "${comic_curl_args[@]}" --data "$comic_payload" "${COMIC_AUTOMATION_URL:-http://192.168.1.224:8090}/jobs"
printf '\n'
