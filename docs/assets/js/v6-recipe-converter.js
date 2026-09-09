(function(){
  'use strict';
  if(document.body?.dataset.page!=='recipe')return;
  const db=globalThis.TataDietDB,intel=globalThis.TataDietIngredientIntelligence,store=globalThis.TataDietV6IntelligenceStore;
  const host=document.querySelector('[data-v6-recipe-converter]');
  if(!host||!db||!intel||!store)return;
  const q=s=>host.querySelector(s),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt=(n,d=1)=>Number.isFinite(Number(n))?Number(n).toLocaleString('it-IT',{maximumFractionDigits:d}):'—';
  const norm=v=>intel.normalize(v);
  const classLabel={
    'very-compatible':'Molto compatibile',
    'compatible':'Compatibile',
    'with-differences':'Con differenze',
    'energy-only':'Solo equivalenza energetica'
  };
  let lib=null,recipe=null,versions=[],version=null,line=null,selected=null,query='';

  function quantity(line){return Number(line?.baseQuantity??line?.base_quantity??line?.quantity);}
  function unit(line){return line?.baseUnit||line?.base_unit||line?.unit||'g';}
  function ingredientFor(line){return lib?.ingredientById?.get(line?.ingredientId||line?.ingredient_id)||null;}
  function linesOf(v){return (v?.ingredientLines||v?.ingredient_lines||[]).filter(x=>ingredientFor(x)&&Number.isFinite(quantity(x))&&quantity(x)>0);}
  function nutritionCells(n){return [
    ['kcal','energyKcal',0],['Proteine','proteinG',1],['Carboidrati','carbohydrateG',1],['Grassi','fatG',1],['Fibre','fiberG',1]
  ].map(([label,key,d])=>`<span><b>${fmt(n?.[key],d)}</b><small>${label}${key==='energyKcal'?'':' g'}</small></span>`).join('');}
  function deltaText(v,key){const x=v?.delta?.[key]?.absolute;if(!Number.isFinite(Number(x)))return '—';const d=key==='energyKcal'?0:1,n=Number(x);return `${n>0?'+':''}${fmt(n,d)}${key==='energyKcal'?'':' g'}`;}
  function recipeMatch(recipes,id,title,slug){const exact=(recipes||[]).find(r=>!r.archivedAt&&r.id===id);if(exact)return exact;const n=norm(title);let rows=(recipes||[]).filter(r=>!r.archivedAt&&norm(r.title)===n);if(!rows.length)rows=(recipes||[]).filter(r=>!r.archivedAt&&(norm(r.title).includes(n)||n.includes(norm(r.title))));if(rows.length>1){const s=norm(slug);rows.sort((a,b)=>Number(norm(a.id).includes(s))-Number(norm(b.id).includes(s)));}return rows.at(-1)||null;}
  function densityText(entry){const kcal=Number(entry?.nutrition?.energyKcal),amount=Number(entry?.basis?.amount||100),u=entry?.basis?.unit||'g';if(!(kcal>0)||!(amount>0))return 'densità kcal —';if((u==='g'||u==='ml')&&amount!==100)return `${fmt(kcal/amount*100,0)} kcal/100 ${u}`;return `${fmt(kcal,0)} kcal/${fmt(amount,0)} ${u}`;}
  function versionSummary(v){const lines=linesOf(v),n=v?.calculatedNutrition||v?.manualNutrition||{};return `Versione ${Math.max(1,versions.indexOf(v)+1)} di ${versions.length} · ${fmt(n.energyKcal,0)} kcal · ${lines.length} ingredienti`;}
  function renderVersion(){
    const sel=q('[data-converter-version]'),row=q('[data-converter-version-row]');
    const info=q('[data-converter-version-info]');
    if(versions.length>1){row.hidden=false;sel.innerHTML=versions.map((v,i)=>{const n=v.calculatedNutrition||v.manualNutrition||{};return `<option value="${esc(v.id)}">Versione ${i+1} · ${fmt(n.energyKcal,0)} kcal</option>`;}).join('');sel.value=version.id;}
    else row.hidden=true;
    if(info)info.textContent=versionSummary(version);
  }
  function renderLines(){
    const lines=linesOf(version),box=q('[data-converter-source-list]');
    if(!lines.length){box.innerHTML='<div class="empty-state compact"><strong>Nessun ingrediente convertibile</strong><span>Questa versione non ha quantità strutturate.</span></div>';q('[data-converter-source-summary]').innerHTML='';q('[data-converter-results]').innerHTML='';return;}
    if(!line||!lines.some(x=>x.id===line.id))line=lines[0];
    box.innerHTML=lines.map(x=>{const ing=ingredientFor(x),active=x.id===line.id;return `<button type="button" class="converter-source-item${active?' is-active':''}" data-converter-line="${esc(x.id)}"><span>${esc(ing.name)}</span><b>${fmt(quantity(x),1)} ${esc(unit(x))}</b></button>`;}).join('');
    box.querySelectorAll('[data-converter-line]').forEach(b=>b.onclick=()=>{line=lines.find(x=>x.id===b.dataset.converterLine)||line;selected=null;query='';q('[data-converter-search]').value='';renderLines();renderAlternatives();});
    const ing=ingredientFor(line),n=intel.nutritionForQuantity(ing,quantity(line));
    q('[data-converter-source-summary]').innerHTML=`<div><p class="eyebrow">Ingrediente originale</p><h3>${esc(ing.name)} · ${fmt(quantity(line),1)} ${esc(unit(line))}</h3><p>${fmt(n?.energyKcal,0)} kcal nella ricetta · ${esc(densityText(ing))}</p></div><div class="converter-mini-nutrition">${nutritionCells(n)}</div>`;
  }
  async function alternatives(){
    if(!line)return[];
    if(query.trim())return store.searchForLine(line,query,{limit:40,includeEnergyOnly:true});
    return store.suggestedForLine(line,{limit:12});
  }
  function renderComparison(row){
    selected=row;const box=q('[data-converter-comparison]');
    if(!row){box.hidden=true;box.innerHTML='';return;}
    const source=ingredientFor(line),target=row.target;
    box.hidden=false;box.innerHTML=`
      <div class="converter-compare-head"><div><p class="eyebrow">Confronto READ</p><h3>${esc(source.name)} → ${esc(target.name)}</h3></div><span class="converter-fit ${esc(row.classification)}">${esc(classLabel[row.classification]||row.classification)}</span></div>
      <p class="converter-equal-energy"><strong>${fmt(quantity(line),1)} ${esc(unit(line))} ${esc(source.name)}</strong> ≈ <strong>${fmt(row.targetQuantity??row.equivalentQuantity,1)} ${esc(row.targetUnit||row.equivalentUnit)} ${esc(target.name)}</strong> a parità di ${fmt(row.sourceNutrition?.energyKcal,0)} kcal.</p>
      <div class="converter-nutrition-table" role="table" aria-label="Confronto nutrizionale">
        <div class="head" role="row"><span>Valore</span><span>Originale</span><span>Alternativa</span><span>Δ</span></div>
        ${[['kcal','energyKcal',0],['Proteine','proteinG',1],['Carboidrati','carbohydrateG',1],['Grassi','fatG',1],['Fibre','fiberG',1]].map(([label,key,d])=>`<div role="row"><b>${label}</b><span>${fmt(row.sourceNutrition?.[key],d)}${key==='energyKcal'?'':' g'}</span><span>${fmt(row.targetNutrition?.[key],d)}${key==='energyKcal'?'':' g'}</span><span>${deltaText(row,key)}</span></div>`).join('')}
      </div>
      <div class="converter-explain"><strong>${esc((row.reasons||[]).join(' · ')||'Equivalenza energetica')}</strong>${row.warnings?.length?`<span>${esc(row.warnings.join(' · '))}</span>`:''}<small>Le kcal totali coincidono per definizione: il confronto utile è su grammi necessari, densità energetica e macro. Questo strumento non modifica la ricetta.</small></div>`;
    box.scrollIntoView({block:'nearest',behavior:'smooth'});
  }
  async function renderAlternatives(){
    const box=q('[data-converter-results]'),note=q('[data-converter-mode-note]');
    if(!line)return;
    box.innerHTML='<div class="converter-loading compact">Calcolo alternative…</div>';
    try{
      const rows=await alternatives();
      note.innerHTML=query.trim()?`<strong>Ricerca libera.</strong> Mostro anche sostituzioni che hanno solo equivalenza calorica.`:`<strong>Suggeriti greedy.</strong> Ordinati per ruolo culinario, profilo nutrizionale e quantità plausibile.`;
      box.innerHTML=rows.length?rows.map((r,i)=>`<button type="button" class="converter-result-card" data-converter-result="${i}"><div><strong>${esc(r.target.name)}</strong><span>${fmt(r.targetQuantity??r.equivalentQuantity,1)} ${esc(r.targetUnit||r.equivalentUnit)} equivalenti · ${esc(densityText(r.target))}</span></div><div><b>${fmt(r.score,0)}/100</b><span class="converter-fit ${esc(r.classification)}">${esc(classLabel[r.classification]||r.classification)}</span></div></button>`).join(''):'<div class="empty-state compact"><strong>Nessun ingrediente trovato</strong><span>Prova un nome o un alias diverso.</span></div>';
      box.querySelectorAll('[data-converter-result]').forEach(b=>b.onclick=()=>renderComparison(rows[Number(b.dataset.converterResult)]));
      renderComparison(null);
    }catch(e){box.innerHTML=`<div class="empty-state compact"><strong>Conversione non disponibile</strong><span>${esc(e.message)}</span></div>`;}
  }
  async function init(){
    try{
      await db.initialize();lib=await store.library();
      recipe=recipeMatch(lib.recipes,host.dataset.recipeId,host.dataset.recipeTitle,host.dataset.recipeSlug);
      if(!recipe)throw new Error('Ricetta non trovata nel catalogo V6.');
      versions=lib.versions.filter(v=>(v.recipeId||v.recipe_id)===recipe.id).sort((a,b)=>Number(a.versionNumber||a.revision||1)-Number(b.versionNumber||b.revision||1));
      if(!versions.length)throw new Error('Nessuna versione strutturata disponibile.');
      version=versions.find(v=>v.id===recipe.currentVersionId)||versions.at(-1);renderVersion();renderLines();
      q('[data-converter-loading]').hidden=true;q('[data-converter-app]').hidden=false;await renderAlternatives();
      q('[data-converter-version]').onchange=async e=>{const next=versions.find(v=>v.id===e.target.value);if(!next||next.id===version.id)return;version=next;line=null;selected=null;query='';q('[data-converter-search]').value='';renderVersion();renderLines();await renderAlternatives();};
      q('[data-converter-search]').oninput=async e=>{query=e.target.value;await renderAlternatives();};
    }catch(e){q('[data-converter-loading]').innerHTML=`<strong>Convertitore non disponibile.</strong> ${esc(e.message)}`;}
  }
  init();
})();
