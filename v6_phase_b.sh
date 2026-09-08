#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

python3 scripts/apply_v6_phase_b_catalog.py
python3 scripts/test_v6_phase_b.py
python3 scripts/build_site.py
cmp -s v5_data/base/recipes.base.v1.json docs/data/v5/recipes.base.v1.json
cmp -s v5_data/base/base-dataset-manifest.json docs/data/v5/base-dataset-manifest.json
python3 scripts/test_v6_phase_a.py
python3 scripts/audit_v6_phase_a.py
python3 scripts/audit_v6_phase_b.py
python3 scripts/test_v5_phase1.py
