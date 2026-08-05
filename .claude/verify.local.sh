#!/usr/bin/env bash
# Docs-only repo: no lint/test/build. Just validate any JSON files parse.
set -euo pipefail
mapfile -t jsons < <(git ls-files '*.json'; git ls-files --others --exclude-standard '*.json')
if [ ${#jsons[@]} -eq 0 ]; then echo "verify: no JSON files, nothing to check"; exit 0; fi
python3 -c "import json,sys; [json.load(open(f,encoding='utf-8')) for f in sys.argv[1:]]; print('verify: JSON OK ->', *sys.argv[1:])" "${jsons[@]}"
