#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
python3 scripts/apply_v6_phase_c1_catalog.py
python3 scripts/apply_v6_phase_c1_plan.py
python3 scripts/audit_v6_phase_c1.py
python3 scripts/report_v6_phase_c1.py
python3 scripts/build_site.py
python3 scripts/test_v6_phase_c1.py
node scripts/test_v5_phase8_stress.js
