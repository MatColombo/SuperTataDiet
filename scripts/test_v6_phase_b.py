#!/usr/bin/env python3
"""Contract and determinism tests for TataDiet V6 Phase B."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import apply_v6_phase_b_catalog as apply_b  # noqa: E402
import audit_v6_phase_b as audit_b  # noqa: E402

RECIPES = ROOT / "v5_data" / "base" / "recipes.base.v1.json"
PLAN = ROOT / "v5_data" / "base" / "plan-template.base.v1.json"
SPEC = ROOT / "spec" / "v6" / "phase-b-recipes.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    before_recipe_hash = sha(RECIPES)
    before_plan_hash = sha(PLAN)
    first = apply_b.build(apply_b.DEFAULT_SPEC, apply_b.DEFAULT_RECIPES, apply_b.DEFAULT_INGREDIENTS, apply_b.DEFAULT_MANIFEST)
    after_first_hash = sha(RECIPES)
    second = apply_b.build(apply_b.DEFAULT_SPEC, apply_b.DEFAULT_RECIPES, apply_b.DEFAULT_INGREDIENTS, apply_b.DEFAULT_MANIFEST)
    after_second_hash = sha(RECIPES)
    assert after_first_hash == after_second_hash, "Phase B catalog generation is not deterministic"
    assert before_recipe_hash == after_second_hash, "Committed Phase B catalog differs from deterministic regeneration"
    assert before_plan_hash == sha(PLAN) == spec["phase_a_baseline"]["plan_sha256"], "Phase B modified the 180-day plan"
    assert first["families_added"] == second["families_added"] == 84

    data = json.loads(RECIPES.read_text(encoding="utf-8"))
    families = [x for x in data["recipe_families"] if str(x.get("slug", "")).startswith("v6-")]
    ids = {x["id"] for x in families}
    versions = [x for x in data["recipe_versions"] if x.get("recipe_id") in ids]
    assert len(families) == 84 and len(versions) == 84
    assert all(len(x.get("version_ids", [])) == 1 for x in families)
    assert all(float(x.get("servings") or 0) == 1.0 for x in versions)
    assert all(x.get("source_occurrence_count") == 0 and x.get("source_occurrence_ids") == [] for x in versions)

    # Validate every generated record with the existing transport schemas.
    schema_dir = ROOT / "schemas" / "v5" / "base"
    for schema_name, records in [("recipe-family.schema.json", families), ("recipe-version.schema.json", versions)]:
        schema = json.loads((schema_dir / schema_name).read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        errors = []
        for record in records:
            for err in validator.iter_errors(record):
                errors.append(f"{record.get('id')}: {err.message}")
        assert not errors, "\n".join(errors[:10])

    summary = audit_b.build()
    assert summary["status"] == "pass", summary["failures"]
    assert summary["catalog"]["before"]["families"] == 306
    assert summary["catalog"]["after"]["families"] == 390
    assert summary["catalog"]["added"]["plant_protein_main_families"] == 40
    assert summary["catalog"]["added"]["pasta_primary_families"] == 36
    assert summary["catalog"]["added"]["rice_primary_families"] == 12

    print(json.dumps({
        "status":"pass",
        "phase":"V6-B",
        "families_added":84,
        "versions_added":84,
        "deterministic":True,
        "fixed_portions":True,
        "plan_unchanged":True,
        "catalog_sha256":after_second_hash,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
