(function(global,factory){
  const api=factory(global.TataDietDB,global.TataDietPlanCore,global.TataDietPlanStore,global.TataDietComposerStore,global.TataDietV6IntelligenceStore,global.TataDietV6Planner);
  if(typeof module==='object'&&module.exports)module.exports=api;
  global.TataDietV6PlannerStore=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(dbApi,planCore,planStore,composerStore,intelStore,planner){
  'use strict';
  let cachedIndex=null,cachedLibrary=null;
  function deps(){if(!dbApi||!planCore||!planStore||!composerStore||!intelStore||!planner)throw new Error('Moduli planner V6 non inizializzati');}
  function normalizeEnergySetting(input){const src=input||{},target=Number(src.targetKcal),pct=Number(src.tolerancePct),tol=Number(src.toleranceKcal);return {targetKcal:Number.isFinite(target)&&target>=800&&target<=2600?target:null,tolerancePct:Number.isFinite(pct)&&pct>=0&&pct<=.2?pct:null,toleranceKcal:Number.isFinite(tol)&&tol>=0?tol:null};}
  async function settings(){deps();return normalizeEnergySetting(await dbApi.getSetting('v6PlannerEnergy'));}
  async function library(force=false){deps();const lib=await intelStore.library(force);if(force||lib!==cachedLibrary||!cachedIndex){const catalog=await composerStore.library();cachedIndex=planner.createIndex(catalog,lib.recipeProfiles,{...lib.policies,phaseE:lib.policies.phaseE||{}});cachedLibrary=lib;}return {lib,index:cachedIndex};}
  async function context(date,force=false){deps();const [{lib,index},bundle,catalog,energy,preferences]=await Promise.all([library(force),planStore.activeBundle(),composerStore.library(),settings(),dbApi.getSetting('foodPreferencesV1')]);if(!bundle)throw new Error('Nessun piano personale attivo');const dayIndex=bundle.days.findIndex(d=>d.date===date);if(dayIndex<0)throw new Error('Giornata non trovata nel piano personale');return {lib,index,bundle,catalog,energy,preferences,dayIndex,day:bundle.days[dayIndex]};}
  function mergedOptions(ctx,options={}){return {...ctx.energy,...options,targetKcal:options.targetKcal??ctx.energy.targetKcal??undefined,tolerancePct:options.tolerancePct??ctx.energy.tolerancePct??undefined,toleranceKcal:options.toleranceKcal??ctx.energy.toleranceKcal??undefined,preferences:options.preferences??ctx.preferences};}
  async function previewDay(date,options={}){const ctx=await context(date,options.force);return planner.planDay(ctx.bundle.days,ctx.dayIndex,ctx.index,null,null,mergedOptions(ctx,options));}
  async function applyDay(date,options={}){const result=await previewDay(date,options);if(!result.accepted)throw new Error(`Planner V6: nessuna soluzione valida${result.reason?` (${result.reason})`:''}`);return {result,...await composerStore.persistDay('v6-plan-day',date,result.day)};}
  async function previewRange(fromDate,toDate,options={}){const ctx=await context(fromDate,options.force),endIndex=ctx.bundle.days.findIndex(d=>d.date===toDate);if(endIndex<ctx.dayIndex)throw new Error('Intervallo planner non valido');return planner.planRange(ctx.bundle.days,ctx.dayIndex,endIndex,ctx.index,null,null,mergedOptions(ctx,options));}
  async function validateDays(days,force=false){const {index}=await library(force),rolling=await intelStore.evaluatePlan(days,force),global=planner.globalVarietyViolations(days,index),reuse=planner.purchaseReuseViolations(days,index);const hard=Number(rolling?.summary?.hardViolations||0),soft=Number(rolling?.summary?.softWarnings||0);return {accepted:hard===0&&soft===0&&!global.violations.length&&!reuse.length,rolling,global,reuse};}
  async function saveEnergySettings(input){const value=normalizeEnergySetting(input);await dbApi.setSetting('v6PlannerEnergy',value,'v6-phase-e');return value;}
  function clearCache(){cachedIndex=null;cachedLibrary=null;intelStore.clearCache?.();}
  return {normalizeEnergySetting,settings,library,context,previewDay,applyDay,previewRange,validateDays,saveEnergySettings,clearCache};
});
