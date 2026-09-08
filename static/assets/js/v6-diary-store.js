(function(global,factory){
  const api=factory(global.TataDietDB,global.TataDietEffectiveStore,global.TataDietEffectiveCore,global.TataDietDiaryCore);
  if(typeof module==='object'&&module.exports)module.exports=api;
  global.TataDietDiaryStore=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(db,effectiveStore,effective,core){
  'use strict';
  function deps(){if(!db||!effectiveStore||!effective||!core)throw new Error('Moduli Diario V6 non inizializzati');}
  const now=()=>new Date().toISOString();
  async function context(startDate=null){deps();return effectiveStore.context(startDate);}
  async function list(planInstanceId){deps();await db.initialize();return (await db.getAll('diaryDays')).filter(x=>x.planInstanceId===planInstanceId).sort((a,b)=>String(a.date).localeCompare(String(b.date)));}
  async function getDay(planInstanceId,date){deps();await db.initialize();return db.get('diaryDays',core.dayId(planInstanceId,date));}
  async function removeDay(planInstanceId,date){deps();const id=core.dayId(planInstanceId,date);const database=await db.openDatabase();try{const tx=database.transaction(['diaryDays'],'readwrite');tx.objectStore('diaryDays').delete(id);await new Promise((resolve,reject)=>{tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);});}finally{database.close();}}
  async function saveRecord(planInstanceId,date,entries,comment='',existing=null){
    deps();const meaningful=core.compactEntries(entries),text=String(comment||'').trim();
    if(!meaningful.length&&!text){await removeDay(planInstanceId,date);return null;}
    const clean=(entries||[]).filter(entry=>entry?.entryType==='planned'||entry?.entryType==='manual').map(entry=>JSON.parse(JSON.stringify(entry)));
    const stamp=now();const record={recordType:'diaryDay',schemaVersion:1,id:core.dayId(planInstanceId,date),planInstanceId,date,plannedSnapshotFrozen:true,entries:clean,comment:text,createdAt:existing?.createdAt||stamp,updatedAt:stamp};
    await db.put('diaryDays',record);return record;
  }
  async function dayView(date,startDate=null){
    const c=await context(startDate);if(!c)return null;const record=await getDay(c.plan.id,date);const events=effective.eventsOnDate(c.days,c.maps,date);const entries=core.mergePlannedEvents(events,record);const stats=core.dayStats(entries);const day=c.days.find(x=>x.date===date)||null;return {context:c,record,events,entries,stats,day,date};
  }
  async function updatePlanned(date,entryId,patch,startDate=null){
    const view=await dayView(date,startDate);if(!view)throw new Error('Piano personale non disponibile');const entry=view.entries.find(x=>x.id===entryId&&x.entryType==='planned');if(!entry)throw new Error('Pasto pianificato non trovato');
    if(patch.status!==undefined)entry.status=core.normalizeStatus(patch.status);
    if(patch.note!==undefined)entry.note=String(patch.note||'').trim();
    if(patch.actualKind!==undefined)entry.actualKind=patch.actualKind||null;
    if(patch.actual!==undefined)entry.actual=patch.actual?{title:String(patch.actual.title||'').trim(),time:String(patch.actual.time||entry.plannedSnapshot?.time||'').trim(),mealType:String(patch.actual.mealType||entry.plannedSnapshot?.mealType||'Pasto').trim(),nutrition:core.normalizeNutrition(patch.actual.nutrition||{})}:null;
    const stamp=now();entry.createdAt=entry.createdAt||stamp;entry.updatedAt=stamp;
    if(entry.status==='followed'&&patch.actual===undefined){entry.actualKind='planned-recipe';entry.actual=null;}
    if(entry.status==='unlogged'&&!entry.note&&!entry.actual)entry.actualKind=null;
    const record=await saveRecord(view.context.plan.id,date,view.entries,view.record?.comment||'',view.record);return {...view,record,entries:core.mergePlannedEvents(view.events,record),stats:core.dayStats(core.mergePlannedEvents(view.events,record))};
  }
  async function markAllFollowed(date,startDate=null){const view=await dayView(date,startDate);if(!view)throw new Error('Piano personale non disponibile');const stamp=now();view.entries.filter(x=>x.entryType==='planned'&&!x.orphaned).forEach(entry=>{entry.status='followed';entry.actualKind='planned-recipe';entry.actual=null;entry.createdAt=entry.createdAt||stamp;entry.updatedAt=stamp;});const record=await saveRecord(view.context.plan.id,date,view.entries,view.record?.comment||'',view.record);return dayView(date,startDate);}
  async function addManual(date,input,startDate=null){const view=await dayView(date,startDate);if(!view)throw new Error('Piano personale non disponibile');const token=globalThis.crypto?.randomUUID?crypto.randomUUID():`${Date.now()}-${Math.random().toString(16).slice(2)}`;const entry=core.createManualEntry(date,input,token);entry.createdAt=entry.updatedAt=now();view.entries.push(entry);await saveRecord(view.context.plan.id,date,view.entries,view.record?.comment||'',view.record);return dayView(date,startDate);}
  async function updateManual(date,entryId,input,startDate=null){const view=await dayView(date,startDate);if(!view)throw new Error('Piano personale non disponibile');const entry=view.entries.find(x=>x.id===entryId&&x.entryType==='manual');if(!entry)throw new Error('Pasto manuale non trovato');const rebuilt=core.createManualEntry(date,{...input,createdAt:entry.createdAt,updatedAt:now()},entry.id.replace(/^manual:[^:]+:/,''));rebuilt.id=entry.id;rebuilt.createdAt=entry.createdAt||now();rebuilt.updatedAt=now();const index=view.entries.indexOf(entry);view.entries[index]=rebuilt;await saveRecord(view.context.plan.id,date,view.entries,view.record?.comment||'',view.record);return dayView(date,startDate);}
  async function deleteManual(date,entryId,startDate=null){const view=await dayView(date,startDate);if(!view)throw new Error('Piano personale non disponibile');const entries=view.entries.filter(x=>x.id!==entryId);await saveRecord(view.context.plan.id,date,entries,view.record?.comment||'',view.record);return dayView(date,startDate);}
  async function saveComment(date,comment,startDate=null){const view=await dayView(date,startDate);if(!view)throw new Error('Piano personale non disponibile');await saveRecord(view.context.plan.id,date,view.entries,comment,view.record);return dayView(date,startDate);}
  return {context,list,getDay,removeDay,saveRecord,dayView,updatePlanned,markAllFollowed,addManual,updateManual,deleteManual,saveComment};
});
