#!/usr/bin/env bash
set -euo pipefail
python3 scripts/test_v6_phase_a.py
python3 scripts/audit_v6_phase_a.py
