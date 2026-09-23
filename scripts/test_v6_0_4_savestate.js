#!/usr/bin/env node
"use strict";
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
if(!global.crypto) global.crypto=require('node:crypto').webcrypto;
global.structuredClone=global.structuredClone||((v)=>JSON.parse(JSON.stringify(v)));

const STORE_NAMES=['meta','settings','ingredients','ingredientRevisions','recipes','recipeVersions','planInstances','calendarDays','operations','shoppingChecklists','diaryDays'];
function makeMemoryDb(){
  const stores=Object.fromEntries(STORE_NAMES.map(n=>[n,new Map()]));
  const clone=v=>v===undefined?undefined:structuredClone(v);
  const keyFor=(s,r)=>s==='meta'||s==='settings'?r.key:r.id;
  const db={
    stores,
    get:async(s,k)=>clone(stores[s].get(k)),
    getAll:async s=>[...stores[s].values()].map(clone),
    put:async(s,r)=>{stores[s].set(keyFor(s,r),clone(r));return clone(r);},
    bulkPut:async(s,rows)=>{rows.forEach(r=>stores[s].set(keyFor(s,r),clone(r)));return rows.length;},
    getSetting:async k=>stores.settings.get(k)?.value??null,
    setSetting:async(k,v,source='test')=>{stores.settings.set(k,{key:k,value:v,source,updatedAt:new Date().toISOString()});return v;},
    allSettingsObject:async()=>Object.fromEntries([...stores.settings.values()].map(r=>[r.key,r.value])),
    openDatabase:async()=>({
      transaction(names,mode){
        const tx={error:null};
        tx.objectStore=s=>({
          put:r=>stores[s].set(keyFor(s,r),clone(r)),
          delete:id=>stores[s].delete(id),
          clear:()=>stores[s].clear(),
          get:id=>({onsuccess:null,onerror:null,result:clone(stores[s].get(id))}),
        });
        setImmediate(()=>tx.oncomplete&&tx.oncomplete());
        return tx;
      },
      close(){}
    })
  };
  return db;
}
function makeStorage(){
  const m=new Map();
  return {getItem:k=>m.has(k)?m.get(k):null,setItem:(k,v)=>m.set(k,String(v)),removeItem:k=>m.delete(k),key:i=>[...m.keys()][i]??null,get length(){return m.size;},dump:()=>Object.fromEntries(m)};
}
async function seedBaseMeta(db,sourceSha='a'.repeat(64)){
  db.stores.meta.set('baseDatasetId',{key:'baseDatasetId',value:'tatadiet-base-v2'});
  db.stores.meta.set('baseDatasetSourceSha256',{key:'baseDatasetSourceSha256',value:sourceSha});
  db.stores.ingredients.set('base:ingredient:x',{id:'base:ingredient:x',origin:'base',immutable:true,name:'Base'});
  db.stores.recipes.set('base:recipe:x',{id:'base:recipe:x',origin:'base',immutable:true,title:'Base'});
}
function loadModules(db,storage){
  global.TataDietDB=db;
  global.localStorage=storage;
  const base=path.resolve(__dirname,'../static/assets/js');
  for(const f of ['v5-backup.js','v5-plan-core.js','v5-plan-store.js','site-state.js']){
    const resolved=path.join(base,f); delete require.cache[require.resolve(resolved)]; require(resolved);
  }
  return {backup:global.TataDietBackup,planStore:global.TataDietPlanStore,planCore:global.TataDietPlanCore,state:global.DietSiteState};
}
async function syntheticOldBackup(){
  const db=makeMemoryDb(),storage=makeStorage(); await seedBaseMeta(db); const {backup}=loadModules(db,storage);
  const p1={recordType:'planInstance',id:'usr:plan:old',name:'Piano personale',timezone:'Europe/Rome',startDate:'2026-09-14',baseDatasetId:'tatadiet-base-v2',schemaVersion:1,status:'active',dayIds:['usr:plan:old:day:001'],createdAt:'2026-09-01T00:00:00Z',updatedAt:'2026-09-01T00:00:00Z'};
  const p2={...p1,id:'usr:plan:current',dayIds:['usr:plan:current:day:001'],updatedAt:'2026-09-22T12:00:00Z'};
  const day=(plan,id,type,source='base')=>({recordType:'calendarDay',id,planInstanceId:plan,date:'2026-09-14',sequenceIndex:0,dayType:type,source,adherenceStatus:'planned',baseDayRef:'base:plan-day:001',shift:{type,name:type,startTime:null,endTime:null,endDayOffset:0,capabilities:{reheat:true,refrigeration:true,complexSnack:true}},meals:[],notes:null,createdAt:'2026-09-01T00:00:00Z',updatedAt:'2026-09-01T00:00:00Z'});
  db.stores.planInstances.set(p1.id,p1);db.stores.planInstances.set(p2.id,p2);
  db.stores.calendarDays.set(p1.dayIds[0],day(p1.id,p1.dayIds[0],'D1'));
  db.stores.calendarDays.set(p2.dayIds[0],day(p2.id,p2.dayIds[0],'FREE','personal'));
  db.stores.settings.set('activePlanInstanceId',{key:'activePlanInstanceId',value:p2.id});
  db.stores.settings.set('planStartDate',{key:'planStartDate',value:'2026-09-14'});
  storage.setItem('diet-plan:start-date:v2','2026-09-14'); storage.setItem('diet-plan-shopping:demo','[\"x\"]');
  const env=await backup.createBackup('full');
  delete env.savestate; env.appVersion='6.0.2'; env.data.planInstances.forEach(p=>p.status='active');
  env.integrity.digest=await backup.sha256(backup.canonical({...env,integrity:{algorithm:'sha256',digest:''}}));
  return env;
}
async function runImport(payload,label){
  const db=makeMemoryDb(),storage=makeStorage(); await seedBaseMeta(db,payload.baseDataset.sourceSha256); const mods=loadModules(db,storage);
  const preview=await mods.backup.preview(payload); assert.equal(preview.valid,true,`${label}: preview must be valid: ${preview.errors?.join('; ')}`);
  const result=await mods.backup.importBackup(payload,'replace');
  assert.equal(result.planStartDate,payload.data.settings.planStartDate,`${label}: planStartDate restored`);
  assert.equal(storage.getItem('diet-plan:start-date:v2'),result.planStartDate,`${label}: localStorage bridge restored`);
  const resolved=mods.state.resolveStart('',storage); assert.equal(resolved.value,result.planStartDate,`${label}: UI resolveStart sees restored date`);
  const plans=await db.getAll('planInstances'); const active=plans.filter(p=>p.status==='active'); assert.equal(active.length,1,`${label}: exactly one active plan after restore`);
  assert.equal(active[0].id,result.activePlanInstanceId,`${label}: active plan matches savestate`);
  assert.equal(await db.getSetting('activePlanInstanceId'),result.activePlanInstanceId,`${label}: setting matches active plan`);
  const bundle=await mods.planStore.activeBundle(); assert.ok(bundle,`${label}: active bundle exists`); assert.equal(bundle.plan.id,result.activePlanInstanceId);
  assert.ok(bundle.days.length>0,`${label}: active calendar is populated`);
  const before=structuredClone(bundle.days[0]); const nextDays=structuredClone(bundle.days); nextDays[0].notes='savestate-regression-edit'; nextDays[0].source='personal';
  await mods.planStore.commitState(structuredClone(bundle.plan),nextDays,'savestate-regression');
  const after=await mods.planStore.activeBundle(); assert.equal(after.days[0].notes,'savestate-regression-edit',`${label}: post-restore calendar edit persists`);
  return {label,activePlanId:bundle.plan.id,days:bundle.days.length,activePlans:active.length,warnings:preview.warnings||[],clientState:result.clientState};
}
(async()=>{
  const synthetic=await syntheticOldBackup(); const reports=[await runImport(synthetic,'synthetic-6.0.2')];
  {
    const db=makeMemoryDb(),storage=makeStorage(); await seedBaseMeta(db); const {backup}=loadModules(db,storage);
    const plan={recordType:'planInstance',id:'usr:plan:newfmt',name:'Piano personale',timezone:'Europe/Rome',startDate:'2026-09-14',baseDatasetId:'tatadiet-base-v2',schemaVersion:1,status:'active',dayIds:['usr:plan:newfmt:day:001'],createdAt:'2026-09-22T00:00:00Z',updatedAt:'2026-09-22T00:00:00Z'};
    const day={recordType:'calendarDay',id:plan.dayIds[0],planInstanceId:plan.id,date:'2026-09-14',sequenceIndex:0,dayType:'D1',source:'personal',adherenceStatus:'planned',shift:{type:'D1',name:'Giornata',startTime:'08:00',endTime:'20:00',endDayOffset:0,capabilities:{reheat:true,refrigeration:true,complexSnack:true}},meals:[],notes:'new-format',createdAt:'2026-09-22T00:00:00Z',updatedAt:'2026-09-22T00:00:00Z'};
    db.stores.planInstances.set(plan.id,plan);db.stores.calendarDays.set(day.id,day);db.stores.settings.set('activePlanInstanceId',{key:'activePlanInstanceId',value:plan.id});db.stores.settings.set('planStartDate',{key:'planStartDate',value:'2026-09-14'});
    storage.setItem('diet-plan:start-date:v2','2026-09-14');storage.setItem('diet-plan-shopping:demo','[\"x\"]');
    const modern=await backup.createBackup('full'); assert.equal(modern.savestate.localStorage['diet-plan-shopping:demo'],'[\"x\"]','new backup captures browser savestate');
    storage.setItem('diet-plan-shopping:demo','[]'); const imported=await backup.importBackup(modern,'replace'); assert.equal(storage.getItem('diet-plan-shopping:demo'),'[\"x\"]','new backup restores browser savestate');
    reports.push({label:'synthetic-6.0.4-client-state',activePlanId:imported.activePlanInstanceId,days:1,shoppingStateRestored:true});
  }
  const fixture=process.env.TATADIET_SAVESTATE_FIXTURE;
  if(fixture){
    const payload=JSON.parse(fs.readFileSync(fixture,'utf8')); const report=await runImport(payload,'uploaded-user-backup');
    const currentId=payload.data.settings.activePlanInstanceId;
    const expectedDays=payload.data.calendarDays.filter(d=>d.planInstanceId===currentId);
    assert.equal(report.activePlanId,currentId,'uploaded backup: exact active plan restored');
    assert.equal(report.days,expectedDays.length,'uploaded backup: exact active plan day count restored');
    assert.equal(expectedDays.filter(d=>d.source!=='base').length,11,'uploaded backup fixture should contain 11 customized days');
    reports.push({...report,customizedDays:11});
  }
  console.log(JSON.stringify({status:'ok',release:'6.0.4',checks:{old_backup_compatible:true,localstorage_bridge:true,single_active_plan:true,active_bundle_populated:true,post_restore_edit_persists:true,browser_savestate_roundtrip:true,uploaded_fixture:!!fixture},reports},null,2));
})().catch(e=>{console.error(e);process.exit(1)});
