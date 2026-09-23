(() => {
  "use strict";
  if (document.body.dataset.page !== "tools") return;
  const core = window.DietCalendarCore;
  const ops = window.DietOperationsCore;
  const state = window.DietSiteState;
  if (!core || !ops || !state) return;
  const show = state.show;
  const startState = state.resolveStart();
  const setStatus = (message, tone = "ok") => {
    const host = document.querySelector("[data-tools-status]");
    if (!host) return;
    host.className = `tool-status ${tone}`;
    host.textContent = message;
    show(host, true);
  };
  const initCalendarTools = async () => {
    const setup = document.querySelector("[data-plan-setup]");
    const app = document.querySelector("[data-ics-app]");
    if (!startState.value) { show(setup, true); show(app, false); return; }
    show(setup, false); show(app, true);
    const calendar = await state.fetchJson("data/calendar.json");
    const start = startState.value;
    const effectiveContext = await globalThis.TataDietEffectiveStore?.context?.(start).catch(() => null);
    const range = effectiveContext ? { start: effectiveContext.days[0].date, end: effectiveContext.days.at(-1).date } : core.planRange(start, calendar.duration_days || 180);
    document.querySelectorAll("[data-active-range]").forEach((element) => { element.textContent = `${core.formatMedium(range.start)} – ${core.formatMedium(range.end)}`; });
    const from = document.querySelector("[data-ics-from]");
    const to = document.querySelector("[data-ics-to]");
    [from, to].forEach((input) => { input.min = range.start; input.max = range.end; });
    from.value = range.start; to.value = range.end;
    document.querySelector("[data-ics-scope]")?.addEventListener("change", (event) => { document.querySelector("[data-ics-custom]").hidden = event.target.value !== "custom"; });
    document.querySelector("[data-export-ics]")?.addEventListener("click", async () => {
      const scope = document.querySelector("[data-ics-scope]")?.value || "all";
      const first = scope === "custom" ? from.value : range.start;
      const last = scope === "custom" ? to.value : range.end;
      if (!core.isValidISO(first) || !core.isValidISO(last)) { setStatus("Seleziona un intervallo valido.", "error"); return; }
      const includePrep = Boolean(document.querySelector("[data-ics-prep]")?.checked);
      const content = effectiveContext && globalThis.TataDietEffectiveCore
        ? globalThis.TataDietEffectiveCore.buildIcs(effectiveContext.plan, effectiveContext.days, effectiveContext.maps, first, last, includePrep)
        : ops.buildIcs(calendar.days, start, first, last, includePrep);
      state.downloadBlob(content, `piano-turni-${first}-${last}.ics`, "text/calendar;charset=utf-8");
      setStatus(`Calendario ${effectiveContext ? "effettivo " : ""}esportato dal ${core.formatMedium(first)} al ${core.formatMedium(last)}${includePrep ? " con promemoria meal-prep" : ""}.`);
    });
  };
  const init = async () => {
    show(document.querySelector("[data-plan-loading]"), false);
    try { await initCalendarTools(); }
    catch (error) { setStatus(`Impossibile preparare l'esportazione ICS: ${error.message}`, "error"); }
  };
  init();
})();
