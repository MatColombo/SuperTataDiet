#!/usr/bin/env python3
"""Contract tests for the V6 Phase A audit."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_v6_phase_a as audit  # noqa: E402


def find_version(dataset, predicate):
    for version in dataset.recipes["recipe_versions"]:
        codes = {line.get("ingredient_code") for line in version.get("ingredient_lines", [])}
        if predicate(version, codes):
            return version
    raise AssertionError("No matching version found")


def main() -> int:
    dataset = audit.load_dataset()
    audit.validate_contract(dataset)

    assert len(dataset.plan["days"]) == 180
    assert sum(len(day["meals"]) for day in dataset.plan["days"]) == 864

    banana_milk = find_version(dataset, lambda v, c: c == {"banana", "latte_ps"})
    c = audit.classify_recipe(banana_milk, dataset)
    assert c["dairy_occurrence"] is False, c
    assert c["egg_equivalent_units"] == 0, c

    ricotta = find_version(dataset, lambda v, c: "ricotta" in c)
    c = audit.classify_recipe(ricotta, dataset)
    assert c["dairy_occurrence"] is True, c

    egg_white = find_version(dataset, lambda v, c: "albume" in c)
    c = audit.classify_recipe(egg_white, dataset)
    assert c["egg_equivalent_units"] > 0, c

    rice_cake_only = find_version(
        dataset,
        lambda v, c: "gallette_riso" in c and not ({"riso_basmati", "riso_integrale", "riso_jasmine", "pasta", "pasta_integrale"} & c),
    )
    c = audit.classify_recipe(rice_cake_only, dataset)
    assert c["pasta_rice_primary"] is False, c

    true_pasta = find_version(dataset, lambda v, c: "pasta" in c and "riso_basmati" not in c)
    c = audit.classify_recipe(true_pasta, dataset)
    assert c["primary_carb"] == "pasta", c
    assert c["pasta_rice_primary"] is True, c

    # Current legume dishes reinforced with egg white must not be falsely counted
    # as plant-protein mains when the animal protein source dominates.
    legume_with_albumen = find_version(dataset, lambda v, c: "albume" in c and bool({"ceci", "lenticchie", "borlotti", "cannellini", "piselli"} & c))
    c = audit.classify_recipe(legume_with_albumen, dataset)
    assert c["primary_protein"] != "legumes" or c["plant_protein_main"] is False, c

    result = audit.audit(dataset)
    assert len(result["window_rows"]) == 174
    assert len(result["day_rows"]) == 180
    assert result["summary"]["hard_constraints"]["all_windows_compliant"] is False
    assert result["summary"]["hard_constraints"]["egg_equivalent"]["windows_failed"] > 0
    assert result["summary"]["hard_constraints"]["cheese_dairy"]["windows_failed"] > 0
    assert result["summary"]["hard_constraints"]["pasta_rice"]["windows_failed"] > 0
    assert result["summary"]["hard_constraints"]["plant_protein_main"]["windows_failed"] > 0

    print("V6 Phase A contract tests: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
