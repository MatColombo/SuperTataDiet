#!/usr/bin/env node
'use strict';
const assert=require('node:assert/strict');
const intel=require('../static/assets/js/v6-ingredient-intelligence-core.js');
const diary=require('../static/assets/js/v6-diary-core.js');
const constraints=require('../static/assets/js/v6-constraint-core.js');
const planner=require('../static/assets/js/v6-planner-core.js');
assert.equal(typeof intel.compareEqualEnergy,'function');
assert.equal(typeof intel.rankAlternatives,'function');
assert.equal(typeof constraints.evaluatePlan,'function');
assert.equal(typeof planner.planDay,'function');
assert.equal(typeof diary.dayStats,'function');
const source={id:'riso',name:'Riso',basis:{amount:100,unit:'g'},nutrition:{energyKcal:360,proteinG:7,carbohydrateG:80,fatG:1,fiberG:1},classId:'dry-rice',primaryRole:'carbohydrate',category:'cereali',preparationState:'dry'};
const target={id:'pasta',name:'Pasta',basis:{amount:100,unit:'g'},nutrition:{energyKcal:350,proteinG:12,carbohydrateG:72,fatG:2,fiberG:3},classId:'dry-pasta',primaryRole:'carbohydrate',category:'cereali',preparationState:'dry'};
const policy={semantics:{compatibility_neighbours:{'dry-rice':['dry-pasta']}},conversion:{very_compatible_min_score:80,compatible_min_score:60,with_differences_min_score:35,greedy_min_score:50,plausible_quantity_ranges:{'dry-pasta':{min:20,max:180}}}};
const cmp=intel.compareEqualEnergy(source,80,target,policy);
assert(Math.abs(cmp.sourceNutrition.energyKcal-cmp.targetNutrition.energyKcal)<0.05);
assert(Number.isFinite(cmp.delta.proteinG.absolute));
const entries=[
  {entryType:'planned',status:'followed'},
  {entryType:'planned',status:'partial'},
  {entryType:'manual',status:'unlogged'}
];
const stats=diary.dayStats(entries);
assert.equal(stats.plannedCount,2);assert.equal(stats.manualCount,1);assert.equal(stats.adherencePct,75);assert.equal(stats.signal,'yellow');
console.log(JSON.stringify({status:'ok',phase:'V6-H',checks:{core_api_surface:true,equal_energy_converter:true,nutrition_delta:true,diary_adherence_semantics:true}},null,2));
