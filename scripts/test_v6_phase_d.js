#!/usr/bin/env node
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {performance}=require('node:perf_hooks');
const ROOT=path.resolve(__dirname,'..');
const intel=require(path.join(ROOT,'static/assets/js/v6-ingredient-intelligence-core.js'));
const constraints=require(path.join(ROOT,'static/assets/js/v6-constraint-core.js'));
const load=p=>JSON.parse(fs.readFileSync(path.join(ROOT,p),'utf8'));
const ingredients=load('v5_data/base/ingredients.base.v1.json');
const recipes=load('v5_data/base/recipes.base.v1.json');
const plan=load('v5_data/base/plan-template.base.v1.json');
const phaseA=load('spec/v6/phase-a-policy.json');
const phaseC1=load('spec/v6/phase-c1-policy.json');
const phaseC2=load('spec/v6/phase-c2-policy.json');
const phaseD=load('spec/v6/phase-d-policy.json');
const policies={phaseA,phaseC1,phaseC2,phaseD};
const catalog=intel.makeBaseCatalog(ingredients.ingredients,phaseD);
const byId=new Map(catalog.map(x=>[x.id,x]));
const byCode=new Map(catalog.map(x=>[x.code,x]));
const familyById=new Map(recipes.recipe_families.map(x=>[x.id,x]));
const profiles=new Map(recipes.recipe_versions.map(v=>[v.id,intel.classifyRecipeVersion(v,familyById.get(v.recipe_id),byId,phaseA)]));

assert.equal(catalog.length,131);
assert.equal(new Set(catalog.map(x=>x.code)).size,131);
assert.equal(catalog.filter(x=>x.classId==='other').length,0,'base ingredients must have structured semantics');
assert.equal(profiles.size,797);
const semanticCodes=new Map();for(const [cls,codes] of Object.entries(phaseD.semantics.classes)){for(const code of codes){assert.ok(!semanticCodes.has(code),`duplicate semantic code ${code}: ${semanticCodes.get(code)} / ${cls}`);semanticCodes.set(code,cls);}}

function assertEnergyEqual(result,label){assert.ok(result.targetQuantity>0,label);assert.ok(Math.abs(result.sourceNutrition.energyKcal-result.targetNutrition.energyKcal)<=phaseD.conversion.energy_tolerance_kcal+1e-6,`${label}: kcal mismatch`);}

const riso=byCode.get('riso_basmati'),pasta=byCode.get('pasta'),olio=byCode.get('olio'),pollo=byCode.get('pollo'),tacchino=byCode.get('tacchino'),merluzzo=byCode.get('merluzzo'),ricotta=byCode.get('ricotta');
const risoPasta=intel.compareEqualEnergy(riso,80,pasta,phaseD);assertEnergyEqual(risoPasta,'riso->pasta');assert.equal(risoPasta.classification,'compatible');assert.ok(risoPasta.targetQuantity>75&&risoPasta.targetQuantity<90);
const risoOlio=intel.compareEqualEnergy(riso,80,olio,phaseD);assertEnergyEqual(risoOlio,'riso->olio');assert.equal(risoOlio.classification,'energy-only');assert.equal(risoOlio.suggestable,false);
const polloTacchino=intel.compareEqualEnergy(pollo,140,tacchino,phaseD);assertEnergyEqual(polloTacchino,'pollo->tacchino');assert.equal(polloTacchino.classification,'very-compatible');assert.ok(polloTacchino.score>=90);
const polloMerluzzo=intel.compareEqualEnergy(pollo,140,merluzzo,phaseD);assertEnergyEqual(polloMerluzzo,'pollo->merluzzo');assert.equal(polloMerluzzo.classification,'compatible');
const ricottaGreedy=intel.rankAlternatives(ricotta,125,catalog,phaseD,{limit:8});assert.ok(ricottaGreedy.length>=5);assert.ok(ricottaGreedy.every(x=>x.suggestable));assert.ok(ricottaGreedy.some(x=>x.target.code==='mozzarella'));
const searchOil=intel.searchAlternatives(riso,80,catalog,'olio',phaseD,{limit:10});assert.equal(searchOil.length,1);assert.equal(searchOil[0].target.code,'olio');assert.equal(searchOil[0].classification,'energy-only');
const searchMerluzzo=intel.searchAlternatives(pollo,140,catalog,'merluzzo',phaseD,{limit:10});assert.equal(searchMerluzzo[0].target.code,'merluzzo');

