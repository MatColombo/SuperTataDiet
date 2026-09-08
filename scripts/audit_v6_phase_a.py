#!/usr/bin/env python3
"""TataDiet V6 Phase A: deterministic audit of the current 180-day base plan.

This script is intentionally read-only with respect to the base dataset. It applies
`spec/v6/phase-a-policy.json` to the current 180-day plan and emits review artifacts
for the one-shot curation pass planned for V6.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "spec" / "v6" / "phase-a-policy.json"
DEFAULT_PLAN = ROOT / "docs" / "data" / "v5" / "plan-template.base.v1.json"
DEFAULT_RECIPES = ROOT / "docs" / "data" / "v5" / "recipes.base.v1.json"
DEFAULT_INGREDIENTS = ROOT / "docs" / "data" / "v5" / "ingredients.base.v1.json"
DEFAULT_OUTPUT = ROOT / "qa" / "v6-phase-a"

MONTH_NUMBERS = {
    "Gennaio": 1,
    "Febbraio": 2,
    "Marzo": 3,
    "Aprile": 4,
    "Maggio": 5,
    "Giugno": 6,
    "Luglio": 7,
    "Agosto": 8,
    "Settembre": 9,
    "Ottobre": 10,
    "Novembre": 11,
    "Dicembre": 12,
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: serialize_csv_value(row.get(key)) for key in fieldnames})


def serialize_csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, bool):
        return "yes" if value else "no"
    return value


def nutrition_contribution(line: dict[str, Any], ingredient: dict[str, Any], nutrient: str) -> float:
    basis = ingredient.get("nutrition_basis") or {}
    amount = float(basis.get("amount") or 100.0)
    if amount <= 0:
        return 0.0
    base_quantity = float(line.get("base_quantity") or 0.0)
    value = float((ingredient.get("nutrients") or {}).get(nutrient) or 0.0)
    return base_quantity / amount * value


@dataclass(frozen=True)
class Dataset:
    policy: dict[str, Any]
    plan: dict[str, Any]
    recipes: dict[str, Any]
    ingredients: dict[str, Any]
    ingredients_by_code: dict[str, dict[str, Any]]
    versions_by_id: dict[str, dict[str, Any]]
    families_by_id: dict[str, dict[str, Any]]


def load_dataset(
    policy_path: Path = DEFAULT_POLICY,
    plan_path: Path = DEFAULT_PLAN,
    recipes_path: Path = DEFAULT_RECIPES,
    ingredients_path: Path = DEFAULT_INGREDIENTS,
) -> Dataset:
    policy = load_json(policy_path)
    plan = load_json(plan_path)
    recipes = load_json(recipes_path)
    ingredients = load_json(ingredients_path)
    return Dataset(
        policy=policy,
        plan=plan,
        recipes=recipes,
        ingredients=ingredients,
        ingredients_by_code={item["code"]: item for item in ingredients["ingredients"]},
        versions_by_id={item["id"]: item for item in recipes["recipe_versions"]},
        families_by_id={item["id"]: item for item in recipes["recipe_families"]},
    )


def reverse_group_map(group_mapping: dict[str, list[str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for group, codes in group_mapping.items():
        for code in codes:
            if code in result:
                raise ValueError(f"Ingredient code {code!r} belongs to more than one group: {result[code]!r}, {group!r}")
            result[code] = group
    return result


def classify_recipe(version: dict[str, Any], dataset: Dataset) -> dict[str, Any]:
    policy = dataset.policy
    classification = policy["classification"]
    hard = policy["hard_constraints"]
    protein_code_to_group = reverse_group_map(classification["protein_groups"])
    carb_code_to_group = reverse_group_map(classification["carb_groups"])

    protein_by_group: Counter[str] = Counter()
    carb_by_group: Counter[str] = Counter()
    quantity_by_code: Counter[str] = Counter()
    meal_codes: set[str] = set()

    for line in version.get("ingredient_lines", []):
        code = line.get("ingredient_code")
        if not code:
            continue
        meal_codes.add(code)
        quantity_by_code[code] += float(line.get("base_quantity") or 0.0)
        ingredient = dataset.ingredients_by_code.get(code)
        if not ingredient:
            continue
        protein_group = protein_code_to_group.get(code)
        if protein_group:
            protein_by_group[protein_group] += nutrition_contribution(line, ingredient, "protein_g")
        carb_group = carb_code_to_group.get(code)
        if carb_group:
            carb_by_group[carb_group] += nutrition_contribution(line, ingredient, "carbohydrate_g")

    primary_policy = classification["primary_source"]
    primary_protein, primary_protein_g, primary_protein_share = choose_primary_group(
        protein_by_group,
        float(primary_policy["minimum_protein_g"]),
        float(primary_policy["minimum_share_of_recognized_group_contribution"]),
    )
    primary_carb, primary_carb_g, primary_carb_share = choose_primary_group(
        carb_by_group,
        float(primary_policy["minimum_carbohydrate_g"]),
        float(primary_policy["minimum_share_of_recognized_group_contribution"]),
    )

    egg_units = 0.0
    for code, conversion in hard["egg_equivalent"]["ingredients"].items():
        grams = quantity_by_code.get(code, 0.0)
        egg_units += grams / float(conversion["grams_per_unit"])

    dairy_codes = set(hard["cheese_dairy"]["included_codes"])
    dairy_present = bool(meal_codes & dairy_codes)

    plant = hard["plant_protein_main"]
    legume_codes = set(plant["legume_codes"])
    legume_quantity = sum(quantity_by_code.get(code, 0.0) for code in legume_codes)
    legume_protein = float(protein_by_group.get("legumes", 0.0))
    total_recognized_protein = sum(protein_by_group.values())
    legume_share = legume_protein / total_recognized_protein if total_recognized_protein > 0 else 0.0
    legumes_main = (
        primary_protein == plant["qualifying_group"]
        and legume_quantity >= float(plant["min_legume_base_quantity_g"])
        and legume_protein >= float(plant["min_group_protein_g"])
        and legume_share >= float(plant["min_group_share_of_recognized_protein"])
    )

    pasta_rice = hard["pasta_rice"]
    pasta_rice_qualifies = primary_carb in set(pasta_rice["qualifying_primary_carb_families"])

    return {
        "recipe_version_id": version["id"],
        "recipe_id": version["recipe_id"],
        "ingredient_codes": sorted(meal_codes),
        "egg_equivalent_units": round(egg_units, 4),
        "dairy_occurrence": dairy_present,
        "dairy_codes": sorted(meal_codes & dairy_codes),
        "primary_protein": primary_protein,
        "primary_protein_g": round(primary_protein_g, 3),
        "primary_protein_share": round(primary_protein_share, 4),
        "protein_group_contributions_g": {k: round(v, 3) for k, v in sorted(protein_by_group.items())},
        "legume_quantity_g": round(legume_quantity, 3),
        "legume_protein_g": round(legume_protein, 3),
        "legume_share_of_recognized_protein": round(legume_share, 4),
        "plant_protein_main": legumes_main,
        "primary_carb": primary_carb,
        "primary_carb_g": round(primary_carb_g, 3),
        "primary_carb_share": round(primary_carb_share, 4),
        "carb_group_contributions_g": {k: round(v, 3) for k, v in sorted(carb_by_group.items())},
        "pasta_rice_primary": pasta_rice_qualifies,
    }


def choose_primary_group(contributions: Counter[str], minimum_value: float, minimum_share: float) -> tuple[str | None, float, float]:
    if not contributions:
        return None, 0.0, 0.0
    group, value = max(contributions.items(), key=lambda item: (item[1], item[0]))
    total = sum(contributions.values())
    share = value / total if total > 0 else 0.0
    if value < minimum_value or share < minimum_share:
        return None, float(value), float(share)
    return group, float(value), float(share)


def family_title(recipe_id: str, dataset: Dataset) -> str:
    return (dataset.families_by_id.get(recipe_id) or {}).get("title") or recipe_id


def month_number(day: dict[str, Any]) -> int:
    month = day.get("month")
    if month not in MONTH_NUMBERS:
        raise ValueError(f"Unknown Italian month name in plan: {month!r}")
    return MONTH_NUMBERS[month]


def build_occurrences(dataset: Dataset, classifications: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    for day_index, day in enumerate(dataset.plan["days"]):
        for meal_index, meal in enumerate(day.get("meals", [])):
            version_id = meal["recipe_version_id"]
            version = dataset.versions_by_id.get(version_id)
            if version is None:
                raise KeyError(f"Unresolved recipe version: {version_id}")
            classification = classifications[version_id]
            occurrences.append(
                {
                    "day_index": day_index,
                    "global_day": int(day["base_global_day"]),
                    "month": day["month"],
                    "month_number": month_number(day),
                    "day_type": day["day_type"],
                    "cycle": day["cycle"],
                    "variant": day["variant"],
                    "day_in_variant": day["day_in_variant"],
                    "meal_index": meal_index,
                    "meal_id": meal["id"],
                    "meal_type": meal["meal_type"],
                    "time": meal["time"],
                    "recipe_id": meal["recipe_id"],
                    "recipe_version_id": version_id,
                    "title": family_title(meal["recipe_id"], dataset),
                    "classification": classification,
                }
            )
    return occurrences


def seasonality_findings(dataset: Dataset, occurrences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seasonality = dataset.policy["soft_constraints"]["seasonality"]
    month_map = {code: set(months) for code, months in seasonality["fresh_ingredient_months"].items()}
    rows: list[dict[str, Any]] = []
    for occurrence in occurrences:
        month = occurrence["month_number"]
        for code in occurrence["classification"]["ingredient_codes"]:
            allowed = month_map.get(code)
            if allowed is None or month in allowed:
                continue
            ingredient = dataset.ingredients_by_code.get(code, {})
            rows.append(
                {
                    "global_day": occurrence["global_day"],
                    "month": occurrence["month"],
                    "day_type": occurrence["day_type"],
                    "meal_id": occurrence["meal_id"],
                    "meal_type": occurrence["meal_type"],
                    "time": occurrence["time"],
                    "recipe_id": occurrence["recipe_id"],
                    "recipe_title": occurrence["title"],
                    "ingredient_code": code,
                    "ingredient_name": ingredient.get("name", code),
                    "allowed_months": sorted(allowed),
                }
            )
    return rows


def recipe_repeat_findings(dataset: Dataset, occurrences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    policy = dataset.policy["soft_constraints"]["recipe_repeat"]
    lookback = int(policy["lookback_days"])
    high_gap = int(policy["high_severity_gap_days"])
    previous_by_recipe: dict[str, dict[str, Any]] = {}
    findings: list[dict[str, Any]] = []
    for occurrence in occurrences:
        previous = previous_by_recipe.get(occurrence["recipe_id"])
        if previous is not None:
            gap = occurrence["global_day"] - previous["global_day"]
            if gap <= lookback:
                findings.append(
                    {
                        "global_day": occurrence["global_day"],
                        "meal_id": occurrence["meal_id"],
                        "meal_type": occurrence["meal_type"],
                        "recipe_id": occurrence["recipe_id"],
                        "recipe_title": occurrence["title"],
                        "previous_global_day": previous["global_day"],
                        "previous_meal_id": previous["meal_id"],
                        "gap_days": gap,
                        "severity": "high" if gap <= high_gap else "warning",
                    }
                )
        previous_by_recipe[occurrence["recipe_id"]] = occurrence
    return findings


def group_occurrences_by_day(occurrences: list[dict[str, Any]], day_count: int) -> list[list[dict[str, Any]]]:
    by_day: list[list[dict[str, Any]]] = [[] for _ in range(day_count)]
    for occurrence in occurrences:
        by_day[occurrence["day_index"]].append(occurrence)
    return by_day


def window_audit(dataset: Dataset, occurrences: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    days = dataset.plan["days"]
    window_days = int(dataset.policy["window_days"])
    hard = dataset.policy["hard_constraints"]
    soft = dataset.policy["soft_constraints"]
    by_day = group_occurrences_by_day(occurrences, len(days))

    window_rows: list[dict[str, Any]] = []
    hard_violations: list[dict[str, Any]] = []
    soft_warnings: list[dict[str, Any]] = []

    excluded_concentration = set(soft["ingredient_concentration"]["excluded_codes"])
    main_meal_types = set(hard["plant_protein_main"]["eligible_meal_types"])

    for start in range(0, len(days) - window_days + 1):
        end = start + window_days
        window_occurrences = [occ for day_rows in by_day[start:end] for occ in day_rows]
        start_day = days[start]
        end_day = days[end - 1]

        egg_units = sum(occ["classification"]["egg_equivalent_units"] for occ in window_occurrences)
        dairy_meals = sum(1 for occ in window_occurrences if occ["classification"]["dairy_occurrence"])
        pasta_rice_meals = sum(1 for occ in window_occurrences if occ["classification"]["pasta_rice_primary"])
        pasta_primary_meals = sum(1 for occ in window_occurrences if occ["classification"]["primary_carb"] == "pasta")
        rice_primary_meals = sum(1 for occ in window_occurrences if occ["classification"]["primary_carb"] == "rice")
        plant_main_meals = sum(
            1
            for occ in window_occurrences
            if occ["meal_type"] in main_meal_types and occ["classification"]["plant_protein_main"]
        )

        failures: list[str] = []
        checks = [
            ("egg_equivalent", egg_units <= float(hard["egg_equivalent"]["max_per_window"]), egg_units, hard["egg_equivalent"]["max_per_window"], "max"),
            ("cheese_dairy_window", dairy_meals <= int(hard["cheese_dairy"]["max_meals_per_window"]), dairy_meals, hard["cheese_dairy"]["max_meals_per_window"], "max"),
            ("pasta_rice", pasta_rice_meals >= int(hard["pasta_rice"]["min_meals_per_window"]), pasta_rice_meals, hard["pasta_rice"]["min_meals_per_window"], "min"),
            ("plant_protein_main", plant_main_meals >= int(hard["plant_protein_main"]["min_meals_per_window"]), plant_main_meals, hard["plant_protein_main"]["min_meals_per_window"], "min"),
        ]
        for code, ok, observed, limit, direction in checks:
            if ok:
                continue
            failures.append(code)
            hard_violations.append(
                {
                    "kind": code,
                    "scope": "window",
                    "start_global_day": start_day["base_global_day"],
                    "end_global_day": end_day["base_global_day"],
                    "observed": round(float(observed), 4),
                    "limit": limit,
                    "direction": direction,
                }
            )

        pasta_rice_balance_warnings: list[dict[str, Any]] = []
        balance = soft.get("pasta_rice_balance") or {}
        if balance:
            min_pasta = int(balance.get("min_pasta_primary_meals_per_window", 0))
            min_rice = int(balance.get("min_rice_primary_meals_per_window", 0))
            if pasta_primary_meals < min_pasta:
                warning = {"source": "pasta", "observed": pasta_primary_meals, "minimum": min_pasta}
                pasta_rice_balance_warnings.append(warning)
                soft_warnings.append(
                    {
                        "kind": "pasta_rice_balance",
                        "scope": "window",
                        "start_global_day": start_day["base_global_day"],
                        "end_global_day": end_day["base_global_day"],
                        **warning,
                    }
                )
            if rice_primary_meals < min_rice:
                warning = {"source": "rice", "observed": rice_primary_meals, "minimum": min_rice}
                pasta_rice_balance_warnings.append(warning)
                soft_warnings.append(
                    {
                        "kind": "pasta_rice_balance",
                        "scope": "window",
                        "start_global_day": start_day["base_global_day"],
                        "end_global_day": end_day["base_global_day"],
                        **warning,
                    }
                )

        primary_protein_counts: Counter[str] = Counter()
        main_classified = 0
        for occ in window_occurrences:
            if occ["meal_type"] not in main_meal_types:
                continue
            group = occ["classification"]["primary_protein"]
            if group:
                primary_protein_counts[group] += 1
                main_classified += 1
        protein_concentration: list[dict[str, Any]] = []
        if main_classified:
            for group, count in primary_protein_counts.items():
                share = count / main_classified
                if (
                    count >= int(soft["primary_protein_concentration"]["minimum_occurrences_to_warn"])
                    and share > float(soft["primary_protein_concentration"]["max_share_in_main_meals_per_window"])
                ):
                    warning = {"group": group, "count": count, "share": round(share, 4)}
                    protein_concentration.append(warning)
                    soft_warnings.append(
                        {
                            "kind": "primary_protein_concentration",
                            "scope": "window",
                            "start_global_day": start_day["base_global_day"],
                            "end_global_day": end_day["base_global_day"],
                            **warning,
                        }
                    )

        ingredient_meal_counts: Counter[str] = Counter()
        ingredient_days: defaultdict[str, set[int]] = defaultdict(set)
        for occ in window_occurrences:
            for code in sorted(set(occ["classification"]["ingredient_codes"])):
                if code in excluded_concentration:
                    continue
                ingredient_meal_counts[code] += 1
                ingredient_days[code].add(occ["global_day"])
        ingredient_concentration: list[dict[str, Any]] = []
        for code, count in sorted(ingredient_meal_counts.items()):
            distinct_days = len(ingredient_days[code])
            if (
                count > int(soft["ingredient_concentration"]["max_meal_occurrences_per_window"])
                and distinct_days >= int(soft["ingredient_concentration"]["minimum_distinct_days"])
            ):
                warning = {"ingredient_code": code, "meal_count": count, "distinct_days": distinct_days}
                ingredient_concentration.append(warning)
                soft_warnings.append(
                    {
                        "kind": "ingredient_concentration",
                        "scope": "window",
                        "start_global_day": start_day["base_global_day"],
                        "end_global_day": end_day["base_global_day"],
                        **warning,
                    }
                )

        window_rows.append(
            {
                "start_global_day": start_day["base_global_day"],
                "end_global_day": end_day["base_global_day"],
                "start_month": start_day["month"],
                "end_month": end_day["month"],
                "egg_equivalent_units": round(egg_units, 2),
                "egg_limit": hard["egg_equivalent"]["max_per_window"],
                "dairy_meals": dairy_meals,
                "dairy_limit": hard["cheese_dairy"]["max_meals_per_window"],
                "pasta_rice_primary_meals": pasta_rice_meals,
                "pasta_primary_meals": pasta_primary_meals,
                "rice_primary_meals": rice_primary_meals,
                "pasta_rice_min": hard["pasta_rice"]["min_meals_per_window"],
                "plant_protein_main_meals": plant_main_meals,
                "plant_protein_min": hard["plant_protein_main"]["min_meals_per_window"],
                "hard_failures": failures,
                "hard_ok": not failures,
                "protein_concentration_warnings": protein_concentration,
                "ingredient_concentration_warnings": ingredient_concentration,
                "pasta_rice_balance_warnings": pasta_rice_balance_warnings,
            }
        )

    return window_rows, hard_violations, soft_warnings


def day_audit(
    dataset: Dataset,
    occurrences: list[dict[str, Any]],
    window_rows: list[dict[str, Any]],
    seasonality: list[dict[str, Any]],
    repeats: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    days = dataset.plan["days"]
    hard = dataset.policy["hard_constraints"]
    energy = dataset.policy["energy_diagnostics"]
    by_day = group_occurrences_by_day(occurrences, len(days))

    seasonality_by_day: Counter[int] = Counter(row["global_day"] for row in seasonality)
    repeat_by_day: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in repeats:
        repeat_by_day[row["global_day"]].append(row)

    hard_windows_touching: Counter[int] = Counter()
    hard_kinds_touching: defaultdict[int, Counter[str]] = defaultdict(Counter)
    soft_windows_touching: Counter[int] = Counter()
    for row in window_rows:
        for global_day in range(int(row["start_global_day"]), int(row["end_global_day"]) + 1):
            if row["hard_failures"]:
                hard_windows_touching[global_day] += 1
                for kind in row["hard_failures"]:
                    hard_kinds_touching[global_day][kind] += 1
            if row["protein_concentration_warnings"] or row["ingredient_concentration_warnings"]:
                soft_windows_touching[global_day] += 1

    daily_hard_violations: list[dict[str, Any]] = []
    daily_soft_warnings: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    main_meal_types = set(hard["plant_protein_main"]["eligible_meal_types"])
    for index, day in enumerate(days):
        day_occurrences = by_day[index]
        global_day = int(day["base_global_day"])
        dairy_meals = sum(1 for occ in day_occurrences if occ["classification"]["dairy_occurrence"])
        egg_units = sum(occ["classification"]["egg_equivalent_units"] for occ in day_occurrences)
        pasta_rice = sum(1 for occ in day_occurrences if occ["classification"]["pasta_rice_primary"])
        plant_main = sum(
            1
            for occ in day_occurrences
            if occ["meal_type"] in main_meal_types and occ["classification"]["plant_protein_main"]
        )
        direct_hard: list[str] = []
        if dairy_meals > int(hard["cheese_dairy"]["max_meals_per_day"]):
            direct_hard.append("cheese_dairy_day")
            daily_hard_violations.append(
                {
                    "kind": "cheese_dairy_day",
                    "scope": "day",
                    "global_day": global_day,
                    "observed": dairy_meals,
                    "limit": hard["cheese_dairy"]["max_meals_per_day"],
                    "direction": "max",
                }
            )

        direct_soft: list[str] = []
        egg_spread_limit = float((dataset.policy["soft_constraints"].get("egg_daily_spread") or {}).get("max_equivalent_units_per_day_before_warning", 0) or 0)
        if egg_spread_limit and egg_units > egg_spread_limit:
            direct_soft.append("egg_daily_spread")
            daily_soft_warnings.append(
                {
                    "kind": "egg_daily_spread",
                    "scope": "day",
                    "global_day": global_day,
                    "observed": round(egg_units, 4),
                    "warning_threshold": egg_spread_limit,
                }
            )

        ref = float(energy["reference_kcal_by_day_type"].get(day["day_type"], 0) or 0)
        actual = float((day.get("source_total") or {}).get("energy_kcal") or 0.0)
        delta = actual - ref if ref else 0.0
        delta_pct = delta / ref if ref else 0.0

        repeat_rows = repeat_by_day[global_day]
        high_repeats = sum(1 for item in repeat_rows if item["severity"] == "high")
        hard_touch = hard_windows_touching[global_day]
        kinds_touch = hard_kinds_touching[global_day]
        off_season = seasonality_by_day[global_day]

        # Review score is an ordering heuristic only. Hard-context impact dominates.
        review_score = (
            len(direct_hard) * 80
            + sum(kinds_touch.values()) * 4
            + len(kinds_touch) * 12
            + high_repeats * 8
            + (len(repeat_rows) - high_repeats) * 3
            + off_season * 3
            + len(direct_soft) * 8
            + soft_windows_touching[global_day]
        )
        rows.append(
            {
                "global_day": global_day,
                "month": day["month"],
                "cycle": day["cycle"],
                "variant": day["variant"],
                "day_in_variant": day["day_in_variant"],
                "day_type": day["day_type"],
                "meal_count": len(day_occurrences),
                "egg_equivalent_units": round(egg_units, 2),
                "dairy_meals": dairy_meals,
                "pasta_rice_primary_meals": pasta_rice,
                "plant_protein_main_meals": plant_main,
                "energy_kcal": round(actual, 1),
                "energy_reference_kcal": round(ref, 1),
                "energy_delta_kcal": round(delta, 1),
                "energy_delta_pct": round(delta_pct, 4),
                "direct_hard_failures": direct_hard,
                "direct_soft_warnings": direct_soft,
                "hard_windows_touching": hard_touch,
                "hard_kinds_touching": dict(sorted(kinds_touch.items())),
                "soft_windows_touching": soft_windows_touching[global_day],
                "recipe_repeat_warnings": len(repeat_rows),
                "high_recipe_repeat_warnings": high_repeats,
                "off_season_occurrences": off_season,
                "review_score": review_score,
            }
        )
    return rows, daily_hard_violations, daily_soft_warnings


def ingredient_frequency(dataset: Dataset, occurrences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    meal_count: Counter[str] = Counter()
    day_sets: defaultdict[str, set[int]] = defaultdict(set)
    total_quantity: Counter[str] = Counter()
    for occurrence in occurrences:
        version = dataset.versions_by_id[occurrence["recipe_version_id"]]
        seen: set[str] = set()
        for line in version.get("ingredient_lines", []):
            code = line.get("ingredient_code")
            if not code:
                continue
            total_quantity[code] += float(line.get("base_quantity") or 0.0)
            if code not in seen:
                meal_count[code] += 1
                day_sets[code].add(occurrence["global_day"])
                seen.add(code)
    rows = []
    for code, count in meal_count.most_common():
        ingredient = dataset.ingredients_by_code.get(code, {})
        rows.append(
            {
                "ingredient_code": code,
                "ingredient_name": ingredient.get("name", code),
                "category": ingredient.get("category_name", ""),
                "meal_occurrences": count,
                "distinct_days": len(day_sets[code]),
                "total_base_quantity": round(total_quantity[code], 2),
                "base_unit": ((ingredient.get("nutrition_basis") or {}).get("unit") or ""),
            }
        )
    return rows


def build_summary(
    dataset: Dataset,
    occurrences: list[dict[str, Any]],
    classifications: dict[str, dict[str, Any]],
    window_rows: list[dict[str, Any]],
    hard_violations: list[dict[str, Any]],
    daily_hard_violations: list[dict[str, Any]],
    soft_warnings: list[dict[str, Any]],
    daily_soft_warnings: list[dict[str, Any]],
    repeats: list[dict[str, Any]],
    seasonality: list[dict[str, Any]],
) -> dict[str, Any]:
    windows = len(window_rows)
    egg_values = [float(row["egg_equivalent_units"]) for row in window_rows]
    dairy_values = [int(row["dairy_meals"]) for row in window_rows]
    pasta_values = [int(row["pasta_rice_primary_meals"]) for row in window_rows]
    plant_values = [int(row["plant_protein_main_meals"]) for row in window_rows]
    failure_counts = Counter(item["kind"] for item in hard_violations + daily_hard_violations)
    soft_counts = Counter(item["kind"] for item in soft_warnings + daily_soft_warnings)
    used_version_ids = {occ["recipe_version_id"] for occ in occurrences}
    used_recipe_ids = {occ["recipe_id"] for occ in occurrences}
    used_classifications = [classifications[vid] for vid in used_version_ids]
    daily_dairy = Counter(occ["global_day"] for occ in occurrences if occ["classification"]["dairy_occurrence"])
    daily_egg = Counter()
    for occ in occurrences:
        daily_egg[occ["global_day"]] += float(occ["classification"]["egg_equivalent_units"])
    main_meal_types = set(dataset.policy["hard_constraints"]["plant_protein_main"]["eligible_meal_types"])
    occurrence_counts = {
        "egg_meals": sum(1 for occ in occurrences if occ["classification"]["egg_equivalent_units"] > 0),
        "dairy_meals": sum(1 for occ in occurrences if occ["classification"]["dairy_occurrence"]),
        "pasta_rice_primary_meals": sum(1 for occ in occurrences if occ["classification"]["pasta_rice_primary"]),
        "plant_protein_main_meals": sum(
            1
            for occ in occurrences
            if occ["meal_type"] in main_meal_types and occ["classification"]["plant_protein_main"]
        ),
    }
    return {
        "phase": "V6-A",
        "policy_version": dataset.policy["policy_version"],
        "source_dataset_version": dataset.plan.get("dataset_version"),
        "counts": {
            "days": len(dataset.plan["days"]),
            "meals": len(occurrences),
            "windows_7d": windows,
            "recipe_versions_total": len(dataset.recipes["recipe_versions"]),
            "recipe_versions_used": len(used_version_ids),
            "recipe_families_used": len(used_recipe_ids),
            "ingredients_total": len(dataset.ingredients["ingredients"]),
        },
        "hard_constraints": {
            "all_windows_compliant": all(row["hard_ok"] for row in window_rows) and not daily_hard_violations,
            "failure_counts": dict(sorted(failure_counts.items())),
            "egg_equivalent": {
                "windows_failed": failure_counts.get("egg_equivalent", 0),
                "min_per_7d": round(min(egg_values), 2),
                "median_per_7d": round(statistics.median(egg_values), 2),
                "mean_per_7d": round(statistics.mean(egg_values), 2),
                "max_per_7d": round(max(egg_values), 2),
                "max_in_single_day": round(max(daily_egg.values(), default=0.0), 2),
                "limit": dataset.policy["hard_constraints"]["egg_equivalent"]["max_per_window"],
            },
            "cheese_dairy": {
                "windows_failed": failure_counts.get("cheese_dairy_window", 0),
                "days_failed": failure_counts.get("cheese_dairy_day", 0),
                "min_meals_per_7d": min(dairy_values),
                "median_meals_per_7d": round(statistics.median(dairy_values), 2),
                "mean_meals_per_7d": round(statistics.mean(dairy_values), 2),
                "max_meals_per_7d": max(dairy_values),
                "max_meals_in_single_day": max(daily_dairy.values(), default=0),
                "window_limit": dataset.policy["hard_constraints"]["cheese_dairy"]["max_meals_per_window"],
                "day_limit": dataset.policy["hard_constraints"]["cheese_dairy"]["max_meals_per_day"],
            },
            "pasta_rice": {
                "windows_failed": failure_counts.get("pasta_rice", 0),
                "min_meals_per_7d": min(pasta_values),
                "median_meals_per_7d": round(statistics.median(pasta_values), 2),
                "mean_meals_per_7d": round(statistics.mean(pasta_values), 2),
                "max_meals_per_7d": max(pasta_values),
                "minimum": dataset.policy["hard_constraints"]["pasta_rice"]["min_meals_per_window"],
            },
            "plant_protein_main": {
                "windows_failed": failure_counts.get("plant_protein_main", 0),
                "min_meals_per_7d": min(plant_values),
                "median_meals_per_7d": round(statistics.median(plant_values), 2),
                "mean_meals_per_7d": round(statistics.mean(plant_values), 2),
                "max_meals_per_7d": max(plant_values),
                "minimum": dataset.policy["hard_constraints"]["plant_protein_main"]["min_meals_per_window"],
            },
        },
        "occurrence_counts": occurrence_counts,
        "semantic_classification": {
            "used_recipe_versions_with_egg": sum(1 for item in used_classifications if item["egg_equivalent_units"] > 0),
            "used_recipe_versions_with_dairy": sum(1 for item in used_classifications if item["dairy_occurrence"]),
            "used_recipe_versions_pasta_rice_primary": sum(1 for item in used_classifications if item["pasta_rice_primary"]),
            "used_recipe_versions_plant_protein_main": sum(1 for item in used_classifications if item["plant_protein_main"]),
        },
        "soft_constraints": {
            "recipe_repeats_within_7d": len(repeats),
            "recipe_repeats_within_2d": sum(1 for row in repeats if row["severity"] == "high"),
            "off_season_occurrences": len(seasonality),
            "warning_counts": dict(sorted(soft_counts.items())),
        },
    }


def audit(dataset: Dataset) -> dict[str, Any]:
    classifications = {
        version["id"]: classify_recipe(version, dataset)
        for version in dataset.recipes["recipe_versions"]
    }
    occurrences = build_occurrences(dataset, classifications)
    seasonality = seasonality_findings(dataset, occurrences)
    repeats = recipe_repeat_findings(dataset, occurrences)
    window_rows, hard_violations, soft_warnings = window_audit(dataset, occurrences)
    day_rows, daily_hard_violations, daily_soft_warnings = day_audit(dataset, occurrences, window_rows, seasonality, repeats)
    frequencies = ingredient_frequency(dataset, occurrences)
    summary = build_summary(
        dataset,
        occurrences,
        classifications,
        window_rows,
        hard_violations,
        daily_hard_violations,
        soft_warnings,
        daily_soft_warnings,
        repeats,
        seasonality,
    )
    return {
        "summary": summary,
        "classifications": classifications,
        "occurrences": occurrences,
        "seasonality": seasonality,
        "repeats": repeats,
        "window_rows": window_rows,
        "day_rows": day_rows,
        "hard_violations": hard_violations + daily_hard_violations,
        "soft_warnings": soft_warnings + daily_soft_warnings,
        "frequencies": frequencies,
    }


def emit(result: dict[str, Any], dataset: Dataset, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "summary.json", result["summary"])
    write_json(
        output_dir / "violations.json",
        {
            "policy_version": dataset.policy["policy_version"],
            "hard_violations": result["hard_violations"],
            "soft_window_warnings": result["soft_warnings"],
            "recipe_repeat_warnings": result["repeats"],
            "seasonality_warnings": result["seasonality"],
        },
    )

    write_csv(
        output_dir / "window-audit.csv",
        [
            "start_global_day",
            "end_global_day",
            "start_month",
            "end_month",
            "egg_equivalent_units",
            "egg_limit",
            "dairy_meals",
            "dairy_limit",
            "pasta_rice_primary_meals",
            "pasta_primary_meals",
            "rice_primary_meals",
            "pasta_rice_min",
            "plant_protein_main_meals",
            "plant_protein_min",
            "hard_ok",
            "hard_failures",
            "protein_concentration_warnings",
            "ingredient_concentration_warnings",
            "pasta_rice_balance_warnings",
        ],
        result["window_rows"],
    )
    write_csv(
        output_dir / "day-audit.csv",
        [
            "global_day",
            "month",
            "cycle",
            "variant",
            "day_in_variant",
            "day_type",
            "meal_count",
            "egg_equivalent_units",
            "dairy_meals",
            "pasta_rice_primary_meals",
            "plant_protein_main_meals",
            "energy_kcal",
            "energy_reference_kcal",
            "energy_delta_kcal",
            "energy_delta_pct",
            "direct_hard_failures",
            "direct_soft_warnings",
            "hard_windows_touching",
            "hard_kinds_touching",
            "soft_windows_touching",
            "recipe_repeat_warnings",
            "high_recipe_repeat_warnings",
            "off_season_occurrences",
            "review_score",
        ],
        result["day_rows"],
    )
    queue = sorted(result["day_rows"], key=lambda row: (-int(row["review_score"]), int(row["global_day"])))
    write_csv(
        output_dir / "review-queue.csv",
        [
            "global_day",
            "month",
            "cycle",
            "variant",
            "day_in_variant",
            "day_type",
            "review_score",
            "direct_hard_failures",
            "direct_soft_warnings",
            "hard_windows_touching",
            "hard_kinds_touching",
            "recipe_repeat_warnings",
            "high_recipe_repeat_warnings",
            "off_season_occurrences",
            "egg_equivalent_units",
            "dairy_meals",
            "pasta_rice_primary_meals",
            "plant_protein_main_meals",
            "energy_kcal",
        ],
        queue,
    )

    used_counts = Counter(occ["recipe_version_id"] for occ in result["occurrences"])
    classification_rows = []
    for version in dataset.recipes["recipe_versions"]:
        item = result["classifications"][version["id"]]
        classification_rows.append(
            {
                "recipe_version_id": version["id"],
                "recipe_id": version["recipe_id"],
                "recipe_title": family_title(version["recipe_id"], dataset),
                "used_occurrences": used_counts.get(version["id"], 0),
                "egg_equivalent_units": item["egg_equivalent_units"],
                "dairy_occurrence": item["dairy_occurrence"],
                "dairy_codes": item["dairy_codes"],
                "primary_protein": item["primary_protein"],
                "primary_protein_g": item["primary_protein_g"],
                "primary_protein_share": item["primary_protein_share"],
                "legume_quantity_g": item["legume_quantity_g"],
                "legume_protein_g": item["legume_protein_g"],
                "legume_share_of_recognized_protein": item["legume_share_of_recognized_protein"],
                "plant_protein_main": item["plant_protein_main"],
                "primary_carb": item["primary_carb"],
                "pasta_rice_primary": item["pasta_rice_primary"],
                "ingredient_codes": item["ingredient_codes"],
            }
        )
    write_csv(
        output_dir / "recipe-classification.csv",
        [
            "recipe_version_id",
            "recipe_id",
            "recipe_title",
            "used_occurrences",
            "egg_equivalent_units",
            "dairy_occurrence",
            "dairy_codes",
            "primary_protein",
            "primary_protein_g",
            "primary_protein_share",
            "legume_quantity_g",
            "legume_protein_g",
            "legume_share_of_recognized_protein",
            "plant_protein_main",
            "primary_carb",
            "pasta_rice_primary",
            "ingredient_codes",
        ],
        classification_rows,
    )
    write_csv(
        output_dir / "ingredient-frequency.csv",
        [
            "ingredient_code",
            "ingredient_name",
            "category",
            "meal_occurrences",
            "distinct_days",
            "total_base_quantity",
            "base_unit",
        ],
        result["frequencies"],
    )
    write_csv(
        output_dir / "seasonality-audit.csv",
        [
            "global_day",
            "month",
            "day_type",
            "meal_id",
            "meal_type",
            "time",
            "recipe_id",
            "recipe_title",
            "ingredient_code",
            "ingredient_name",
            "allowed_months",
        ],
        result["seasonality"],
    )


def validate_contract(dataset: Dataset) -> None:
    if len(dataset.plan.get("days", [])) != 180:
        raise ValueError(f"Phase A expects exactly 180 base days, found {len(dataset.plan.get('days', []))}")
    expected_windows = len(dataset.plan["days"]) - int(dataset.policy["window_days"]) + 1
    if expected_windows != 174:
        raise ValueError(f"Phase A expects 174 seven-day windows, found {expected_windows}")
    meal_count = sum(len(day.get("meals", [])) for day in dataset.plan["days"])
    if meal_count != 864:
        raise ValueError(f"Phase A expects 864 base meals, found {meal_count}")

    all_codes = set(dataset.ingredients_by_code)
    referenced_codes: set[str] = set()
    hard = dataset.policy["hard_constraints"]
    referenced_codes.update(hard["egg_equivalent"]["ingredients"].keys())
    referenced_codes.update(hard["cheese_dairy"]["included_codes"])
    referenced_codes.update(hard["cheese_dairy"]["excluded_codes"])
    referenced_codes.update(hard["plant_protein_main"]["legume_codes"])
    for groups in dataset.policy["classification"].values():
        if isinstance(groups, dict):
            for value in groups.values():
                if isinstance(value, list):
                    referenced_codes.update(value)
    referenced_codes.update(dataset.policy["soft_constraints"]["seasonality"]["fresh_ingredient_months"].keys())
    referenced_codes.update(dataset.policy["soft_constraints"]["seasonality"]["explicitly_year_round_or_exempt"])
    missing = sorted(referenced_codes - all_codes)
    if missing:
        raise ValueError(f"Policy references ingredient codes absent from catalog: {missing}")

    for day in dataset.plan["days"]:
        month_number(day)
        for meal in day.get("meals", []):
            if meal["recipe_version_id"] not in dataset.versions_by_id:
                raise ValueError(f"Plan meal {meal['id']} references unknown version {meal['recipe_version_id']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--recipes", type=Path, default=DEFAULT_RECIPES)
    parser.add_argument("--ingredients", type=Path, default=DEFAULT_INGREDIENTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    dataset = load_dataset(args.policy, args.plan, args.recipes, args.ingredients)
    validate_contract(dataset)
    result = audit(dataset)
    emit(result, dataset, args.output)

    summary = result["summary"]
    hard = summary["hard_constraints"]
    print("TataDiet V6 Phase A audit")
    print(f"- days: {summary['counts']['days']} | meals: {summary['counts']['meals']} | windows: {summary['counts']['windows_7d']}")
    print(f"- egg windows failed: {hard['egg_equivalent']['windows_failed']} / {summary['counts']['windows_7d']}")
    print(f"- dairy windows failed: {hard['cheese_dairy']['windows_failed']} / {summary['counts']['windows_7d']}; days failed: {hard['cheese_dairy']['days_failed']} / {summary['counts']['days']}")
    print(f"- pasta/rice windows failed: {hard['pasta_rice']['windows_failed']} / {summary['counts']['windows_7d']}")
    print(f"- plant-protein windows failed: {hard['plant_protein_main']['windows_failed']} / {summary['counts']['windows_7d']}")
    print(f"- recipe repeats <=7d: {summary['soft_constraints']['recipe_repeats_within_7d']} (<=2d: {summary['soft_constraints']['recipe_repeats_within_2d']})")
    print(f"- off-season occurrences: {summary['soft_constraints']['off_season_occurrences']}")
    print(f"- output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
