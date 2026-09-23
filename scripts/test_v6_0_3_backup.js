#!/usr/bin/env node
"use strict";
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
global.structuredClone=global.structuredClone||((v)=>JSON.parse(JSON.stringify(v)));
const names=['meta','settings','ingredients','ingredientRevisions','recipes','recipeVersions','planInstances','calendarDays','operations','shoppingChecklists','diaryDays'];
const stores=Object.fromEntries(names.map(n=>[n,new Map()]));
const clone=v=>v===undefined?undefined:structuredClone(v), keyFor=(s,r)=>s==='meta'||s==='settings'?r.key:r.id;
const db={
 get:async(s,k)=>clone(stores[s].get(k)),
 getAll:async s=>[...stores[s].values()].map(clone),
 put:async(s,r)=>{stores[s].set(keyFor(s,r),clone(r));return r},
 allSettingsObject:async()=>Object.fromEntries([...stores.settings.values()].map(r=>[r.key,r.value])),
 openDatabase:async()=>({transaction(){const tx={error:null};tx.objectStore=s=>({put:r=>stores[s].set(keyFor(s,r),clone(r)),delete:id=>stores[s].delete(id),clear:()=>stores[s].clear()});setImmediate(()=>tx.oncomplete&&tx.oncomplete());return tx;},close(){}})
};
global.TataDietDB=db;
require(path.resolve(__dirname,'../static/assets/js/v5-backup.js'));
const backup=global.TataDietBackup;
(async()=>{
 stores.meta.set('baseDatasetId',{key:'baseDatasetId',value:'tatadiet-base-v2'});
 stores.meta.set('baseDatasetSourceSha256',{key:'baseDatasetSourceSha256',value:'a'.repeat(64)});
 stores.ingredients.set('base:ingredient:x',{id:'base:ingredient:x',origin:'base',immutable:true,name:'Base'});
 stores.recipes.set('base:recipe:x',{id:'base:recipe:x',origin:'base',immutable:true,title:'Base'});
 stores.ingredients.set('usr:ingredient:x',{id:'usr:ingredient:x',origin:'personal',name:'Personal'});
 stores.recipes.set('usr:recipe:x',{id:'usr:recipe:x',origin:'personal',title:'Personal recipe'});
 stores.planInstances.set('usr:plan:1',{id:'usr:plan:1',startDate:'2026-09-01',status:'active',dayIds:['usr:day:1']});
 stores.calendarDays.set('usr:day:1',{id:'usr:day:1',planInstanceId:'usr:plan:1',date:'2026-09-01',sequenceIndex:0,dayType:'D1',meals:[]});
 stores.diaryDays.set('usr:diary:1',{id:'usr:diary:1',planInstanceId:'usr:plan:1',date:'2026-09-01',comment:'backup'});
 stores.shoppingChecklists.set('usr:shop:1',{id:'usr:shop:1',scopeKey:'week',checked:{a:true}});
 stores.settings.set('planStartDate',{key:'planStartDate',value:'2026-09-01'});
 stores.settings.set('activePlanInstanceId',{key:'activePlanInstanceId',value:'usr:plan:1'});
 const full=await backup.createBackup('full');
 assert.equal(full.mode,'full'); assert.equal((await backup.preview(full)).valid,true);
 assert.equal(full.data.diaryDays.length,1); assert.equal(full.data.shoppingChecklists.length,1);
 // mutate everything personal, then restore.
 stores.ingredients.set('usr:ingredient:y',{id:'usr:ingredient:y',origin:'personal',name:'Temporary'});
 stores.calendarDays.get('usr:day:1').dayType='D2';
 stores.diaryDays.get('usr:diary:1').comment='mutated';
 stores.settings.set('planStartDate',{key:'planStartDate',value:'2030-01-01'});
 const result=await backup.importBackup(full,'replace');
 assert.ok(result.imported.calendarDays===1 && result.imported.diaryDays===1);
 assert.equal(stores.ingredients.has('usr:ingredient:y'),false);
 assert.equal(stores.ingredients.has('base:ingredient:x'),true,'base catalog must survive restore');
 assert.equal(stores.calendarDays.get('usr:day:1').dayType,'D1');
 assert.equal(stores.diaryDays.get('usr:diary:1').comment,'backup');
 assert.equal(stores.settings.get('planStartDate').value,'2026-09-01');
 assert.ok(stores.meta.get('preImportRollback')?.value,'automatic checkpoint must exist');
 // UI contract: no legacy/merge/partial import controls.
 const html=fs.readFileSync(path.resolve(__dirname,'../templates/tools.html'),'utf8');
 assert.ok(html.includes('data-v5-restore-backup'));
 assert.ok(html.includes('Ripristina tutto dal backup'));
 assert.ok(!html.includes('data-v5-import-mode'));
 assert.ok(!html.includes('data-import-preferences'));
 assert.ok(!html.includes('>Unisci<'));
 const ui=fs.readFileSync(path.resolve(__dirname,'../static/assets/js/v5-tools.js'),'utf8');
 assert.ok(ui.includes('payload.mode !== "full"'));
 assert.ok(ui.includes('backup.importBackup(pendingBackup, "replace")'));
 console.log(JSON.stringify({status:'ok',checks:{full_backup:true,restore_roundtrip:true,base_preserved:true,diary_and_shopping:true,checkpoint:true,single_restore_ui:true,no_legacy_ui:true}},null,2));
})().catch(e=>{console.error(e);process.exit(1)});
