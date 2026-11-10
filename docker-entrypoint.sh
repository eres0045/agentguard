#!/bin/sh
# AgentGuard container entrypoint (Hugging Face Spaces).
# Materializes the vault keys from Space Secrets into $AGENTGUARD_KEYS_DIR.
# The secrets are the FULL contents of the local keys/*.json files:
#   AGENTGUARD_MASTER_JSON      <- keys/master.json
#   AGENTGUARD_AGENT_JSON       <- keys/agent.json
#   AGENTGUARD_AGENT_FN_JSON    <- keys/agent-function-call.json
# Keys live only in the running container's filesystem, never in the image
# or the repo. If any secret is missing, fail fast with a clear error.
set -eu
KEYS_DIR="${AGENTGUARD_KEYS_DIR:-/app/keys}"
mkdir -p "$KEYS_DIR"
for pair in "AGENTGUARD_MASTER_JSON:master.json" "AGENTGUARD_AGENT_JSON:agent.json" "AGENTGUARD_AGENT_FN_JSON:agent-function-call.json"; do
  var="${pair%%:*}"
  file="${pair##*:}"
  val="$(printenv "$var" || true)"
  if [ -z "$val" ]; then
    echo "FATAL: Space Secret $var is not set (expected full contents of keys/$file)" >&2
    exit 1
  fi
  printf '%s' "$val" > "$KEYS_DIR/$file"
  chmod 600 "$KEYS_DIR/$file"
done
echo "AgentGuard: keys materialized in $KEYS_DIR (3 files); starting backend"
exec "$@"
