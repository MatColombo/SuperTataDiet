#!/usr/bin/env node
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {performance}=require('node:perf_hooks');
const ROOT=path.resolve(__dirname,'..');
global.structuredClone=global.structuredClone||((v)=>JSON.parse(JSON.stringify(v)));
const cal=require(path.join(ROOT,'static/assets/js/calendar-core.js'));global.DietCalendarCore=cal;
const planCore=require(path.join(ROOT,'static/assets/js/v5-plan-core.js'));
const composer=require(path.join(ROOT,'static/assets/js/v5-composer-core.js'));
const legacyPlanning=require(path.join(ROOT,'static/assets/js/v5-planning-core.js'));
const intel=require(path.join(ROOT,'static/assets/js/v6-ingredient-intelligence-core.js'));
const constraints=require(path.join(ROOT,'static/assets/js/v6-constraint-core.js'));
const planner=require(path.join(ROOT,'static/assets/js/v6-planner-core.js'));
const load=p=>JSON.parse(fs.readFileSync(path.join(ROOT,p),'utf8'));
const ingredientsFile=load('v5_data/base/ingredients.base.v1.json');
const recipesFile=load('v5_data/base/recipes.base.v1.json');
const template=load('v5_data/base/plan-template.base.v1.json');
const phaseA=load('spec/v6/phase-a-policy.json');
const phaseC1=load('spec/v6/phase-c1-policy.json');
const phaseC2=load('spec/v6/phase-c2-policy.json');
const phaseD=load('spec/v6/phase-d-policy.json');
const phaseE=load('spec/v6/phase-e-policy.json');
const policies={phaseA,phaseC1,phaseC2,phaseD,phaseE};

function camelNutrition(n={}){return {energyKcal:Number(n.energy_kcal||0),proteinG:Number(n.protein_g||0),carbohydrateG:Number(n.carbohydrate_g||0),fatG:Number(n.fat_g||0),fiberG:Number(n.fiber_g||0)};}
function yes(v){return /^(s[iì]|yes|true)/i.test(String(v||''));}
const runtimeIngredients=ingredientsFile.ingredients.map(i=>({id:i.id,name:i.name,aliases:i.aliases||[],category:i.category_id||i.category_name||'altro',origin:'base',currentRevisionId:i.revision_id,archivedAt:null}));
const runtimeRecipes=recipesFile.recipe_families.map(f=>({id:f.id,title:f.title,mealTypes:f.meal_types||[],cuisines:f.cuisines||[],origin:'base',currentVersionId:f.default_version_id,archivedAt:null}));
const familyById=new Map(recipesFile.recipe_families.map(f=>[f.id,f]));
const runtimeVersions=recipesFile.recipe_versions.map(v=>{const f=familyById.get(v.recipe_id),mp=v.meal_prep||{};return {id:v.id,recipeId:v.recipe_id,versionNumber:v.revision||1,servings:v.servings||1,nutritionMode:'calculated',ingredientLines:(v.ingredient_lines||[]).map((x,i)=>({id:`${v.id}:line:${i+1}`,ingredientId:x.ingredient_id,ingredientRevisionId:x.ingredient_revision_id,quantity:x.quantity,unit:x.unit,baseQuantity:x.base_quantity,baseUnit:x.base_unit,conversionId:x.conversion_id,preparationNote:x.preparation_note})),calculatedNutrition:camelNutrition(v.nutrition?.values_per_serving),manualNutrition:camelNutrition(v.nutrition?.source_values_per_serving),metadata:{mealTypes:f?.meal_types||[],cuisine:v.cuisine||f?.cuisines?.[0]||'Italiana',tags:[],prepMinutes:v.prep_minutes||0,instructions:v.instructions||[],mealPrep:{prepareAhead:yes(mp.prepare_ahead),coldSuitable:yes(mp.cold),reheatable:yes(mp.reheat),fridgeHours:null},spiceLevel:v.spices==='Nessuna'?'none':'very-low'},origin:'base',immutable:true};});
const catalog=composer.makeCatalog(runtimeRecipes,runtimeVersions,runtimeIngredients);
const ingredientCatalog=intel.makeBaseCatalog(ingredientsFile.ingredients,phaseD),ingredientById=new Map(ingredientCatalog.map(x=>[x.id,x]));
const profiles=new Map(recipesFile.recipe_versions.map(v=>[v.id,intel.classifyRecipeVersion(v,familyById.get(v.recipe_id),ingredientById,phaseA)]));
const initial=planCore.buildPlan(template,'2026-09-01',template.dataset_version,'2026-09-08T16:00:00.000Z');
const indexStart=performance.now();
const index=planner.createIndex(catalog,profiles,policies);
const indexMs=performance.now()-indexStart;

