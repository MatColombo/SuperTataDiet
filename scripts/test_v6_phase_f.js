const assert=require('assert');
const core=require('../static/assets/js/v5-composer-core.js');
const intel=require('../static/assets/js/v6-ingredient-intelligence-core.js');

const ingredients=new Map([
  ['i:ceci',{id:'i:ceci',name:'Ceci',aliases:['garbanzo']}],
  ['i:riso',{id:'i:riso',name:'Riso basmati',aliases:['basmati']}],
]);
const recipe={id:'r:1',title:'Bowl mediterranea',currentVersionId:'v:1',mealTypes:['Pranzo'],cuisines:['Italiana'],origin:'base'};
const version={id:'v:1',recipeId:'r:1',ingredientLines:[{ingredientId:'i:ceci',baseQuantity:120,baseUnit:'g'},{ingredientId:'i:riso',baseQuantity:70,baseUnit:'g'}],calculatedNutrition:{energyKcal:510,proteinG:22,carbohydrateG:76,fatG:11,fiberG:10},metadata:{mealTypes:['Pranzo'],cuisine:'Italiana',tags:['bowl'],prepMinutes:15,mealPrep:{}}};
const entry=core.entryFrom(recipe,version,ingredients);
assert(entry.ingredientNames.includes('Ceci'));
assert(entry.ingredientNames.includes('Riso basmati'));
assert(core.matchesSearch(entry,'ceci'));
assert(core.matchesSearch(entry,'garbanzo'));
assert(core.matchesSearch(entry,'basmati'));
assert(core.matchesSearch(entry,'mediterranea'));
assert(!core.matchesSearch(entry,'salmone'));
assert.strictEqual(core.mealRecord({id:'d:1'},{time:'13:00',dayOffset:0,mealType:'Pranzo'},entry,1).portionMultiplier,1);

// Equal-energy conversion remains separate from compatibility.
const source={id:'riso',name:'Riso',basis:{amount:100,unit:'g'},nutrition:{energyKcal:360,proteinG:7,carbohydrateG:80,fatG:1,fiberG:1},classId:'dry-rice',primaryRole:'carbohydrate',category:'cereali',preparationState:'dry'};
const target={id:'pasta',name:'Pasta',basis:{amount:100,unit:'g'},nutrition:{energyKcal:350,proteinG:12,carbohydrateG:72,fatG:2,fiberG:3},classId:'dry-pasta',primaryRole:'carbohydrate',category:'cereali',preparationState:'dry'};
const policy={semantics:{compatibility_neighbours:{'dry-rice':['dry-pasta']}},conversion:{very_compatible_min_score:80,compatible_min_score:60,with_differences_min_score:35,greedy_min_score:50,plausible_quantity_ranges:{'dry-pasta':{min:20,max:180}}}};
const cmp=intel.compareEqualEnergy(source,80,target,policy);
assert(Math.abs(cmp.sourceNutrition.energyKcal-cmp.targetNutrition.energyKcal)<0.05);
assert(cmp.targetQuantity>80 && cmp.targetQuantity<85);
assert(cmp.delta && Number.isFinite(cmp.delta.proteinG.absolute));
console.log(JSON.stringify({status:'ok',phase:'V6-F',checks:{ingredient_search:true,alias_search:true,fixed_serving:true,equal_energy_delta:true}},null,2));
