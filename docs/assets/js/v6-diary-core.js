(function(global,factory){
  const calendar=global.DietCalendarCore||(typeof module==='object'&&module.exports?require('./calendar-core.js'):null);
  const api=factory(calendar);
  if(typeof module==='object'&&module.exports)module.exports=api;
  global.TataDietDiaryCore=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(calendar){
  'use strict';
  const NUTRIENTS=['energyKcal','proteinG','carbohydrateG','fatG','fiberG'];
  const STATUSES=['unlogged','followed','partial','not-followed','not-applicable'];
  const STATUS_WEIGHT={followed:1,partial:.5,'not-followed':0};
  const clone=value=>value==null?value:JSON.parse(JSON.stringify(value));
  const num=(value,fallback=0)=>Number.isFinite(Number(value))?Number(value):fallback;
  const cleanText=value=>String(value??'').trim();

  function normalizeNutrition(value={}){
    return Object.fromEntries(NUTRIENTS.map(key=>[key,Math.max(0,num(value?.[key],0))]));
  }
  function normalizeStatus(value){return STATUSES.includes(value)?value:'unlogged';}
  function dayId(planInstanceId,date){return `diary:${String(planInstanceId)}:${String(date)}`;}
  function plannedEntryId(event){return `planned:${String(event?.actualDate||event?.date||'')}:${String(event?.id||event?.meal?.id||'meal')}`;}
  function manualEntryId(date,token){return `manual:${String(date)}:${String(token||Date.now())}`;}

  function plannedSnapshot(event){
    return {
      mealId:event?.id||event?.meal?.id||null,
      sourceDate:event?.sourceDate||event?.day?.date||null,
      actualDate:event?.actualDate||null,
      time:event?.time||'',
      mealType:event?.mealType||'Pasto',
      recipeId:event?.recipeId||null,
      recipeVersionId:event?.recipeVersionId||null,
      title:event?.title||'Pasto pianificato',
      nutrition:normalizeNutrition(event?.nutrition||{}),
    };
  }

  function createPlannedEntry(event,stored={}){
    const snapshot=stored.plannedSnapshot||plannedSnapshot(event);
    return {
      id:stored.id||plannedEntryId(event),
      entryType:'planned',
      sourceMealId:stored.sourceMealId||event?.id||event?.meal?.id||snapshot.mealId||null,
      status:normalizeStatus(stored.status),
      plannedSnapshot:clone(snapshot),
      actualKind:stored.actualKind||null,
      actual:stored.actual?{
        title:cleanText(stored.actual.title),
        time:cleanText(stored.actual.time||snapshot.time),
        mealType:cleanText(stored.actual.mealType||snapshot.mealType||'Pasto'),
        nutrition:normalizeNutrition(stored.actual.nutrition||{}),
      }:null,
      note:cleanText(stored.note),
      createdAt:stored.createdAt||null,
      updatedAt:stored.updatedAt||null,
      orphaned:Boolean(stored.orphaned),
    };
  }

  function createManualEntry(date,input={},token){
    return {
      id:manualEntryId(date,token),entryType:'manual',sourceMealId:null,status:'followed',plannedSnapshot:null,actualKind:'manual',
      actual:{
        title:cleanText(input.title)||'Pasto fuori ricettario',
        time:cleanText(input.time),
        mealType:cleanText(input.mealType)||'Pasto extra',
        nutrition:normalizeNutrition(input.nutrition||input),
      },
      note:cleanText(input.note),createdAt:input.createdAt||null,updatedAt:input.updatedAt||null,orphaned:false,
    };
  }

  function meaningfulPlannedEntry(entry){
    if(!entry||entry.entryType!=='planned')return false;
    return normalizeStatus(entry.status)!=='unlogged'||Boolean(entry.note)||Boolean(entry.actual);
  }
  function meaningfulManualEntry(entry){return Boolean(entry&&entry.entryType==='manual');}
  function compactEntries(entries){return (entries||[]).filter(entry=>meaningfulPlannedEntry(entry)||meaningfulManualEntry(entry)).map(clone);}

  function mergePlannedEvents(events,record){
    const stored=(record?.entries||[]).map(clone);
    if(record?.plannedSnapshotFrozen){
      return stored.sort((a,b)=>{
        const ta=a.entryType==='planned'?a.plannedSnapshot?.time:a.actual?.time;
        const tb=b.entryType==='planned'?b.plannedSnapshot?.time:b.actual?.time;
        return String(ta||'99:99').localeCompare(String(tb||'99:99'))||String(a.id).localeCompare(String(b.id));
      });
    }
    const bySource=new Map(stored.filter(x=>x.entryType==='planned'&&x.sourceMealId).map(x=>[x.sourceMealId,x]));
    const byId=new Map(stored.filter(x=>x.entryType==='planned').map(x=>[x.id,x]));
    const used=new Set();
    const planned=(events||[]).map(event=>{
      const expectedId=plannedEntryId(event);
      const found=bySource.get(event.id)||byId.get(expectedId)||{};
      if(found.id)used.add(found.id);
      return createPlannedEntry(event,{...found,orphaned:false});
    });
    stored.filter(x=>x.entryType==='planned'&&!used.has(x.id)).forEach(x=>planned.push({...x,orphaned:true,status:normalizeStatus(x.status)}));
    const manual=stored.filter(x=>x.entryType==='manual');
    return [...planned,...manual].sort((a,b)=>{
      const ta=a.entryType==='planned'?a.plannedSnapshot?.time:a.actual?.time;
      const tb=b.entryType==='planned'?b.plannedSnapshot?.time:b.actual?.time;
      return String(ta||'99:99').localeCompare(String(tb||'99:99'))||String(a.id).localeCompare(String(b.id));
    });
  }

  function plannedEntries(entries){return (entries||[]).filter(x=>x.entryType==='planned'&&!x.orphaned&&normalizeStatus(x.status)!=='not-applicable');}
  function loggedPlannedEntries(entries){return plannedEntries(entries).filter(x=>Object.prototype.hasOwnProperty.call(STATUS_WEIGHT,normalizeStatus(x.status)));}
  function dayStats(entries){
    const planned=plannedEntries(entries),logged=loggedPlannedEntries(entries),manual=(entries||[]).filter(x=>x.entryType==='manual');
    const weights=logged.map(x=>STATUS_WEIGHT[normalizeStatus(x.status)]);
    const adherence=weights.length?weights.reduce((a,b)=>a+b,0)/weights.length:null;
    const completion=planned.length?logged.length/planned.length:(manual.length?1:0);
    let signal='gray';
    if(logged.length){
      if(completion<1)signal='yellow';
      else if((adherence??0)>=.85)signal='green';
      else if((adherence??0)<.5)signal='red';
      else signal='yellow';
    } else if(manual.length) signal='yellow';
    const counts={followed:0,partial:0,'not-followed':0,unlogged:0};
    planned.forEach(x=>{const s=normalizeStatus(x.status);if(s in counts)counts[s]+=1;});
    return {
      signal,plannedCount:planned.length,loggedCount:logged.length,manualCount:manual.length,
      adherence,adherencePct:adherence==null?null:Math.round(adherence*100),completion,completionPct:Math.round(completion*100),counts,
    };
  }

  function summaryForViews(views){
    const rows=(views||[]).filter(Boolean);let planned=0,logged=0,weighted=0,loggedDays=0,completeDays=0,green=0,yellow=0,red=0,gray=0,manual=0;
    rows.forEach(view=>{const stats=view.stats||dayStats(view.entries||[]);planned+=stats.plannedCount;logged+=stats.loggedCount;manual+=stats.manualCount;
      if(stats.loggedCount){loggedDays++;weighted+=(stats.adherence||0)*stats.loggedCount;} if(stats.completion>=1&&stats.plannedCount)completeDays++;
      if(stats.signal==='green')green++;else if(stats.signal==='yellow')yellow++;else if(stats.signal==='red')red++;else gray++;
    });
    return {days:rows.length,loggedDays,completeDays,plannedMeals:planned,loggedMeals:logged,manualMeals:manual,
      adherencePct:logged?Math.round(weighted/logged*100):null,completionPct:planned?Math.round(logged/planned*100):0,signals:{green,yellow,red,gray}};
  }

  function rangeDates(endDate,count,minDate){
    if(!calendar||!calendar.isValidISO(endDate))return [];
    const out=[];for(let offset=count-1;offset>=0;offset--){const date=calendar.addDays(endDate,-offset);if(!minDate||calendar.compareDates(date,minDate)>=0)out.push(date);}return out;
  }
  function signalLabel(signal){return ({green:'Seguita',yellow:'Parziale / incompleta',red:'Fuori piano',gray:'Non compilata'})[signal]||'Non compilata';}
  function signalSymbol(signal){return ({green:'●',yellow:'●',red:'●',gray:'○'})[signal]||'○';}

  return {NUTRIENTS,STATUSES,STATUS_WEIGHT,normalizeNutrition,normalizeStatus,dayId,plannedEntryId,manualEntryId,plannedSnapshot,
    createPlannedEntry,createManualEntry,compactEntries,mergePlannedEvents,plannedEntries,loggedPlannedEntries,dayStats,summaryForViews,rangeDates,signalLabel,signalSymbol};
});
