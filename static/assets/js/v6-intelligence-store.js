(function(global,factory){
  const api=factory(global.TataDietDB,global.TataDietIngredientIntelligence,global.TataDietV6Constraints);
  if(typeof module==='object'&&module.exports)module.exports=api;
  global.TataDietV6IntelligenceStore=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(dbApi,intel,constraints){
  'use strict';
  let cachedPolicy=null,cachedLibrary=null;
  function deps(){if(!dbApi||!intel||!constraints)throw new Error('Moduli V6 Ingredient Intelligence non inizializzati');}
  async function fetchJson(path){const root=typeof document!=='undefined'?(document.body?.dataset?.root||''):'';const response=await fetch(`${root}${path}`);if(!response.ok)throw new Error(`HTTP ${response.status}: ${path}`);return response.json();}
  async function policyBundle(force=false){deps();if(cachedPolicy&&!force)return cachedPolicy;const [phaseA,phaseC1,phaseC2,phaseD,phaseE]=await Promise.all(['phase-a-policy.json','phase-c1-policy.json','phase-c2-policy.json','phase-d-policy.json','phase-e-policy.json'].map(name=>fetchJson(`data/v6/${name}`)));cachedPolicy={phaseA,phaseC1,phaseC2,phaseD,phaseE};return cachedPolicy;}
  async function library(force=false){
    deps();if(cachedLibrary&&!force)return cachedLibrary;const [ingredients,revisions,recipes,versions,policies]=await Promise.all([dbApi.getAll('ingredients'),dbApi.getAll('ingredientRevisions'),dbApi.getAll('recipes'),dbApi.getAll('recipeVersions'),policyBundle(force)]);
    const ingredientCatalog=intel.makeCatalog(ingredients,revisions,policies.phaseD),ingredientById=new Map(ingredientCatalog.map(x=>[x.id,x])),recipeById=new Map(recipes.map(x=>[x.id,x]));const recipeProfiles=new Map();
    versions.forEach(v=>recipeProfiles.set(v.id,intel.classifyRecipeVersion(v,recipeById.get(v.recipeId||v.recipe_id),ingredientById,policies.phaseA)));
    cachedLibrary={policies,ingredientCatalog,ingredientById,recipeProfiles,recipes,versions};return cachedLibrary;
  }
  async function converterContext(ingredientId,quantity,force=false){const lib=await library(force),source=lib.ingredientById.get(ingredientId);if(!source)throw new Error('Ingrediente non disponibile');return {source,quantity:Number(quantity),catalog:lib.ingredientCatalog,policy:lib.policies.phaseD};}
  async function suggestedAlternatives(ingredientId,quantity,options={}){const ctx=await converterContext(ingredientId,quantity,options.force);return intel.rankAlternatives(ctx.source,ctx.quantity,ctx.catalog,ctx.policy,options);}
  async function searchAlternatives(ingredientId,quantity,query,options={}){const ctx=await converterContext(ingredientId,quantity,options.force);return intel.searchAlternatives(ctx.source,ctx.quantity,ctx.catalog,query,ctx.policy,options);}
  function lineIdentity(line){return {ingredientId:line?.ingredientId||line?.ingredient_id||null,quantity:Number(line?.baseQuantity??line?.base_quantity??line?.quantity),unit:line?.baseUnit||line?.base_unit||line?.unit||'g'};}
  async function suggestedForLine(line,options={}){const x=lineIdentity(line);if(!x.ingredientId||!Number.isFinite(x.quantity))throw new Error('Riga ingrediente non convertibile');return suggestedAlternatives(x.ingredientId,x.quantity,options);}
  async function searchForLine(line,query,options={}){const x=lineIdentity(line);if(!x.ingredientId||!Number.isFinite(x.quantity))throw new Error('Riga ingrediente non convertibile');return searchAlternatives(x.ingredientId,x.quantity,query,options);}
  async function evaluatePlan(days,force=false){const lib=await library(force);return constraints.evaluatePlan(days,lib.recipeProfiles,lib.policies);}
  async function evaluateReplacement(days,dayIndex,mealIndex,newVersionId,newRecipeId=null,force=false){const lib=await library(force);return constraints.evaluateReplacement(days,dayIndex,mealIndex,newVersionId,newRecipeId,lib.recipeProfiles,lib.policies);}
  function clearCache(){cachedPolicy=null;cachedLibrary=null;}
  return {policyBundle,library,converterContext,suggestedAlternatives,searchAlternatives,lineIdentity,suggestedForLine,searchForLine,evaluatePlan,evaluateReplacement,clearCache};
});