const greedyRiso=intel.rankAlternatives(riso,80,catalog,phaseD,{limit:12});assert.ok(greedyRiso.some(x=>x.target.code==='pasta'));assert.ok(!greedyRiso.some(x=>x.target.code==='olio'));assert.ok(greedyRiso.every(x=>x.target.primaryRole==='carbohydrate'));
const zeroEnergy={...olio,id:'test:zero',code:'zero',name:'Acqua test',nutrition:{energyKcal:0,proteinG:0,carbohydrateG:0,fatG:0,fiberG:0}};assert.equal(intel.equivalentQuantity(riso,80,zeroEnergy),null);

const evaluation=constraints.evaluatePlan(plan.days,profiles,policies);assert.equal(evaluation.summary.hardViolations,0);assert.equal(evaluation.summary.softWarnings,0);assert.equal(evaluation.summary.windows,174);
assert.equal(Math.min(...evaluation.windows.map(x=>x.metrics.dairyMeals)),3);assert.equal(Math.max(...evaluation.windows.map(x=>x.metrics.dairyMeals)),3);assert.equal(Math.min(...evaluation.windows.map(x=>x.metrics.avocadoPortions)),2);assert.equal(Math.max(...evaluation.windows.map(x=>x.metrics.avocadoPortions)),2);

// Replacement guard: add a counted dairy recipe to a day already containing dairy.
const dairyVersion=recipes.recipe_versions.find(v=>profiles.get(v.id)?.dairyOccurrence);
let replacementCase=null;
for(let di=0;di<plan.days.length&&!replacementCase;di++){
  const day=plan.days[di],hasDairy=day.meals.some(m=>profiles.get(m.recipe_version_id)?.dairyOccurrence);if(!hasDairy)continue;
  const mi=day.meals.findIndex(m=>!profiles.get(m.recipe_version_id)?.dairyOccurrence);if(mi>=0)replacementCase={di,mi};
}
assert.ok(replacementCase);
const blocked=constraints.evaluateReplacement(plan.days,replacementCase.di,replacementCase.mi,dairyVersion.id,dairyVersion.recipe_id,profiles,policies);assert.equal(blocked.accepted,false);assert.ok(blocked.after.hard.some(x=>x.kind==='cheese_dairy_day'||x.kind==='counted_dairy_max'));

// Fixed serving is a hard V6 contract.
const scaled=JSON.parse(JSON.stringify(plan.days));scaled[0].meals[0].portionMultiplier=1.1;const scaledEval=constraints.evaluatePlan(scaled,profiles,policies);assert.ok(scaledEval.hard.some(x=>x.kind==='scaled_recipe_portion'));

// Removing one avocado occurrence must break at least one affected rolling window.
let avocadoCase=null;
for(let di=0;di<plan.days.length&&!avocadoCase;di++)for(let mi=0;mi<plan.days[di].meals.length;mi++){const m=plan.days[di].meals[mi];if((profiles.get(m.recipe_version_id)?.ingredientQuantities?.avocado||0)>0){avocadoCase={di,mi};break;}}
const nonAvo=recipes.recipe_versions.find(v=>!(profiles.get(v.id)?.ingredientQuantities?.avocado));assert.ok(avocadoCase&&nonAvo);const noAvo=constraints.evaluateReplacement(plan.days,avocadoCase.di,avocadoCase.mi,nonAvo.id,nonAvo.recipe_id,profiles,policies);assert.equal(noAvo.accepted,false);assert.ok(noAvo.after.hard.some(x=>x.kind==='avocado_min'));

const perfStart=performance.now();for(let i=0;i<2000;i++)intel.rankAlternatives(riso,80,catalog,phaseD,{limit:12});const perfMs=performance.now()-perfStart;assert.ok(perfMs<5000,`converter ranking too slow: ${perfMs.toFixed(1)}ms/2000`);

