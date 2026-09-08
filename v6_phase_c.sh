#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
python3 scripts/apply_v6_phase_c_catalog.py
python3 scripts/apply_v6_phase_c_plan.py
python3 scripts/audit_v6_phase_a.py --plan v5_data/base/plan-template.base.v1.json --recipes v5_data/base/recipes.base.v1.json --ingredients v5_data/base/ingredients.base.v1.json --output qa/v6-phase-c
python3 scripts/report_v6_phase_c.py
python3 scripts/build_site.py
python3 scripts/test_v6_phase_c.py
node scripts/test_v5_phase8_stress.js