assert.equal(index.catalog.length,556,'planner must use current recipe families only');
assert.equal(profiles.size,797);
assert.equal(planner.globalVarietyViolations(initial.days,index).violations.length,0,'C2 baseline must satisfy C1 global variety');
assert.equal(planner.purchaseReuseViolations(initial.days,index).length,0,'C2 baseline must satisfy purchase reuse');
const baseEval=constraints.evaluatePlan(initial.days,profiles,policies);
assert.equal(baseEval.summary.hardViolations,0);
assert.equal(baseEval.summary.softWarnings,0);

// Phase E automatic generation never scales a recipe, including legacy fallback generators.
assert.equal(legacyPlanning.portionForEnergy({energyKcal:800},{nutrition:{energyKcal:400}}),1);

const matrixSpec=[
  {target:800,dayIndex:2},{target:1000,dayIndex:0},{target:1200,dayIndex:2},{target:1400,dayIndex:0},{target:1600,dayIndex:0},
  {target:1800,dayIndex:3},{target:2000,dayIndex:0},{target:2200,dayIndex:3},{target:2400,dayIndex:3},{target:2600,dayIndex:3}
];
const matrix=[];const perf=[];
for(const row of matrixSpec){
  const r=planner.planDay(initial.days,row.dayIndex,index,null,null,{targetKcal:row.target,tolerancePct:.05});
  assert.equal(r.accepted,true,`${row.target} kcal should be covered by day ${row.dayIndex+1}`);
  assert.equal(r.status,'ok');
  assert.ok(r.evaluation.energyKcal>=r.target.lowerKcal-1e-6&&r.evaluation.energyKcal<=r.target.upperKcal+1e-6,`${row.target}: energy outside tolerance`);
  assert.equal(r.evaluation.hard.length,0,`${row.target}: hard violations`);
  assert.equal(r.evaluation.soft.length,0,`${row.target}: soft warnings`);
  assert.ok(r.day.meals.every(m=>Number(m.portionMultiplier)===1),`${row.target}: scaled serving emitted`);
  assert.ok((r.items||[]).every(x=>Number(x.portionMultiplier)===1),`${row.target}: scaled item emitted`);
  perf.push(r.performanceMs);
  matrix.push({targetKcal:row.target,dayIndex:row.dayIndex+1,dayType:initial.days[row.dayIndex].dayType,resultKcal:Number(r.evaluation.energyKcal.toFixed(2)),lowerKcal:Number(r.target.lowerKcal.toFixed(2)),upperKcal:Number(r.target.upperKcal.toFixed(2)),deltaPct:Number(((r.evaluation.energyKcal-row.target)/row.target*100).toFixed(2)),skippedOptionalSlots:r.diagnostics.skippedSlots,performanceMs:r.performanceMs,status:r.status});
}
assert.ok(matrix.find(x=>x.targetKcal===1000).skippedOptionalSlots>=1,'low target should be able to omit an optional snack');

// A day/target combination that cannot fit must be explicit, not silently out of target.
const infeasible=planner.planDay(initial.days,0,index,null,null,{targetKcal:800,tolerancePct:.05});
assert.equal(infeasible.accepted,false);
assert.equal(infeasible.status,'infeasible');
assert.ok(infeasible.evaluation?.hard?.some(x=>x.kind==='energy_target'),'infeasible result must expose energy_target');

