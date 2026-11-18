#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$REPO_ROOT"

GIT_ROOT="$(git rev-parse --show-toplevel)"
if [[ "$GIT_ROOT" != "$REPO_ROOT" ]]; then
  printf 'Refusing tests: resolved repository root does not match Git root.\n' >&2
  exit 2
fi

PYTHON="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  printf 'Refusing tests: expected project interpreter is missing: %s\n' "$PYTHON" >&2
  exit 2
fi

# Do not load project/Hermes .env files during tests. API tests additionally
# require TEST_DATABASE_URL + TEST_DATABASE_NAME and verify the server target.
export PYTHON_DOTENV_DISABLED="${PYTHON_DOTENV_DISABLED:-1}"
exec "$PYTHON" -m pytest --rootdir="$REPO_ROOT" --confcutdir="$REPO_ROOT" "$@"
