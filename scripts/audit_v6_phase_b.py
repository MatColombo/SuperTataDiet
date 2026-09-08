#!/usr/bin/env python3
"""Audit the V6 Phase B curated recipe extension and its coverage gains."""
from __future__ import annotations

import csv
import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_v6_phase_a as phase_a  # noqa: E402

SPEC = ROOT / "spec" / "v6" / "phase-b-recipes.json"
RECIPES = ROOT / "v5_data" / "base" / "recipes.base.v1.json"
INGREDIENTS = ROOT / "v5_data" / "base" / "ingredients.base.v1.json"
PLAN = ROOT / "v5_data" / "base" / "plan-template.base.v1.json"
MANIFEST = ROOT / "v5_data" / "base" / "base-dataset-manifest.json"
OUT = ROOT / "qa" / "v6-phase-b"
MONTHS = [9, 10, 11, 12, 1, 2]
MONTH_LABEL = {9:"Settembre",10:"Ottobre",11:"Novembre",12:"Dicembre",1:"Gennaio",2:"Febbraio"}
MAIN_ROLES = {"plant_pasta", "plant_rice", "plant_other", "pasta_animal", "main_other"}
PLANT_ROLES = {"plant_pasta", "plant_rice", "plant_other"}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def role_map(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["title"]: row for row in spec["recipes"]}


def signature(version: dict[str, Any]) -> tuple[tuple[str, float, str], ...]:
    return tuple(sorted((str(x.get("ingredient_code")), float(x.get("base_quantity") or 0), str(x.get("base_unit") or "")) for x in version.get("ingredient_lines", [])))


def safe_months_for_recipe(spec_row: dict[str, Any], policy: dict[str, Any]) -> set[int]:
    mapping = policy["soft_constraints"]["seasonality"]["fresh_ingredient_months"]
    phase_months = set(MONTHS)
    constrained = []
    for item in spec_row["ingredients"]:
        months = mapping.get(item["code"])
        if months:
            constrained.append(set(months) & phase_months)
    if not constrained:
        return phase_months
    return set.intersection(*constrained)


