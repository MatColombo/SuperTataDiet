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
  function issueKey(item){if(!item)return '';return [item.kind,item.scope,item.dayIndex,item.mealIndex,item.startIndex,item.endIndex,item.ingredientCode,item.group,item.recipeId,item.source].map(v=>v??'').join('|');}
  function describeIssue(item){if(!item)return 'Il piano si discosta dalle linee guida V6.';const obs=Number(item.observed),lim=Number(item.limit);switch(item.kind){
    case 'cheese_dairy_day': return `Più di ${Number.isFinite(lim)?lim:1} porzione di latticini conteggiati nella stessa giornata.`;
    case 'egg_equivalent': return `Uova/albume oltre il riferimento settimanale (${Number.isFinite(obs)?obs.toFixed(1):'?'} eq; riferimento ${Number.isFinite(lim)?lim:'6'}).`;
    case 'counted_dairy_min': return `Meno latticini del riferimento settimanale (${Number.isFinite(obs)?obs:'?'}; riferimento ${Number.isFinite(lim)?lim:'3'}).`;
    case 'counted_dairy_max': return `Più latticini del riferimento settimanale (${Number.isFinite(obs)?obs:'?'}; riferimento ${Number.isFinite(lim)?lim:'4'}).`;
    case 'counted_dairy_variety': return `Varietà di latticini ridotta nella finestra di 7 giorni.`;
    case 'pasta_rice': return `Pasta/riso meno frequenti del riferimento settimanale (${Number.isFinite(obs)?obs:'?'} pasti; riferimento ${Number.isFinite(lim)?lim:'5'}).`;
    case 'plant_protein_main': return `Proteine vegetali principali meno frequenti del riferimento settimanale.`;
    case 'avocado_min': return `Meno di 2 porzioni di avocado nella finestra di 7 giorni.`;
    case 'avocado_max': return `Più di 2 porzioni di avocado nella finestra di 7 giorni.`;
    case 'avocado_portion': return `Una porzione di avocado si discosta dai 75 g di riferimento.`;
    case 'scaled_recipe_portion': return `La ricetta usa una porzione scalata invece della porzione fissa.`;
    case 'egg_daily_spread': return `Uova/albume concentrati nella stessa giornata.`;
    case 'pasta_rice_balance': return `Rotazione ${item.source==='pasta'?'pasta':'riso'} meno varia del riferimento.`;
    case 'primary_protein_concentration': return `La stessa fonte proteica principale è concentrata nei giorni vicini.`;
    case 'ingredient_concentration': return `L'ingrediente ${item.ingredientCode||''} ricorre spesso nei giorni vicini.`.trim();
    case 'recipe_repeat': return `La stessa ricetta ricompare dopo ${item.gapDays||'?'} giorni.`;
    case 'seasonality': return `L'ingrediente ${item.ingredientCode||''} è fuori dalla stagionalità impostata.`.trim();
    case 'recipe_global_cap': return `La stessa famiglia di ricetta è molto frequente nel semestre.`;
    case 'ingredient_global_cap': return `L'ingrediente ${item.ingredientCode||''} supera il tetto di varietà globale.`.trim();
    case 'chickpea_hummus_share': return `Ceci/hummus pesano troppo sulla rotazione complessiva dei legumi.`;
    case 'top3_fruit_share': return `La frutta è concentrata su poche tipologie.`;
    case 'top3_vegetable_share': return `Le verdure sono concentrate su poche tipologie.`;
    case 'rotation_minimum': return `L'ingrediente ${item.ingredientCode||''} è poco rappresentato nella rotazione.`.trim();
    case 'fresh_dairy_isolated': return `Il latticino fresco ${item.ingredientCode||''} rischia di restare un acquisto isolato.`.trim();
    case 'avocado_isolated': return `L'avocado rischia di restare un acquisto isolato invece di essere riutilizzato.`;
    case 'preference_never': return `La modifica include un alimento segnato come “mai” nelle preferenze.`;
    case 'preference_max_7d': return `La modifica supera la frequenza preferita per ${item.group||'un gruppo alimentare'}.`;
    default: return `Scostamento dalla linea guida V6: ${String(item.kind||'controllo').replaceAll('_',' ')}.`;
  }}
  function manualWarnings(validation,beforeValidation=null,extra={}){const all=v=>[...(v?.rolling?.hard||[]),...(v?.rolling?.soft||[]),...(v?.global?.violations||[]),...(v?.reuse||[])];const beforeKeys=new Set(all(beforeValidation).map(issueKey));const issues=all(validation).filter(x=>!beforeValidation||!beforeKeys.has(issueKey(x)));const messages=[];const seen=new Set();for(const item of issues){const m=describeIssue(item);if(m&&!seen.has(m)){seen.add(m);messages.push(m);}}if(extra.energyOk===false){const m=`Energia giornaliera ${Math.round(extra.energyKcal||0)} kcal: fuori dal riferimento ${Math.round(extra.target||0)} kcal ±5%.`;if(!seen.has(m))messages.push(m);}return messages;}
  async function saveEnergySettings(input){const value=normalizeEnergySetting(input);await dbApi.setSetting('v6PlannerEnergy',value,'v6-phase-e');return value;}
  function clearCache(){cachedIndex=null;cachedLibrary=null;intelStore.clearCache?.();}
  return {normalizeEnergySetting,settings,library,context,previewDay,applyDay,previewRange,validateDays,describeIssue,manualWarnings,saveEnergySettings,clearCache};
});
