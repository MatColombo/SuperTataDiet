#!/usr/bin/env node
"use strict";
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
global.structuredClone=global.structuredClone||((v)=>JSON.parse(JSON.stringify(v)));
global.DietCalendarCore=require(path.resolve(__dirname,'../static/assets/js/calendar-core.js'));
const core=require(path.resolve(__dirname,'../static/assets/js/v5-plan-core.js'));
const template=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../v5_data/base/plan-template.base.v1.json'),'utf8'));
const made=core.buildPlan(template,'2026-09-01',template.dataset_version,'2026-09-01T00:00:00Z');
const tailCount=d=>(d.meals||[]).filter(m=>Number(m.dayOffset||0)>0).length;
const date='2026-09-04';
const beforeCount=made.days.length;
const inserted=core.applyAction(made.plan,made.days,'insert-day',{date,dayType:'D2'},template,'2026-09-02T00:00:00Z');
const night=core.byDate(inserted.days,date);
assert.equal(night.dayType,'D2');
assert.ok(night.meals.length>=5,'inserted night should receive a usable menu');
assert.ok(tailCount(night)>=2,'inserted night must include +1 meals');
const nightId=night.id;
const tailIds=new Set(night.meals.filter(m=>m.dayOffset>0).map(m=>m.id));
const removed=core.applyAction(inserted.plan,inserted.days,'remove-day',{date},template,'2026-09-03T00:00:00Z');
assert.equal(removed.days.length,beforeCount);
assert.equal(removed.days.some(d=>d.id===nightId),false);
assert.equal(removed.days.some(d=>(d.meals||[]).some(m=>tailIds.has(m.id))),false,'night tail must disappear with source day');

const d1Date='2026-09-01';
const changed=core.applyAction(made.plan,made.days,'replace-day-type',{date:d1Date,dayType:'D2'},template,'2026-09-02T00:00:00Z');
const converted=core.byDate(changed.days,d1Date);
assert.equal(converted.dayType,'D2');
assert.ok(tailCount(converted)>=2,'changing into night must materialize +1 tail');
const reverted=core.applyAction(changed.plan,changed.days,'replace-day-type',{date:d1Date,dayType:'D1'},template,'2026-09-03T00:00:00Z');
assert.equal(tailCount(core.byDate(reverted.days,d1Date)),0,'leaving night must remove +1 tail');

// Structural edits before an existing night must shift both source date and its civil +1 tail together.
const originalNight=made.days.find(d=>d.dayType==='D2');
const originalTailDate=global.DietCalendarCore.addDays(originalNight.date,1);
const priorDate=global.DietCalendarCore.addDays(originalNight.date,-1);
const shifted=core.applyAction(made.plan,made.days,'insert-day',{date:priorDate,dayType:'D4'},template,'2026-09-02T00:00:00Z');
const sameNight=shifted.days.find(d=>d.id===originalNight.id);
assert.equal(sameNight.date,global.DietCalendarCore.addDays(originalNight.date,1));
assert.equal(global.DietCalendarCore.addDays(sameNight.date,1),global.DietCalendarCore.addDays(originalTailDate,1));
assert.equal(tailCount(sameNight),tailCount(originalNight));
console.log(JSON.stringify({status:'ok',checks:{insert_night_tail:true,remove_night_tail:true,type_change_tail:true,structural_shift_tail:true}},null,2));
