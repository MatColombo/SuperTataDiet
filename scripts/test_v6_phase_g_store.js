const assert=require('assert');
const diaryCore=require('../static/assets/js/v6-diary-core.js');
global.TataDietDiaryCore=diaryCore;
const rows=new Map();
function tx(){const t={objectStore:()=>({delete:id=>rows.delete(id)})};queueMicrotask(()=>t.oncomplete&&t.oncomplete());return t;}
global.TataDietDB={
  initialize:async()=>{},
  getAll:async name=>name==='diaryDays'?[...rows.values()]:[],
  get:async(name,id)=>name==='diaryDays'?rows.get(id):null,
  put:async(name,value)=>{if(name==='diaryDays')rows.set(value.id,JSON.parse(JSON.stringify(value)));return value;},
  openDatabase:async()=>({transaction:()=>tx(),close:()=>{}}),
};
let events=[
  {id:'m1',sourceDate:'2026-09-08',actualDate:'2026-09-08',time:'08:00',mealType:'Colazione',recipeId:'r1',recipeVersionId:'v1',title:'Colazione',nutrition:{energyKcal:300,proteinG:10,carbohydrateG:40,fatG:8,fiberG:4}},
  {id:'m2',sourceDate:'2026-09-08',actualDate:'2026-09-08',time:'13:00',mealType:'Pranzo',recipeId:'r2',recipeVersionId:'v2',title:'Pranzo',nutrition:{energyKcal:500,proteinG:30,carbohydrateG:60,fatG:15,fiberG:8}},
];
const context={plan:{id:'plan:1'},days:[{date:'2026-09-08',dayType:'D1',shift:{name:'Giornata'}}],maps:{}};
global.TataDietEffectiveStore={context:async()=>context};
global.TataDietEffectiveCore={eventsOnDate:()=>events};
const store=require('../static/assets/js/v6-diary-store.js');
(async()=>{
  let view=await store.dayView('2026-09-08','2026-09-07');assert.strictEqual(view.entries.length,2);assert(view.record==null);
  await store.updatePlanned('2026-09-08',view.entries[0].id,{status:'followed'},'2026-09-07');
  let record=await store.getDay('plan:1','2026-09-08');assert(record.plannedSnapshotFrozen);assert.strictEqual(record.entries.filter(x=>x.entryType==='planned').length,2);assert.strictEqual(record.entries.find(x=>x.sourceMealId==='m2').status,'unlogged');
  events=[{...events[0],id:'new',title:'Piano cambiato'}];
  view=await store.dayView('2026-09-08','2026-09-07');assert(view.entries.some(x=>x.sourceMealId==='m1'));assert(view.entries.some(x=>x.sourceMealId==='m2'));assert(!view.entries.some(x=>x.sourceMealId==='new'));
  view=await store.addManual('2026-09-08',{title:'Cena fuori',time:'20:30',mealType:'Cena',nutrition:{energyKcal:700}},'2026-09-07');assert.strictEqual(view.stats.manualCount,1);const manual=view.entries.find(x=>x.entryType==='manual');assert(manual);
  await store.saveComment('2026-09-08','Turno impegnativo','2026-09-07');record=await store.getDay('plan:1','2026-09-08');assert.strictEqual(record.comment,'Turno impegnativo');
  await store.markAllFollowed('2026-09-08','2026-09-07');view=await store.dayView('2026-09-08','2026-09-07');assert.strictEqual(view.stats.signal,'green');assert.strictEqual(view.stats.adherencePct,100);
  await store.deleteManual('2026-09-08',manual.id,'2026-09-07');view=await store.dayView('2026-09-08','2026-09-07');assert.strictEqual(view.stats.manualCount,0);
  console.log(JSON.stringify({status:'ok',phase:'V6-G-store',checks:{snapshot_freeze:true,status_persistence:true,manual_meal_crud:true,daily_comment:true,mark_all:true}},null,2));
})().catch(error=>{console.error(error);process.exit(1);});