def build() -> dict[str, Any]:
    spec = load(SPEC)
    manifest = load(MANIFEST)
    dataset = phase_a.load_dataset(
        plan_path=PLAN,
        recipes_path=RECIPES,
        ingredients_path=INGREDIENTS,
    )
    spec_by_title = role_map(spec)
    all_families = dataset.recipes["recipe_families"]
    all_versions = dataset.recipes["recipe_versions"]
    new_families = [x for x in all_families if str(x.get("slug", "")).startswith("v6-")]
    new_family_ids = {x["id"] for x in new_families}
    new_versions = [x for x in all_versions if x.get("recipe_id") in new_family_ids]
    old_versions = [x for x in all_versions if x.get("recipe_id") not in new_family_ids]
    family_by_id = {x["id"]: x for x in all_families}

    new_rows = []
    classifications_new = []
    for v in new_versions:
        f = family_by_id[v["recipe_id"]]
        c = phase_a.classify_recipe(v, dataset)
        s = spec_by_title.get(f["title"])
        if not s:
            raise ValueError(f"Ricetta V6 non presente nella spec: {f['title']}")
        kcal = float(v["nutrition"]["values_per_serving"]["energy_kcal"])
        protein = float(v["nutrition"]["values_per_serving"]["protein_g"])
        fiber = float(v["nutrition"]["values_per_serving"]["fiber_g"])
        declared = set(s["season_months"])
        actual_safe = safe_months_for_recipe(s, dataset.policy)
        classifications_new.append(c)
        new_rows.append({
            "role": s["role"],
            "title": f["title"],
            "recipe_id": f["id"],
            "version_id": v["id"],
            "meal_types": " | ".join(f.get("meal_types", [])),
            "primary_protein": c["primary_protein"] or "",
            "primary_carb": c["primary_carb"] or "",
            "plant_protein_main": c["plant_protein_main"],
            "egg_equivalent": c["egg_equivalent_units"],
            "cheese_dairy": c["dairy_occurrence"],
            "energy_kcal": round(kcal, 1),
            "protein_g": round(protein, 1),
            "fiber_g": round(fiber, 1),
            "declared_season_months": ",".join(map(str, sorted(declared))),
            "derived_safe_months": ",".join(map(str, sorted(actual_safe))),
            "season_declaration_valid": declared <= actual_safe,
            "ingredient_codes": " | ".join(c["ingredient_codes"]),
        })

    def stats(versions: list[dict[str, Any]]) -> dict[str, Any]:
        cls = [phase_a.classify_recipe(v, dataset) for v in versions]
        ids = {v["recipe_id"] for v in versions}
        return {
            "families": len(ids),
            "versions": len(versions),
            "plant_protein_main_families": len({v["recipe_id"] for v,c in zip(versions, cls) if c["plant_protein_main"]}),
            "plant_protein_main_versions": sum(c["plant_protein_main"] for c in cls),
            "pasta_primary_families": len({v["recipe_id"] for v,c in zip(versions, cls) if c["primary_carb"] == "pasta"}),
            "pasta_primary_versions": sum(c["primary_carb"] == "pasta" for c in cls),
            "rice_primary_families": len({v["recipe_id"] for v,c in zip(versions, cls) if c["primary_carb"] == "rice"}),
            "rice_primary_versions": sum(c["primary_carb"] == "rice" for c in cls),
            "egg_free_versions": sum(c["egg_equivalent_units"] == 0 for c in cls),
            "cheese_free_versions": sum(not c["dairy_occurrence"] for c in cls),
            "egg_and_cheese_free_versions": sum(c["egg_equivalent_units"] == 0 and not c["dairy_occurrence"] for c in cls),
        }

    before = stats(old_versions)
    after = stats(all_versions)
    added = stats(new_versions)

    coverage_rows = []
    for month in MONTHS:
        eligible = [r for r in spec["recipes"] if month in set(r["season_months"])]
        main = [r for r in eligible if r["role"] in MAIN_ROLES]
        plant = [r for r in eligible if r["role"] in PLANT_ROLES]
        pasta = [r for r in eligible if r["role"] in {"plant_pasta", "pasta_animal"}]
        rice = [r for r in eligible if r["role"] == "plant_rice"]
        coverage_rows.append({
            "month": month,
            "month_label": MONTH_LABEL[month],
            "new_main_candidates": len(main),
            "new_plant_main_candidates": len(plant),
            "new_pasta_candidates": len(pasta),
            "new_rice_candidates": len(rice),
            "new_breakfast_snack_candidates": len([r for r in eligible if r["role"] == "breakfast_snack"]),
        })

    role_distribution = Counter(spec_by_title[row["title"]]["role"] for row in new_families)
    role_nutrition = []
    for role in sorted(role_distribution):
        values = [r for r in new_rows if r["role"] == role]
        kcal = [float(r["energy_kcal"]) for r in values]
        fiber = [float(r["fiber_g"]) for r in values]
        protein = [float(r["protein_g"]) for r in values]
        role_nutrition.append({
            "role": role,
            "recipes": len(values),
            "kcal_min": round(min(kcal),1),
            "kcal_median": round(statistics.median(kcal),1),
            "kcal_max": round(max(kcal),1),
            "protein_median_g": round(statistics.median(protein),1),
            "fiber_max_g": round(max(fiber),1),
        })

    signatures = defaultdict(list)
    for v in new_versions:
        signatures[signature(v)].append(v["id"])
    duplicate_signatures = [ids for ids in signatures.values() if len(ids) > 1]
    all_titles = [f["title"] for f in all_families]
    duplicate_titles = sorted([title for title,count in Counter(all_titles).items() if count > 1])

    targets = spec["targets"]
    main_rows = [r for r in new_rows if r["role"] in MAIN_ROLES]
    bs_rows = [r for r in new_rows if r["role"] == "breakfast_snack"]
    failures = []
    checks = {
        "new_recipe_families": len(new_families) == int(targets["new_recipe_families"]),
        "one_fixed_version_per_new_family": len(new_versions) == len(new_families) and all(float(v.get("servings") or 0) == 1.0 and v.get("servings_source") == "explicit" for v in new_versions),
        "new_plant_protein_main": sum(r["plant_protein_main"] for r in new_rows) >= int(targets["new_plant_protein_main"]),
        "new_pasta_primary": sum(r["primary_carb"] == "pasta" for r in new_rows) >= int(targets["new_pasta_primary"]),
        "new_rice_primary": sum(r["primary_carb"] == "rice" for r in new_rows) >= int(targets["new_rice_primary"]),
        "new_safe_main_pool": len(main_rows) >= int(targets["new_safe_main_pool"]),
        "new_main_all_egg_free": all(float(r["egg_equivalent"]) == 0 for r in main_rows),
        "new_main_all_cheese_free": all(not r["cheese_dairy"] for r in main_rows),
        "breakfast_snack_target": len(bs_rows) >= int(targets["new_cheese_free_egg_free_breakfast_snack"]),
        "breakfast_snack_all_egg_cheese_free": all(float(r["egg_equivalent"]) == 0 and not r["cheese_dairy"] for r in bs_rows),
        "main_energy_range": all(float(targets["main_energy_kcal_range"][0]) <= float(r["energy_kcal"]) <= float(targets["main_energy_kcal_range"][1]) for r in main_rows),
        "breakfast_snack_energy_range": all(float(targets["breakfast_snack_energy_kcal_range"][0]) <= float(r["energy_kcal"]) <= float(targets["breakfast_snack_energy_kcal_range"][1]) for r in bs_rows),
        "moderate_fiber_new_mains": all(float(r["fiber_g"]) <= 12.0 for r in main_rows),
        "declared_seasonality_valid": all(bool(r["season_declaration_valid"]) for r in new_rows),
        "monthly_main_coverage": all(int(r["new_main_candidates"]) >= int(targets["minimum_new_main_candidates_per_month"]) for r in coverage_rows),
        "monthly_plant_coverage": all(int(r["new_plant_main_candidates"]) >= int(targets["minimum_new_plant_main_candidates_per_month"]) for r in coverage_rows),
        "no_duplicate_new_compositions": not duplicate_signatures,
        "no_duplicate_titles": not duplicate_titles,
        "source_occurrences_empty": all(v.get("source_occurrence_ids") == [] and int(v.get("source_occurrence_count") or 0) == 0 for v in new_versions),
        "plan_template_unchanged_from_phase_a": sha256(PLAN) == spec["phase_a_baseline"]["plan_sha256"],
        "manifest_plan_checksum_current": sha256(PLAN) == manifest["files"]["plan-template.base.v1.json"]["sha256"],
    }
    for name, ok in checks.items():
        if not ok:
            failures.append(name)

    gap_rows = [
        {"metric":"recipe families", "before":before["families"], "added":added["families"], "after":after["families"]},
        {"metric":"recipe versions", "before":before["versions"], "added":added["versions"], "after":after["versions"]},
        {"metric":"plant-protein-main families", "before":before["plant_protein_main_families"], "added":added["plant_protein_main_families"], "after":after["plant_protein_main_families"]},
        {"metric":"pasta-primary families", "before":before["pasta_primary_families"], "added":added["pasta_primary_families"], "after":after["pasta_primary_families"]},
        {"metric":"rice-primary families", "before":before["rice_primary_families"], "added":added["rice_primary_families"], "after":after["rice_primary_families"]},
        {"metric":"egg+cheese-free versions", "before":before["egg_and_cheese_free_versions"], "added":added["egg_and_cheese_free_versions"], "after":after["egg_and_cheese_free_versions"]},
    ]

    summary = {
        "phase":"V6-B",
        "status":"pass" if not failures else "fail",
        "policy_version":spec["policy_version"],
        "plan_days_modified":0,
        "catalog": {"before":before, "added":added, "after":after},
        "new_roles":dict(sorted(role_distribution.items())),
        "new_main": {
            "count":len(main_rows),
            "energy_kcal_min":min(float(r["energy_kcal"]) for r in main_rows),
            "energy_kcal_median":round(statistics.median(float(r["energy_kcal"]) for r in main_rows),1),
            "energy_kcal_max":max(float(r["energy_kcal"]) for r in main_rows),
            "fiber_g_max":max(float(r["fiber_g"]) for r in main_rows),
        },
        "checks":checks,
        "failures":failures,
        "duplicate_titles":duplicate_titles,
        "duplicate_signature_groups":duplicate_signatures,
        "monthly_coverage":coverage_rows,
    }

    write_json(OUT / "summary.json", summary)
    write_csv(OUT / "catalog-gap-matrix.csv", gap_rows, ["metric","before","added","after"])
    write_csv(OUT / "new-recipes.csv", sorted(new_rows, key=lambda r:(r["role"],r["title"])), [
        "role","title","recipe_id","version_id","meal_types","primary_protein","primary_carb","plant_protein_main","egg_equivalent","cheese_dairy","energy_kcal","protein_g","fiber_g","declared_season_months","derived_safe_months","season_declaration_valid","ingredient_codes"
    ])
    write_csv(OUT / "seasonal-coverage.csv", coverage_rows, ["month","month_label","new_main_candidates","new_plant_main_candidates","new_pasta_candidates","new_rice_candidates","new_breakfast_snack_candidates"])
    write_csv(OUT / "nutrition-by-role.csv", role_nutrition, ["role","recipes","kcal_min","kcal_median","kcal_max","protein_median_g","fiber_max_g"])
    return summary


def main() -> int:
    summary = build()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