const matrix=[
 ['riso_basmati',80,'pasta'],['riso_basmati',80,'patata'],['pollo',140,'tacchino'],['pollo',140,'merluzzo'],['salmone',120,'sgombro'],['ricotta',125,'mozzarella'],['ceci',120,'cannellini'],['banana',100,'mela'],['olio',10,'avocado'],['riso_basmati',80,'olio']
].map(([s,q,t])=>{const x=intel.compareEqualEnergy(byCode.get(s),q,byCode.get(t),phaseD);return {source:s,sourceQuantity:q,target:t,targetQuantity:x.targetQuantity,targetUnit:x.targetUnit,score:x.score,classification:x.classification,suggestable:x.suggestable,sourceKcal:x.sourceNutrition?.energyKcal,targetKcal:x.targetNutrition?.energyKcal,proteinDeltaG:x.delta?.proteinG?.absolute,carbohydrateDeltaG:x.delta?.carbohydrateG?.absolute,fatDeltaG:x.delta?.fatG?.absolute,fiberDeltaG:x.delta?.fiberG?.absolute};});
const qa=path.join(ROOT,'qa/v6-phase-d');fs.mkdirSync(qa,{recursive:true});
function csvCell(v){const s=String(v??'');return /[",\n]/.test(s)?`"${s.replace(/"/g,'""')}"`:s;}
function writeCsv(name,headers,rows){fs.writeFileSync(path.join(qa,name),'\uFEFF'+[headers.join(','),...rows.map(r=>headers.map(h=>csvCell(r[h])).join(','))].join('\n')+'\n');}
fs.writeFileSync(path.join(qa,'converter-matrix.json'),JSON.stringify(matrix,null,2));
writeCsv('converter-matrix.csv',Object.keys(matrix[0]),matrix);
writeCsv('ingredient-semantics.csv',['code','name','category','classId','primaryRole','energyKcal','proteinG','carbohydrateG','fatG','fiberG','basisUnit'],catalog.map(x=>({code:x.code,name:x.name,category:x.category,classId:x.classId,primaryRole:x.primaryRole,energyKcal:x.nutrition.energyKcal,proteinG:x.nutrition.proteinG,carbohydrateG:x.nutrition.carbohydrateG,fatG:x.nutrition.fatG,fiberG:x.nutrition.fiberG,basisUnit:x.basis.unit})));
const used=new Set(plan.days.flatMap(d=>d.meals.map(m=>m.recipe_version_id)));
writeCsv('recipe-profiles-used.csv',['recipeVersionId','recipeId','primaryProtein','primaryCarb','eggEquivalentUnits','dairyOccurrence','dairyCodes','plantProteinMain','pastaRicePrimary','avocadoG','ingredientCodes'],[...profiles.values()].filter(x=>used.has(x.recipeVersionId)).map(x=>({recipeVersionId:x.recipeVersionId,recipeId:x.recipeId,primaryProtein:x.primaryProtein||'',primaryCarb:x.primaryCarb||'',eggEquivalentUnits:x.eggEquivalentUnits,dairyOccurrence:x.dairyOccurrence,dairyCodes:(x.dairyCodes||[]).join('|'),plantProteinMain:x.plantProteinMain,pastaRicePrimary:x.pastaRicePrimary,avocadoG:x.ingredientQuantities?.avocado||0,ingredientCodes:(x.ingredientCodes||[]).join('|')})));
const report={status:'ok',phase:'V6-D',policyVersion:phaseD.policy_version,counts:{ingredients:catalog.length,recipeVersions:profiles.size,days:plan.days.length,windows:evaluation.windows.length},checks:{structured_semantics:true,equal_energy_math:true,greedy_excludes_energy_only:true,free_search_includes_energy_only:true,nutrition_delta:true,baseline_constraint_parity:true,fixed_serving_guard:true,replacement_guard:true,avocado_guard:true},performance:{rank_2000_calls_ms:Number(perfMs.toFixed(1)),average_call_ms:Number((perfMs/2000).toFixed(4))},baseline:evaluation.summary};
fs.writeFileSync(path.join(qa,'phase-d-core-report.json'),JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));
