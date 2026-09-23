#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
bash build.sh
node scripts/test_v6_0_3_night_tail.js
node scripts/test_v6_0_3_backup.js
python3 scripts/test_v6_phase_c2.py >/dev/null
node scripts/test_v6_phase_d.js >/dev/null
python3 scripts/test_v6_phase_d.py >/dev/null
node scripts/test_v6_phase_e.js >/dev/null
python3 scripts/test_v6_phase_e.py >/dev/null
node scripts/test_v6_phase_f.js >/dev/null
python3 scripts/test_v6_phase_f.py >/dev/null
node scripts/test_v6_phase_g.js >/dev/null
node scripts/test_v6_phase_g_store.js >/dev/null
python3 scripts/test_v6_phase_g.py >/dev/null
node scripts/test_v6_phase_h.js >/dev/null
python3 scripts/test_v6_phase_h.py >/dev/null
node scripts/test_v5_phase8_stress.js >/dev/null
python3 scripts/test_v6_0_3.py
python3 scripts/validate_site.py
