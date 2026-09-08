(function(global,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  global.TataDietIngredientIntelligence=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';

  const NUTRIENT_KEYS=['energyKcal','proteinG','carbohydrateG','fatG','fiberG'];
  const POLICY_CACHE=new WeakMap();
  const CODE_CLASS_CACHE=new WeakMap();
  const CLASS_ROLE_CACHE=new WeakMap();
  const DEFAULT_POLICY={
    conversion:{
      energy_tolerance_kcal:.05,greedy_min_score:58,very_compatible_min_score:82,compatible_min_score:62,with_differences_min_score:40,max_default_results:12,allow_energy_only_in_search:true,allow_energy_only_in_greedy:false,
      quantity_plausibility:{other:[5,600]}
    },
    semantics:{classes:{},primary_roles:{},compatibility_neighbours:{}}
  };

  function normalize(value){return String(value||'').toLocaleLowerCase('it').normalize('NFD').replace(/[\u0300-\u036f]/g,'').trim();}
  function num(value,fallback=0){const n=Number(value);return Number.isFinite(n)?n:fallback;}
  function round(value,digits=3){const p=10**digits;return Math.round((num(value)+Number.EPSILON)*p)/p;}
  function unique(values){return [...new Set((values||[]).filter(Boolean))];}
  function deepMerge(base,extra){
    if(Array.isArray(extra))return extra.slice();
    if(!extra||typeof extra!=='object')return extra===undefined?base:extra;
    const out={...(base&&typeof base==='object'&&!Array.isArray(base)?base:{})};
    Object.entries(extra).forEach(([k,v])=>{out[k]=v&&typeof v==='object'&&!Array.isArray(v)?deepMerge(out[k],v):Array.isArray(v)?v.slice():v;});
    return out;
  }
  function policy(input){
    if(!input||typeof input!=='object')return DEFAULT_POLICY;
    if(input.__tatadietResolvedPolicy)return input;
    if(POLICY_CACHE.has(input))return POLICY_CACHE.get(input);
    const resolved=deepMerge(DEFAULT_POLICY,input);Object.defineProperty(resolved,'__tatadietResolvedPolicy',{value:true,enumerable:false});POLICY_CACHE.set(input,resolved);return resolved;
  }

  function ingredientCode(ingredient){
    if(ingredient?.code)return String(ingredient.code);
    const id=String(ingredient?.id||'');
    const m=id.match(/^base:ingredient:([^:]+)$/);if(m)return m[1];
    return normalize(ingredient?.name||'ingrediente').replace(/[^a-z0-9]+/g,'_').replace(/^_+|_+$/g,'');
  }
  function categoryOf(ingredient){return ingredient?.category||ingredient?.category_id||ingredient?.category_name||'altro';}
  function nutritionOf(revisionOrIngredient){
    const src=revisionOrIngredient?.nutrition||revisionOrIngredient?.nutrients||{};
    return {
      energyKcal:num(src.energyKcal??src.energy_kcal),proteinG:num(src.proteinG??src.protein_g),carbohydrateG:num(src.carbohydrateG??src.carbohydrate_g),fatG:num(src.fatG??src.fat_g),fiberG:num(src.fiberG??src.fiber_g),
      sugarsG:src.sugarsG??src.sugars_g??null,saturatedFatG:src.saturatedFatG??src.saturated_fat_g??null,saltG:src.saltG??src.salt_g??null,sodiumMg:src.sodiumMg??src.sodium_mg??null
    };
  }
  function basisOf(revisionOrIngredient){
    const b=revisionOrIngredient?.basis||revisionOrIngredient?.nutrition_basis||{amount:100,unit:'g'};
    return {amount:num(b.amount,100)||100,unit:b.unit==='ml'?'ml':'g'};
  }
  function preparationStateOf(revisionOrIngredient){return revisionOrIngredient?.preparationState||revisionOrIngredient?.food_state||'unknown';}
  function codeClassMap(p){
    const pol=policy(p);if(CODE_CLASS_CACHE.has(pol))return CODE_CLASS_CACHE.get(pol);const out=new Map();Object.entries(pol.semantics.classes||{}).forEach(([cls,codes])=>(codes||[]).forEach(code=>{if(!out.has(code))out.set(code,cls);}));CODE_CLASS_CACHE.set(pol,out);return out;
  }
  function classRoleMap(p){
    const pol=policy(p);if(CLASS_ROLE_CACHE.has(pol))return CLASS_ROLE_CACHE.get(pol);const out=new Map();Object.entries(pol.semantics.primary_roles||{}).forEach(([role,classes])=>(classes||[]).forEach(cls=>{if(!out.has(cls))out.set(cls,role);}));CLASS_ROLE_CACHE.set(pol,out);return out;
  }
  function heuristicClass(ingredient,revision){
    const name=normalize(ingredient?.name),cat=normalize(categoryOf(ingredient)),n=nutritionOf(revision);
    if(cat.includes('pesce'))return n.fatG>=8?'fatty-fish':'lean-white-fish';
    if(cat.includes('legumi'))return 'legume';
    if(cat.includes('carne'))return /prosciutto|bresaola|affett/.test(name)?'cold-cut':'fresh-red-meat';
    if(cat.includes('latticini')){
      if(/uov|albume/.test(name))return 'egg';
      if(/latte|yogurt|kefir|skyr/.test(name))return 'milk-yogurt';
      return n.fatG>=24?'aged-cheese':'fresh-cheese';
    }
    if(cat.includes('cereali')){
      if(/pasta/.test(name))return 'dry-pasta';if(/riso/.test(name))return 'dry-rice';if(/patat|gnocch/.test(name))return 'potato';if(/pane|piadin|tortilla/.test(name))return 'bread';if(/cracker|fett.*bisc|gallett/.test(name))return 'cracker-rusk';if(/avena|cornflake/.test(name))return 'breakfast-cereal';return 'dry-grain';
    }
    if(cat.includes('frutta secca'))return /burro|crema/.test(name)?'spread':'nuts-seeds';
    if(cat.includes('condimenti')){if(n.fatG>=80)return 'cooking-fat';if(/miele|marmell|confett/.test(name))return 'sweetener';return 'sauce';}
    if(cat.includes('ortofrutta')){
      if(/avocado/.test(name))return 'culinary-fat-fruit';
      if(/mela|pera|banana|aranci|kiwi|uva|fico|prugn|pompelm|mandarin|cachi|melagran|frutti.*bosco/.test(name))return 'fruit';
      if(/spinac|bietol|lattug|cicori|indivi|radicch|verza|cavolo nero/.test(name))return 'leafy-vegetable';
      if(/broccol|cavolfior|cavolett|cappuccio/.test(name))return 'cruciferous-vegetable';
      if(/carot|barbab|cipoll|finocch|porr|rapa|sedan/.test(name))return 'root-bulb-vegetable';
      if(/zucchin|melanz|pomodor|cetriol/.test(name))return 'summer-fruit-vegetable';return 'other-vegetable';
    }
    return 'other';
  }
  function roleForClass(cls,p){return classRoleMap(p).get(cls)||'other';}
  function semanticsFor(ingredient,revision,p){
    const pol=policy(p),code=ingredientCode(ingredient),cls=codeClassMap(pol).get(code)||heuristicClass(ingredient,revision),role=roleForClass(cls,pol);
    const traits=[];const state=preparationStateOf(revision);if(['dry','drained','prepared','ready-to-eat','as-sold'].includes(state))traits.push(state);
    if(['fresh-cheese','milk-yogurt','fresh-meat','fresh-poultry','fresh-red-meat','fresh-rabbit','lean-white-fish','fatty-fish','seafood'].includes(cls))traits.push('perishable');
    if(['dry-pasta','dry-rice','dry-grain','breakfast-cereal','cracker-rusk','nuts-seeds','cooking-fat','sweetener'].includes(cls))traits.push('pantry');
    return {code,classId:cls,primaryRole:role,traits:unique(traits)};
  }
  function makeEntry(ingredient,revision,p){
    if(!ingredient)return null;const rev=revision||ingredient.revision||ingredient.currentRevision||ingredient.current_revision||ingredient;
    const sem=semanticsFor(ingredient,rev,p),nutrition=nutritionOf(rev),basis=basisOf(rev),aliases=Array.isArray(ingredient.aliases)?ingredient.aliases:[];
    return {ingredient,revision:rev,id:ingredient.id||sem.code,code:sem.code,name:ingredient.name||sem.code,aliases,category:categoryOf(ingredient),basis,nutrition,preparationState:preparationStateOf(rev),classId:sem.classId,primaryRole:sem.primaryRole,traits:sem.traits,searchText:normalize([ingredient.name,sem.code,...aliases,categoryOf(ingredient),sem.classId,sem.primaryRole].join(' '))};
  }
  function makeCatalog(ingredients,revisions,p){
    const revs=new Map((revisions||[]).map(r=>[r.id,r]));return (ingredients||[]).map(i=>makeEntry(i,revs.get(i.currentRevisionId||i.revision_id)||i.revision,p)).filter(Boolean);
  }
  function makeBaseCatalog(baseIngredients,p){return (baseIngredients||[]).map(i=>makeEntry(i,i,p)).filter(Boolean);}
  function nutritionForQuantity(entry,quantity){
    const q=num(quantity,NaN),basis=entry?.basis||{amount:100,unit:'g'};if(!Number.isFinite(q)||q<0||!num(basis.amount))return null;const f=q/num(basis.amount,100),out={};NUTRIENT_KEYS.forEach(k=>out[k]=round(num(entry?.nutrition?.[k])*f,4));return out;
  }
  function energyForQuantity(entry,quantity){return nutritionForQuantity(entry,quantity)?.energyKcal??null;}
  function equivalentQuantity(source,sourceQuantity,target){
    const kcal=energyForQuantity(source,sourceQuantity),targetDensity=num(target?.nutrition?.energyKcal),basisAmount=num(target?.basis?.amount,100);if(!(kcal>0)||!(targetDensity>0)||!(basisAmount>0))return null;return round(kcal/targetDensity*basisAmount,2);
  }
  function nutrientDistance(a,b){
    const weights={proteinG:1.8,carbohydrateG:1.4,fatG:1.4,fiberG:.7};let total=0,w=0;Object.entries(weights).forEach(([k,weight])=>{const av=Math.abs(num(a?.[k])),bv=Math.abs(num(b?.[k]));const scale=Math.max(2,av,bv);total+=Math.abs(bv-av)/scale*weight;w+=weight;});return w?total/w:1;
  }
  function quantityPlausibility(entry,quantity,p){
    const pol=policy(p),range=pol.conversion.quantity_plausibility?.[entry?.classId]||pol.conversion.quantity_plausibility?.other||[5,600],q=num(quantity,NaN);if(!Number.isFinite(q)||q<=0)return {plausible:false,score:-25,range};
    if(q>=range[0]&&q<=range[1])return {plausible:true,score:10,range};
    const ratio=q<range[0]?range[0]/Math.max(q,.01):q/range[1];return {plausible:false,score:ratio<=1.6?-6:ratio<=3?-16:-30,range};
  }
  function compatibility(source,target,sourceQuantity,p){
    const pol=policy(p);if(!source||!target)return {score:0,classification:'energy-only',suggestable:false,reasons:[],warnings:['Ingrediente non disponibile']};
    if(source.id===target.id)return {score:100,classification:'same',suggestable:false,reasons:['stesso ingrediente'],warnings:[]};
    const q=equivalentQuantity(source,sourceQuantity,target);if(q===null)return {score:0,classification:'energy-only',suggestable:false,reasons:[],warnings:['Equivalenza kcal non calcolabile']};
    const sourceN=nutritionForQuantity(source,sourceQuantity),targetN=nutritionForQuantity(target,q),reasons=[],warnings=[];let score=0;
    if(source.classId===target.classId){score+=58;reasons.push('stessa famiglia funzionale');}
    else if((pol.semantics.compatibility_neighbours?.[source.classId]||[]).includes(target.classId)){score+=32;reasons.push('famiglia culinaria vicina');}
    if(source.primaryRole===target.primaryRole){score+=22;reasons.push('stesso ruolo nel pasto');}else if(['protein','carbohydrate','produce','fat','condiment'].includes(source.primaryRole)&&['protein','carbohydrate','produce','fat','condiment'].includes(target.primaryRole)){score-=28;warnings.push('ruolo alimentare diverso');}
    if(source.category===target.category)score+=5;
    if(source.preparationState===target.preparationState&&source.preparationState!=='unknown')score+=3;
    const dist=nutrientDistance(sourceN,targetN);score+=Math.max(-18,18-dist*35);if(dist<=.2)reasons.push('profilo macro vicino');else if(dist>.55)warnings.push('macro sensibilmente diversi');
    const plausible=quantityPlausibility(target,q,pol);score+=plausible.score;if(!plausible.plausible)warnings.push(`quantità equivalente poco pratica (${round(q,1)} ${target.basis.unit})`);
    score=Math.max(0,Math.min(100,round(score,1)));
    let classification='energy-only';if(score>=pol.conversion.very_compatible_min_score&&source.primaryRole===target.primaryRole&&source.classId===target.classId)classification='very-compatible';else if(score>=pol.conversion.compatible_min_score&&source.primaryRole===target.primaryRole)classification='compatible';else if(score>=pol.conversion.with_differences_min_score)classification='with-differences';
    const suggestable=classification!=='energy-only'&&score>=pol.conversion.greedy_min_score&&plausible.plausible;
    return {score,classification,suggestable,reasons:unique(reasons),warnings:unique(warnings),equivalentQuantity:q,equivalentUnit:target.basis.unit,sourceNutrition:sourceN,targetNutrition:targetN,macroDistance:round(dist,4),quantityPlausible:plausible.plausible,quantityRange:plausible.range};
  }
  function deltaNutrition(sourceNutrition,targetNutrition){
    const out={};NUTRIENT_KEYS.forEach(k=>{const a=num(sourceNutrition?.[k]),b=num(targetNutrition?.[k]);out[k]={absolute:round(b-a,4),percent:Math.abs(a)>.0001?round((b-a)/a*100,1):null};});return out;
  }
  function compareEqualEnergy(source,sourceQuantity,target,p){
    const match=compatibility(source,target,sourceQuantity,p);if(match.equivalentQuantity==null)return {...match,delta:null};return {...match,sourceQuantity:num(sourceQuantity),sourceUnit:source.basis.unit,targetQuantity:match.equivalentQuantity,targetUnit:target.basis.unit,delta:deltaNutrition(match.sourceNutrition,match.targetNutrition)};
  }
  function rankAlternatives(source,sourceQuantity,catalog,p,options={}){
    const pol=policy(p),limit=num(options.limit,pol.conversion.max_default_results)||12,query=normalize(options.query),includeEnergyOnly=options.includeEnergyOnly===true;
    let rows=(catalog||[]).filter(x=>x&&x.id!==source?.id);
    if(query)rows=rows.filter(x=>x.searchText.includes(query));
    rows=rows.map(target=>({target,...compareEqualEnergy(source,sourceQuantity,target,pol)})).filter(x=>x.equivalentQuantity!=null);
    if(!includeEnergyOnly)rows=rows.filter(x=>x.suggestable);
    rows.sort((a,b)=>b.score-a.score||Number(b.quantityPlausible)-Number(a.quantityPlausible)||String(a.target.name).localeCompare(String(b.target.name),'it'));
    return rows.slice(0,limit);
  }
  function searchAlternatives(source,sourceQuantity,catalog,query,p,options={}){
    const pol=policy(p);return rankAlternatives(source,sourceQuantity,catalog,pol,{...options,query,includeEnergyOnly:options.includeEnergyOnly!==false&&pol.conversion.allow_energy_only_in_search!==false,limit:options.limit||50});
  }
  function recipeLineCode(line,ingredientById){
    if(line?.ingredient_code)return line.ingredient_code;const id=line?.ingredientId||line?.ingredient_id;const ing=ingredientById?.get?.(id);return ing?ingredientCode(ing):String(id||'').replace(/^base:ingredient:/,'');
  }
  function recipeIngredientFacts(version,ingredientCatalog,p){
    const entries=ingredientCatalog instanceof Map?ingredientCatalog:new Map((ingredientCatalog||[]).map(x=>[x.id||x.ingredient?.id,x]));const byCode=new Map((ingredientCatalog instanceof Map?[...ingredientCatalog.values()]:(ingredientCatalog||[])).map(x=>[x.code,x]));
    const protein=new Map(),carbs=new Map(),quantities=new Map(),codes=new Set(),classes=new Set();
    const lines=version?.ingredientLines||version?.ingredient_lines||[];
    for(const line of lines){const id=line.ingredientId||line.ingredient_id,entry=entries.get(id)||byCode.get(line.ingredient_code),code=entry?.code||line.ingredient_code||String(id||'').replace(/^base:ingredient:/,'');if(!code)continue;codes.add(code);if(entry?.classId)classes.add(entry.classId);const q=num(line.baseQuantity??line.base_quantity??line.quantity);quantities.set(code,num(quantities.get(code))+q);if(!entry)continue;const n=nutritionForQuantity(entry,q)||{};if(entry.primaryRole==='protein')protein.set(entry.classId,num(protein.get(entry.classId))+num(n.proteinG));if(entry.primaryRole==='carbohydrate')carbs.set(entry.classId,num(carbs.get(entry.classId))+num(n.carbohydrateG));}
    return {codes:[...codes],classes:[...classes],quantities,protein,carbs};
  }
  function groupedPrimary(contributions,classToGroup,minValue=0,minShare=0){
    const groupValues=new Map();for(const [cls,value] of contributions.entries()){const group=classToGroup[cls]||cls;groupValues.set(group,num(groupValues.get(group))+num(value));}if(!groupValues.size)return {group:null,value:0,share:0,contributions:{}};const sorted=[...groupValues.entries()].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]));const [group,value]=sorted[0],total=sorted.reduce((s,x)=>s+x[1],0),share=total?value/total:0;return {group:value>=minValue&&share>=minShare?group:null,value:round(value,3),share:round(share,4),contributions:Object.fromEntries(sorted.map(([k,v])=>[k,round(v,3)]))};
  }
  function classifyRecipeVersion(version,recipe,ingredientCatalog,phaseAPolicy){
    const facts=recipeIngredientFacts(version,ingredientCatalog,phaseAPolicy),hard=phaseAPolicy?.hard_constraints||{},primary=phaseAPolicy?.classification?.primary_source||{};
    const proteinGroupMap={legume:'legumes',egg:'eggs','fresh-cheese':'cheese','aged-cheese':'cheese','milk-yogurt':'milk_yogurt','fresh-poultry':'poultry','fresh-red-meat':'red_meat','fresh-rabbit':'red_meat','cold-cut':'cold_cuts','lean-white-fish':'fish','fatty-fish':'fish',seafood:'fish','preserved-fish':'fish'};
    const carbGroupMap={'dry-pasta':'pasta','dry-rice':'rice','dry-grain':'other_grains',potato:'potato',bread:'bread','breakfast-cereal':'other_grains','cracker-rusk':'crackers_rusks_cakes','flour-breading':'other_grains'};
    const pp=groupedPrimary(facts.protein,proteinGroupMap,num(primary.minimum_protein_g,4),num(primary.minimum_share_of_recognized_group_contribution,.4));
    const pc=groupedPrimary(facts.carbs,carbGroupMap,num(primary.minimum_carbohydrate_g,8),num(primary.minimum_share_of_recognized_group_contribution,.4));
    let egg=0;Object.entries(hard.egg_equivalent?.ingredients||{}).forEach(([code,cfg])=>egg+=num(facts.quantities.get(code))/Math.max(.001,num(cfg.grams_per_unit,50)));
    const dairyCodes=new Set(hard.cheese_dairy?.included_codes||[]),dairy=[...facts.codes].filter(c=>dairyCodes.has(c));
    const legumeCodes=new Set(hard.plant_protein_main?.legume_codes||[]),legumeQty=[...legumeCodes].reduce((s,c)=>s+num(facts.quantities.get(c)),0),legumeProtein=num(pp.contributions.legumes),recognized=[...facts.protein.values()].reduce((s,v)=>s+num(v),0),legumeShare=recognized?legumeProtein/recognized:0;
    const plantMain=pp.group===(hard.plant_protein_main?.qualifying_group||'legumes')&&legumeQty>=num(hard.plant_protein_main?.min_legume_base_quantity_g,70)&&legumeProtein>=num(hard.plant_protein_main?.min_group_protein_g,6)&&legumeShare>=num(hard.plant_protein_main?.min_group_share_of_recognized_protein,.5);
    const foodGroups=[];if(egg>0)foodGroups.push('eggs');if(dairy.length)foodGroups.push('cheese');if(facts.classes.includes('milk-yogurt'))foodGroups.push('milkYogurt');if(facts.classes.includes('cold-cut'))foodGroups.push('coldCuts');if(['fish'].includes(pp.group)||facts.classes.some(c=>['lean-white-fish','fatty-fish','seafood','preserved-fish'].includes(c)))foodGroups.push('fish');if(facts.classes.includes('legume'))foodGroups.push('legumes');if(pp.group==='red_meat')foodGroups.push('redMeat');
    return {recipeVersionId:version?.id||null,recipeId:version?.recipeId||version?.recipe_id||recipe?.id||null,ingredientCodes:facts.codes,ingredientClasses:facts.classes,ingredientQuantities:Object.fromEntries([...facts.quantities.entries()].map(([k,v])=>[k,round(v,3)])),eggEquivalentUnits:round(egg,4),dairyOccurrence:Boolean(dairy.length),dairyCodes:dairy,primaryProtein:pp.group,primaryProteinG:pp.value,primaryProteinShare:pp.share,proteinGroupContributionsG:pp.contributions,legumeQuantityG:round(legumeQty,3),legumeProteinG:round(legumeProtein,3),legumeShareOfRecognizedProtein:round(legumeShare,4),plantProteinMain:plantMain,primaryCarb:pc.group,primaryCarbG:pc.value,primaryCarbShare:pc.share,carbGroupContributionsG:pc.contributions,pastaRicePrimary:['pasta','rice'].includes(pc.group),foodGroups:unique(foodGroups)};
  }

  return {NUTRIENT_KEYS,normalize,num,round,policy,ingredientCode,categoryOf,nutritionOf,basisOf,preparationStateOf,semanticsFor,makeEntry,makeCatalog,makeBaseCatalog,nutritionForQuantity,energyForQuantity,equivalentQuantity,nutrientDistance,quantityPlausibility,compatibility,deltaNutrition,compareEqualEnergy,rankAlternatives,searchAlternatives,recipeIngredientFacts,classifyRecipeVersion};
});