// Locked meals remain unchanged; scaled locked meals are rejected rather than normalized silently.
const lockedDays=structuredClone(initial.days);lockedDays[0].meals[0].locked=true;const lockedVersion=lockedDays[0].meals[0].recipeVersionId;
const lockedTarget=planner.dayEnergy(lockedDays[0],index.byVersion);
const lockedResult=planner.planDay(lockedDays,0,index,null,null,{targetKcal:lockedTarget,tolerancePct:.05});
assert.equal(lockedResult.accepted,true);assert.equal(lockedResult.day.meals.find(m=>m.id===lockedDays[0].meals[0].id).recipeVersionId,lockedVersion);
const badLocked=structuredClone(initial.days);badLocked[0].meals[0].locked=true;badLocked[0].meals[0].portionMultiplier=1.25;
const badLockedResult=planner.planDay(badLocked,0,index,null,null,{targetKcal:1600,tolerancePct:.05});
assert.equal(badLockedResult.accepted,false);assert.equal(badLockedResult.reason,'locked_scaled_portion');

// Deterministic tie-breaking.
const detA=planner.planDay(initial.days,0,index,null,null,{targetKcal:1400,tolerancePct:.05});
const detB=planner.planDay(initial.days,0,index,null,null,{targetKcal:1400,tolerancePct:.05});
assert.deepEqual(detA.day.meals.map(m=>m.recipeVersionId),detB.day.meals.map(m=>m.recipeVersionId));

// Sequential range planning must preserve the complete rolling contract.
const range=planner.planRange(initial.days,0,2,index,null,null,{targets:[1400,1600,1200],tolerancePct:.05});
assert.equal(range.accepted,true);assert.equal(range.status,'ok');assert.equal(range.evaluation.summary.hardViolations,0);assert.equal(range.evaluation.summary.softWarnings,0);
assert.ok(range.previewDays.slice(0,3).every(d=>d.meals.every(m=>Number(m.portionMultiplier)===1)));

assert.throws(()=>planner.planDay(initial.days,0,index,null,null,{targetKcal:799}),/fuori range/);
assert.throws(()=>planner.planDay(initial.days,0,index,null,null,{targetKcal:2601}),/fuori range/);

const sorted=perf.slice().sort((a,b)=>a-b),median=sorted[Math.floor(sorted.length/2)],p95=sorted[Math.min(sorted.length-1,Math.ceil(sorted.length*.95)-1)],max=Math.max(...perf);
assert.ok(indexMs<250,`index too slow: ${indexMs.toFixed(1)} ms`);
assert.ok(median<2500,`planner median too slow: ${median} ms`);
assert.ok(max<5000,`planner max too slow: ${max} ms`);

const qa=path.join(ROOT,'qa/v6-phase-e');fs.mkdirSync(qa,{recursive:true});
function cell(v){const s=String(v??'');return /[",\n]/.test(s)?`"${s.replace(/"/g,'""')}"`:s;}
function writeCsv(name,rows){const headers=Object.keys(rows[0]||{});fs.writeFileSync(path.join(qa,name),'\uFEFF'+[headers.join(','),...rows.map(r=>headers.map(h=>cell(r[h])).join(','))].join('\n')+'\n');}
writeCsv('energy-target-matrix.csv',matrix);
const report={status:'ok',phase:'V6-E',policyVersion:phaseE.policy_version,counts:{days:initial.days.length,meals:initial.days.reduce((a,d)=>a+d.meals.length,0),currentRecipeFamilies:index.catalog.length,recipeVersions:profiles.size},checks:{baseline_c2_clean:true,fixed_serving_automatic:true,target_range_800_2600_covered:true,explicit_infeasible:true,optional_snack_skip:true,locked_meal_preserved:true,scaled_locked_rejected:true,deterministic:true,range_planning_clean:true,no_silent_constraint_override:true},performance:{indexMs:Number(indexMs.toFixed(2)),matrixMedianMs:median,matrixP95Ms:p95,matrixMaxMs:max},infeasibleExample:{dayIndex:1,dayType:initial.days[0].dayType,targetKcal:800,bestKcal:Number((infeasible.evaluation?.energyKcal||0).toFixed(2)),hardKinds:(infeasible.evaluation?.hard||[]).map(x=>x.kind)},range:{targets:[1400,1600,1200],resultKcal:range.results.map(x=>Number(x.evaluation.energyKcal.toFixed(2))),hardViolations:range.evaluation.summary.hardViolations,softWarnings:range.evaluation.summary.softWarnings}};
fs.writeFileSync(path.join(qa,'phase-e-core-report.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
