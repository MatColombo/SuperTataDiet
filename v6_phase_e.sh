#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
python3 scripts/build_site.py
python3 scripts/test_v6_phase_c2.py
node scripts/test_v6_phase_d.js
python3 scripts/test_v6_phase_d.py
node scripts/test_v6_phase_e.js
node scripts/test_v6_phase_e_stress.js
python3 scripts/test_v6_phase_e.py
