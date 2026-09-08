(function(global){
  'use strict';
  const core=global.DietCalendarCore,state=global.DietSiteState,diaryCore=global.TataDietDiaryCore,store=global.TataDietDiaryStore,effective=global.TataDietEffectiveCore;
  if(!core||!state||!diaryCore||!store||!effective)return;
  const $=(selector,root=document)=>root.querySelector(selector);
  const esc=state.escapeHtml;
  const fmt=value=>Number(value||0).toLocaleString('it-IT',{maximumFractionDigits:1});
  const monthFmt=new Intl.DateTimeFormat('it-IT',{month:'long',year:'numeric',timeZone:'UTC'});
  const statusMeta={
    followed:{label:'Seguito',symbol:'✓',className:'green'},partial:{label:'Modificato',symbol:'~',className:'yellow'},'not-followed':{label:'Fuori piano',symbol:'×',className:'red'},unlogged:{label:'Non compilato',symbol:'○',className:'gray'}
  };
  const nutritionFields=['energyKcal','proteinG','carbohydrateG','fatG','fiberG'];
  function numInput(value){return Number(value||0)>0?String(Math.round(Number(value)*10)/10):'';}
  function monthLabel(date){const p=core.parseISO(date);return monthFmt.format(new Date(Date.UTC(p.year,p.month-1,1))).replace(/^./,c=>c.toUpperCase());}
  function clamp(value,min,max){return core.clampDate(value,min,max);}
  function valueOf(form,name){return form.elements[name]?.value??'';}
  function nutritionFromForm(form){return Object.fromEntries(nutritionFields.map(key=>[key,Number(valueOf(form,key)||0)]));}

  document.addEventListener('DOMContentLoaded',async()=>{
    if(document.body?.dataset?.page!=='diary')return;
    const loading=$('[data-diary-loading]'),errorBox=$('[data-diary-error]'),app=$('[data-diary-app]');
    const fail=message=>{loading.hidden=true;errorBox.hidden=false;errorBox.innerHTML=`<strong>Diario non disponibile</strong><span>${esc(message)}</span>`;};
    try{
      const start=state.resolveStart(location.search).value;
      if(!start){fail('Imposta prima la data di inizio del piano dal Calendario.');return;}
      let context=await store.context(start);if(!context){fail('Non trovo un piano personale attivo per questa data di inizio.');return;}
      const first=context.days[0]?.date,last=context.days.at(-1)?.date,today=core.todayISO();
      if(!first||!last){fail('Il piano personale non contiene giornate.');return;}
      if(core.compareDates(today,first)<0){fail(`Il Diario sarà disponibile dal ${core.formatLong(first)}. Non registra giornate future.`);return;}
      const maxDiary=core.minDate(today,last);
      const requested=new URLSearchParams(location.search).get('date');
      let focus=core.isValidISO(requested)?clamp(requested,first,maxDiary):clamp(today,first,maxDiary);
      let shownMonth=core.monthStart(focus);
      let records=[];let recordMap=new Map();let eventsByDate=new Map();
      const rebuildEvents=()=>{eventsByDate=new Map();effective.allEvents(context.days,context.maps).forEach(event=>{if(!eventsByDate.has(event.actualDate))eventsByDate.set(event.actualDate,[]);eventsByDate.get(event.actualDate).push(event);});};
      const reloadRecords=async()=>{records=await store.list(context.plan.id);recordMap=new Map(records.map(row=>[row.date,row]));};
      const viewForDate=date=>{const entries=diaryCore.mergePlannedEvents(eventsByDate.get(date)||[],recordMap.get(date));return {date,record:recordMap.get(date)||null,entries,stats:diaryCore.dayStats(entries),day:context.days.find(x=>x.date===date)||null};};
      rebuildEvents();await reloadRecords();

      function updateUrl(){const url=state.stateUrl('diario/index.html',start,{date:focus});history.replaceState(null,'',url.href);}
      function viewsForRange(days){return diaryCore.rangeDates(focus,days,first).filter(date=>core.compareDates(date,maxDiary)<=0).map(viewForDate);}
      function renderSummary(){const s7=diaryCore.summaryForViews(viewsForRange(7)),s30=diaryCore.summaryForViews(viewsForRange(30));
        $('[data-diary-summary-7]').textContent=s7.adherencePct==null?'—':`${s7.adherencePct}%`;$('[data-diary-summary-7-note]').textContent=`${s7.loggedMeals}/${s7.plannedMeals} pasti registrati`;
        $('[data-diary-summary-30]').textContent=s30.adherencePct==null?'—':`${s30.adherencePct}%`;$('[data-diary-summary-30-note]').textContent=`Copertura ${s30.completionPct}%`;
        $('[data-diary-summary-meals]').textContent=String(s30.loggedMeals);$('[data-diary-summary-meals-note]').textContent=`${s30.plannedMeals} pianificati · ${s30.manualMeals} extra`;
        $('[data-diary-summary-days]').textContent=String(s30.completeDays);$('[data-diary-summary-days-note]').textContent=`${s30.loggedDays} giorni iniziati su ${s30.days}`;
      }
      function renderCalendar(){
        $('[data-diary-month-title]').textContent=monthLabel(shownMonth);const dates=core.monthGridDates(shownMonth);const host=$('[data-diary-calendar]');
        host.innerHTML=dates.map(date=>{const inPlan=core.compareDates(date,first)>=0&&core.compareDates(date,maxDiary)<=0;const same=core.sameMonth(date,shownMonth);if(!inPlan)return `<span class="diary-calendar-day is-empty${same?'':' outside-month'}"></span>`;
          const view=viewForDate(date),p=core.parseISO(date),selected=date===focus,stats=view.stats,percent=stats.adherencePct==null?'':`${stats.adherencePct}%`;
          return `<button type="button" class="diary-calendar-day ${stats.signal}${selected?' is-selected':''}${same?'':' outside-month'}" data-diary-date-choice="${esc(date)}" aria-label="${esc(core.formatLong(date))}: ${esc(diaryCore.signalLabel(stats.signal))}"><span>${p.day}</span><i class="diary-dot ${stats.signal}"></i><small>${esc(percent)}</small></button>`;
        }).join('');
        $('[data-diary-month-prev]').disabled=core.compareDates(core.monthEnd(core.addMonths(shownMonth,-1)),first)<0;
        $('[data-diary-month-next]').disabled=core.compareDates(core.monthStart(core.addMonths(shownMonth,1)),maxDiary)>0;
      }
      function plannedEditor(entry){const snap=entry.plannedSnapshot||{},actual=entry.actual||{},n=actual.nutrition||{};return `<details class="diary-entry-details"${entry.actual||entry.note?' open':''}><summary>Dettagli / cosa hai mangiato</summary><form data-diary-entry-form="${esc(entry.id)}" class="diary-entry-form">
        <label class="wide">Descrizione effettiva<input name="title" value="${esc(actual.title||'')}" placeholder="Lascia vuoto se hai seguito la ricetta"></label>
        <label>Ora<input type="time" name="time" value="${esc(actual.time||snap.time||'')}"></label><label>Tipo<input name="mealType" value="${esc(actual.mealType||snap.mealType||'')}"></label>
        <label>kcal<input type="number" min="0" step="1" name="energyKcal" value="${esc(numInput(n.energyKcal))}"></label><label>Proteine g<input type="number" min="0" step="0.1" name="proteinG" value="${esc(numInput(n.proteinG))}"></label>
        <label>Carbo g<input type="number" min="0" step="0.1" name="carbohydrateG" value="${esc(numInput(n.carbohydrateG))}"></label><label>Grassi g<input type="number" min="0" step="0.1" name="fatG" value="${esc(numInput(n.fatG))}"></label><label>Fibre g<input type="number" min="0" step="0.1" name="fiberG" value="${esc(numInput(n.fiberG))}"></label>
        <label class="wide">Nota<input name="note" value="${esc(entry.note||'')}" placeholder="Facoltativa"></label><div class="wide diary-form-actions"><button class="button secondary compact" type="submit">Salva dettagli</button><button class="button ghost compact" type="button" data-diary-clear-entry="${esc(entry.id)}">Azzera registrazione</button></div></form></details>`;}
      function manualEditor(entry){const a=entry.actual||{},n=a.nutrition||{};return `<article class="diary-meal-card manual" data-diary-entry="${esc(entry.id)}"><div class="diary-meal-top"><div class="diary-meal-time"><strong>${esc(a.time||'—')}</strong><span>${esc(a.mealType||'Pasto extra')}</span></div><div class="diary-meal-copy"><p class="eyebrow">Fuori ricettario</p><h3>${esc(a.title||'Pasto manuale')}</h3><p>${Math.round(n.energyKcal||0)} kcal · P ${fmt(n.proteinG)} · C ${fmt(n.carbohydrateG)} · G ${fmt(n.fatG)} · fibre ${fmt(n.fiberG)}</p></div><span class="diary-status-chip manual">Manuale</span></div><details class="diary-entry-details"><summary>Modifica</summary><form data-diary-manual-edit="${esc(entry.id)}" class="diary-entry-form"><label>Ora<input type="time" name="time" value="${esc(a.time||'')}"></label><label>Tipo<input name="mealType" value="${esc(a.mealType||'')}"></label><label class="wide">Descrizione<input required name="title" value="${esc(a.title||'')}"></label><label>kcal<input type="number" min="0" step="1" name="energyKcal" value="${esc(numInput(n.energyKcal))}"></label><label>Proteine g<input type="number" min="0" step="0.1" name="proteinG" value="${esc(numInput(n.proteinG))}"></label><label>Carbo g<input type="number" min="0" step="0.1" name="carbohydrateG" value="${esc(numInput(n.carbohydrateG))}"></label><label>Grassi g<input type="number" min="0" step="0.1" name="fatG" value="${esc(numInput(n.fatG))}"></label><label>Fibre g<input type="number" min="0" step="0.1" name="fiberG" value="${esc(numInput(n.fiberG))}"></label><label class="wide">Nota<input name="note" value="${esc(entry.note||'')}"></label><div class="wide diary-form-actions"><button class="button secondary compact" type="submit">Salva</button><button class="button ghost compact danger" type="button" data-diary-delete-manual="${esc(entry.id)}">Elimina</button></div></form></details></article>`;}
      function renderMeals(view){const host=$('[data-diary-meals]');const planned=view.entries.filter(x=>x.entryType==='planned');const manual=view.entries.filter(x=>x.entryType==='manual');
        const plannedHtml=planned.map(entry=>{const snap=entry.plannedSnapshot||{},meta=statusMeta[diaryCore.normalizeStatus(entry.status)]||statusMeta.unlogged;return `<article class="diary-meal-card ${meta.className}${entry.orphaned?' orphaned':''}" data-diary-entry="${esc(entry.id)}"><div class="diary-meal-top"><div class="diary-meal-time"><strong>${esc(snap.time||'—')}</strong><span>${esc(snap.mealType||'Pasto')}</span></div><div class="diary-meal-copy"><p class="eyebrow">${entry.orphaned?'Storico':'Pianificato'}</p><h3>${esc(snap.title||'Pasto pianificato')}</h3><p>${Math.round(snap.nutrition?.energyKcal||0)} kcal${entry.note?` · ${esc(entry.note)}`:''}</p></div><span class="diary-status-chip ${meta.className}">${meta.symbol} ${meta.label}</span></div>
          ${entry.orphaned?'<p class="diary-orphan-note">Questo pasto non è più presente nel piano corrente, ma resta nello storico del diario.</p>':`<div class="diary-status-buttons" role="group" aria-label="Esito pasto"><button type="button" data-diary-status="followed" data-entry-id="${esc(entry.id)}" aria-pressed="${entry.status==='followed'}">✓ Seguito</button><button type="button" data-diary-status="partial" data-entry-id="${esc(entry.id)}" aria-pressed="${entry.status==='partial'}">~ Modificato</button><button type="button" data-diary-status="not-followed" data-entry-id="${esc(entry.id)}" aria-pressed="${entry.status==='not-followed'}">× Fuori piano</button></div>`}${plannedEditor(entry)}</article>`;}).join('');
        host.innerHTML=plannedHtml+(manual.length?`<div class="diary-extra-divider"><span>Pasti extra / manuali</span></div>${manual.map(manualEditor).join('')}`:'');
      }
      function renderDay(){const view=viewForDate(focus),stats=view.stats,day=view.day;$('[data-diary-date]').textContent=core.formatLong(focus);$('[data-diary-shift]').textContent=day?`${day.dayType} · ${day.shift?.name||day.dayType}`:'Giornata';
        const score=$('[data-diary-day-score]');score.innerHTML=`<span class="diary-signal ${stats.signal}"><i class="diary-dot ${stats.signal}"></i>${esc(diaryCore.signalLabel(stats.signal))}</span><span>${stats.adherencePct==null?'Aderenza —':`Aderenza ${stats.adherencePct}%`} · ${stats.loggedCount}/${stats.plannedCount} pasti registrati${stats.manualCount?` · ${stats.manualCount} extra`:''}</span>`;
        $('[data-diary-prev-day]').disabled=focus===first;$('[data-diary-next-day]').disabled=focus===maxDiary;$('[data-diary-open-plan]').href=state.stateUrl('oggi/index.html',start,{date:focus}).href;
        renderMeals(view);$('[data-diary-comment]').value=view.record?.comment||'';
      }
      function renderAll(){renderSummary();renderCalendar();renderDay();updateUrl();}
      async function afterWrite(){await reloadRecords();renderAll();}
      function feedback(text){const node=$('[data-diary-feedback]');node.textContent=text;clearTimeout(feedback.timer);feedback.timer=setTimeout(()=>{node.textContent='';},1800);}
      async function setFocus(date){focus=clamp(date,first,maxDiary);shownMonth=core.monthStart(focus);renderAll();}

      $('[data-diary-calendar]').addEventListener('click',event=>{const button=event.target.closest('[data-diary-date-choice]');if(button)setFocus(button.dataset.diaryDateChoice);});
      $('[data-diary-month-prev]').onclick=()=>{shownMonth=core.addMonths(shownMonth,-1);renderCalendar();};
      $('[data-diary-month-next]').onclick=()=>{shownMonth=core.addMonths(shownMonth,1);renderCalendar();};
      $('[data-diary-prev-day]').onclick=()=>setFocus(core.addDays(focus,-1));$('[data-diary-next-day]').onclick=()=>setFocus(core.addDays(focus,1));
      $('[data-diary-mark-all]').onclick=async()=>{await store.markAllFollowed(focus,start);await afterWrite();feedback('Giornata segnata come seguita.');};
      $('[data-diary-meals]').addEventListener('click',async event=>{const statusButton=event.target.closest('[data-diary-status]');if(statusButton){await store.updatePlanned(focus,statusButton.dataset.entryId,{status:statusButton.dataset.diaryStatus},start);await afterWrite();const card=$(`[data-diary-entry="${CSS.escape(statusButton.dataset.entryId)}"]`);if(statusButton.dataset.diaryStatus==='partial')card?.querySelector('details')?.setAttribute('open','');return;}const clear=event.target.closest('[data-diary-clear-entry]');if(clear){await store.updatePlanned(focus,clear.dataset.diaryClearEntry,{status:'unlogged',note:'',actualKind:null,actual:null},start);await afterWrite();return;}const del=event.target.closest('[data-diary-delete-manual]');if(del){await store.deleteManual(focus,del.dataset.diaryDeleteManual,start);await afterWrite();feedback('Pasto manuale eliminato.');}});
      $('[data-diary-meals]').addEventListener('submit',async event=>{event.preventDefault();const form=event.target;if(form.matches('[data-diary-entry-form]')){const actualTitle=valueOf(form,'title').trim();const hasActual=actualTitle||nutritionFields.some(k=>Number(valueOf(form,k)||0)>0);await store.updatePlanned(focus,form.dataset.diaryEntryForm,{status:viewForDate(focus).entries.find(x=>x.id===form.dataset.diaryEntryForm)?.status==='unlogged'?'partial':undefined,note:valueOf(form,'note'),actualKind:hasActual?'manual':null,actual:hasActual?{title:actualTitle||'Pasto modificato',time:valueOf(form,'time'),mealType:valueOf(form,'mealType'),nutrition:nutritionFromForm(form)}:null},start);await afterWrite();feedback('Dettagli salvati.');}else if(form.matches('[data-diary-manual-edit]')){await store.updateManual(focus,form.dataset.diaryManualEdit,{title:valueOf(form,'title'),time:valueOf(form,'time'),mealType:valueOf(form,'mealType'),nutrition:nutritionFromForm(form),note:valueOf(form,'note')},start);await afterWrite();feedback('Pasto manuale aggiornato.');}});
      $('[data-diary-manual-form]').addEventListener('submit',async event=>{event.preventDefault();const form=event.currentTarget;await store.addManual(focus,{title:valueOf(form,'title'),time:valueOf(form,'time'),mealType:valueOf(form,'mealType'),nutrition:nutritionFromForm(form),note:valueOf(form,'note')},start);form.reset();await afterWrite();feedback('Pasto aggiunto.');});
      $('[data-diary-save-comment]').onclick=async()=>{await store.saveComment(focus,$('[data-diary-comment]').value,start);await afterWrite();feedback('Commento salvato.');};

      loading.hidden=true;app.hidden=false;renderAll();
    }catch(error){console.error(error);fail(error?.message||'Errore inatteso durante il caricamento del Diario.');}
  });
})(typeof globalThis!=='undefined'?globalThis:this);
