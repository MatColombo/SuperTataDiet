#!/usr/bin/env python3
"""Build the curated V6 Phase B recipe extension into the immutable base catalog.

The operation is deterministic and idempotent. It reuses only ingredients already
present in the base ingredient catalog, calculates nutrition from those ingredient
records, and creates exactly one fixed-portion version for every curated recipe.
It deliberately does not edit the 180-day plan template.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT / "spec" / "v6" / "phase-b-recipes.json"
DEFAULT_RECIPES = ROOT / "v5_data" / "base" / "recipes.base.v1.json"
DEFAULT_INGREDIENTS = ROOT / "v5_data" / "base" / "ingredients.base.v1.json"
DEFAULT_MANIFEST = ROOT / "v5_data" / "base" / "base-dataset-manifest.json"
DEFAULT_PLAN = ROOT / "v5_data" / "base" / "plan-template.base.v1.json"
V6_PREFIX = "v6-"
STAMP = "2026-09-08T07:00:00+00:00"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def nutrition_for(defn: dict[str, Any], ingredient_by_code: dict[str, dict[str, Any]]) -> dict[str, float]:
    totals = {"energy_kcal": 0.0, "protein_g": 0.0, "carbohydrate_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0}
    for line in defn["ingredients"]:
        ingredient = ingredient_by_code[line["code"]]
        basis = ingredient.get("nutrition_basis") or {"amount": 100.0}
        amount = float(basis.get("amount") or 100.0)
        factor = float(line["quantity"]) / amount
        nutrients = ingredient.get("nutrients") or {}
        for key in totals:
            totals[key] += factor * float(nutrients.get(key) or 0.0)
    return {k: round(v, 4) for k, v in totals.items()}


def ingredient_lines(defn: dict[str, Any], ingredient_by_code: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for item in defn["ingredients"]:
        ingredient = ingredient_by_code[item["code"]]
        unit = (ingredient.get("nutrition_basis") or {}).get("unit") or "g"
        quantity = float(item["quantity"])
        display_quantity: float | int = int(quantity) if quantity.is_integer() else quantity
        name = ingredient["name"]
        result.append({
            "ingredient_id": ingredient["id"],
            "ingredient_revision_id": ingredient["revision_id"],
            "ingredient_code": ingredient["code"],
            "label": name,
            "quantity": display_quantity,
            "unit": unit,
            "base_quantity": display_quantity,
            "base_unit": unit,
            "conversion_id": None,
            "preparation_note": None,
            "source_text": f"{name} {display_quantity:g} {unit}" if isinstance(display_quantity, float) else f"{name} {display_quantity} {unit}",
        })
    return result


def instructions(defn: dict[str, Any], ingredient_by_code: dict[str, dict[str, Any]]) -> list[str]:
    codes = [item["code"] for item in defn["ingredients"]]
    names = [ingredient_by_code[c]["name"] for c in codes]
    role = defn["role"]
    method = defn.get("method", "main")
    if role in {"plant_pasta", "pasta_animal"}:
        return [
            "Cuoci la pasta al dente in acqua non eccessivamente salata.",
            "Cuoci o scalda gli altri ingredienti in padella con l'olio e poca acqua, mantenendo la preparazione delicata.",
            "Unisci la pasta al condimento, amalgama per 1-2 minuti e servi.",
        ]
    if role == "plant_rice":
        return [
            "Cuoci il riso fino a consistenza morbida ma non sfatta.",
            "Scalda legumi e verdure con l'olio e poca acqua, senza soffritti pesanti.",
            "Unisci il riso, mescola e servi tiepido o caldo.",
        ]
    if role in {"plant_other", "main_other"}:
        return [
            "Cuoci separatamente la fonte di carboidrati prevista dalla ricetta.",
            "Cuoci o scalda la componente proteica e le verdure con l'olio, usando una cottura semplice.",
            "Riunisci gli ingredienti e servi nella porzione indicata.",
        ]
    if method == "breakfast":
        return [
            "Pesa gli ingredienti nella porzione indicata.",
            "Combina gli ingredienti al momento del consumo; se presente avena, può essere lasciata ammorbidire qualche minuto.",
        ]
    return [
        "Pesa gli ingredienti nella porzione indicata.",
        "Assembla lo spuntino al momento del consumo o prepara in anticipo la parte non deperibile.",
    ]


def meal_prep(defn: dict[str, Any]) -> dict[str, str]:
    if defn.get("method") in {"breakfast", "snack"}:
        return {
            "prepare_ahead": "Sì, componenti porzionabili in anticipo",
            "cold": "Sì",
            "reheat": "No",
            "fridge": "1 giorno se contiene ingredienti deperibili",
        }
    return {
        "prepare_ahead": "Sì, 1 giorno prima",
        "cold": "Possibile per i piatti adatti; preferibile tiepido",
        "reheat": "Facoltativo, 1-2 min",
        "fridge": "2 giorni",
    }


def stable_version_token(defn: dict[str, Any]) -> str:
    raw = json.dumps({"title": defn["title"], "ingredients": defn["ingredients"]}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build(spec_path: Path, recipes_path: Path, ingredients_path: Path, manifest_path: Path) -> dict[str, Any]:
    spec = load(spec_path)
    recipes = load(recipes_path)
    ingredients = load(ingredients_path)
    manifest = load(manifest_path)
    ingredient_by_code = {row["code"]: row for row in ingredients["ingredients"]}

    # Remove prior Phase B generated entries so the process is idempotent.
    recipes["recipe_families"] = [r for r in recipes["recipe_families"] if not str(r.get("slug", "")).startswith(V6_PREFIX)]
    recipes["recipe_versions"] = [v for v in recipes["recipe_versions"] if not str(v.get("recipe_id", "")).startswith("base:recipe:v6-")]

    existing_titles = {r["title"] for r in recipes["recipe_families"]}
    existing_slugs = {r["slug"] for r in recipes["recipe_families"]}
    created_families = []
    created_versions = []

    for defn in spec["recipes"]:
        missing = [x["code"] for x in defn["ingredients"] if x["code"] not in ingredient_by_code]
        if missing:
            raise ValueError(f"Ingredienti mancanti per {defn['title']}: {missing}")
        if defn["title"] in existing_titles:
            raise ValueError(f"Titolo ricetta già presente: {defn['title']}")
        slug = V6_PREFIX + slugify(defn["title"])
        if slug in existing_slugs:
            raise ValueError(f"Slug ricetta già presente: {slug}")
        recipe_id = f"base:recipe:{slug}"
        version_id = f"base:recipe-version:{slug}:{stable_version_token(defn)}"
        lines = ingredient_lines(defn, ingredient_by_code)
        nutrition = nutrition_for(defn, ingredient_by_code)
        family = {
            "id": recipe_id,
            "slug": slug,
            "title": defn["title"],
            "description": "Ricetta curata per il catalogo V6: porzione fissa, senza scaling automatico.",
            "origin": "base",
            "immutable": True,
            "status": "active",
            "meal_types": defn["meal_types"],
            "cuisines": [defn["cuisine"]],
            "version_ids": [version_id],
            "instructions_status": "available",
            "default_version_id": version_id,
        }
        version = {
            "id": version_id,
            "recipe_id": recipe_id,
            "revision": 1,
            "servings": 1.0,
            "servings_source": "explicit",
            "origin": "base",
            "immutable": True,
            "status": "active",
            "composition_status": "structured",
            "ingredient_lines": lines,
            "source_ingredient_text": "; ".join(line["source_text"] for line in lines),
            "nutrition": {
                "mode": "calculated_from_ingredients",
                "values_per_serving": nutrition,
                "source_values_per_serving": {k: round(v, 1) for k, v in nutrition.items()},
                "rounded_match_to_source": True,
                "calculation_version": "v6-phase-b-1",
            },
            "prep_minutes": int(defn["prep_minutes"]),
            "meal_prep": meal_prep(defn),
            "cuisine": defn["cuisine"],
            "spices": defn.get("spices", "Nessuna"),
            "instructions": instructions(defn, ingredient_by_code),
            "instructions_status": "available",
            "practical_notes": f"V6 Phase B · ruolo {defn['role']} · mesi consigliati {','.join(map(str, defn['season_months']))}.",
            "editable_ingredient_composition": True,
            "source_occurrence_ids": [],
            "source_occurrence_count": 0,
        }
        created_families.append(family)
        created_versions.append(version)
        existing_titles.add(defn["title"])
        existing_slugs.add(slug)

    recipes["recipe_families"].extend(created_families)
    recipes["recipe_versions"].extend(created_versions)
    recipes["recipe_families"].sort(key=lambda row: row["title"].casefold())
    recipes["recipe_versions"].sort(key=lambda row: (row["recipe_id"], int(row.get("revision", 1)), row["id"]))
    recipes["generated_at"] = STAMP
    recipes["catalog_extension"] = {
        "version": spec["policy_version"],
        "source": str(spec_path.relative_to(ROOT)),
        "fixed_portions_only": True,
        "families_added": len(created_families),
        "recipe_versions_added": len(created_versions),
    }
    dump(recipes_path, recipes)

    manifest["generated_at"] = STAMP
    manifest.setdefault("extensions", {})["v6_phase_b"] = {
        "version": spec["policy_version"],
        "source": str(spec_path.relative_to(ROOT)),
        "source_sha256": sha256(spec_path),
        "note": "Catalog-only extension. The 180-day plan template is intentionally unchanged until Phase C.",
    }
    manifest["files"]["recipes.base.v1.json"] = {
        "sha256": sha256(recipes_path),
        "recipe_families": len(recipes["recipe_families"]),
        "recipe_versions": len(recipes["recipe_versions"]),
    }
    manifest["files"]["ingredients.base.v1.json"]["sha256"] = sha256(ingredients_path)
    plan_path = DEFAULT_PLAN
    plan_payload = load(plan_path)
    manifest["files"]["plan-template.base.v1.json"] = {
        "sha256": sha256(plan_path),
        "days": len(plan_payload.get("days", [])),
        "meals": sum(len(day.get("meals", [])) for day in plan_payload.get("days", [])),
    }
    dump(manifest_path, manifest)

    return {
        "status": "ok",
        "policy_version": spec["policy_version"],
        "families_added": len(created_families),
        "versions_added": len(created_versions),
        "family_total": len(recipes["recipe_families"]),
        "version_total": len(recipes["recipe_versions"]),
        "recipes_sha256": sha256(recipes_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--recipes", type=Path, default=DEFAULT_RECIPES)
    parser.add_argument("--ingredients", type=Path, default=DEFAULT_INGREDIENTS)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    result = build(args.spec, args.recipes, args.ingredients, args.manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
