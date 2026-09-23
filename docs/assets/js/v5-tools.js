(() => {
  "use strict";
  if (document.body.dataset.page !== "tools") return;
  const db = window.TataDietDB;
  const backup = window.TataDietBackup;
  const state = window.DietSiteState;
  if (!db || !backup || !state) return;

  const $ = (selector) => document.querySelector(selector);
  const status = (message, tone = "ok") => {
    const host = $("[data-v5-status]");
    if (!host) return;
    host.className = `tool-status ${tone}`;
    host.textContent = message;
    host.hidden = false;
  };
  const LABELS = {
    ingredients:"ingredienti personali", ingredientRevisions:"revisioni ingredienti", recipes:"ricette personali", recipeVersions:"versioni ricetta",
    planInstances:"piani", calendarDays:"giornate", operations:"operazioni", shoppingChecklists:"spunte spesa", diaryDays:"giorni Diario", settings:"impostazioni"
  };
  const formatCounts = (counts) => Object.entries(counts).filter(([, value]) => value).map(([key, value]) => `${value} ${LABELS[key] || key}`).join(" · ") || "nessun dato personale";

  async function initialize() {
    const result = await db.initialize({ fetchJson: (path) => state.fetchJson(path) });
    const [ingredients, recipes] = await Promise.all([db.getAll("ingredients"), db.getAll("recipes")]);
    const personalIngredients = ingredients.filter(x => x.origin !== "base" && !String(x.id || "").startsWith("base:")).length;
    const personalRecipes = recipes.filter(x => x.origin !== "base" && !String(x.id || "").startsWith("base:")).length;
    const counts = result.counts;
    $("[data-v5-db-state]").textContent = "Pronto";
    $("[data-v5-base-count]").textContent = `${counts.ingredients || 0} ingredienti · ${counts.recipes || 0} ricette`;
    $("[data-v5-personal-count]").textContent = `${personalIngredients} ingredienti · ${personalRecipes} ricette`;
    const start = await db.getSetting("planStartDate");
    $("[data-v5-start]").textContent = start || "non impostata";
    return result;
  }

  async function exportBackup() {
    status("Preparazione del backup completo…", "neutral");
    const envelope = await backup.createBackup("full");
    state.downloadBlob(JSON.stringify(envelope, null, 2), backup.filename("full"), "application/json;charset=utf-8");
    status("Backup completo creato. Conserva questo file per ripristinare i dati personali.");
  }

  function renderPreview(report, payload) {
    const host = $("[data-import-preview]");
    if (!host) return;
    host.hidden = false;
    const counts = Object.entries(report.counts || {}).filter(([, n]) => n).map(([key, n]) => `<li><strong>${n}</strong> ${state.escapeHtml(LABELS[key] || key)}</li>`).join("");
    const warnings = (report.warnings || []).map(w => `<p>${state.escapeHtml(w)}</p>`).join("");
    const errors = (report.errors || []).map(e => `<p>${state.escapeHtml(e)}</p>`).join("");
    host.innerHTML = `
      <div class="import-preview-head"><div><p class="eyebrow">Backup selezionato</p><h3>${report.valid ? "File verificato" : "File non importabile"}</h3></div><span class="status-pill ${report.valid ? "success" : "danger"}">${report.valid ? "Integrità OK" : "Errore"}</span></div>
      <p>TataDiet ${state.escapeHtml(payload.appVersion || "?")} · esportato ${state.escapeHtml(payload.exportedAt || "data sconosciuta")}</p>
      ${counts ? `<ul class="compact-count-list">${counts}</ul>` : "<p>Il file non contiene dati personali.</p>"}
      ${warnings ? `<div class="import-warning">${warnings}</div>` : ""}
      ${errors ? `<div class="import-errors">${errors}</div>` : ""}
    `;
    $("[data-import-actions]").hidden = !report.valid;
  }

  let pendingBackup = null;
  async function chooseBackup(file) {
    pendingBackup = null;
    $("[data-import-preview]").hidden = true;
    $("[data-import-actions]").hidden = true;
    if (!file) return;
    status("Verifica del backup in corso…", "neutral");
    const payload = await backup.parseFile(file);
    if (payload?.recordType !== "backup" || payload?.format !== backup.FORMAT) throw new Error("Questo file non è un backup TataDiet.");
    if (payload.mode !== "full") throw new Error("Seleziona un Backup completo TataDiet. I vecchi JSON di preferenze e i backup parziali non sono più importabili da questa schermata.");
    const report = await backup.preview(payload);
    renderPreview(report, payload);
    if (!report.valid) { status("Backup non importabile: controlla i dettagli nell'anteprima.", "error"); return; }
    pendingBackup = payload;
    status("Backup verificato. Puoi ripristinarlo quando vuoi.");
  }

  async function restoreBackup() {
    if (!pendingBackup) throw new Error("Seleziona prima un backup completo TataDiet.");
    const ok = window.confirm("Ripristinare questo backup? I dati personali attuali (calendario, Diario, ricette/ingredienti personali, impostazioni e spunte) verranno sostituiti. Il catalogo base V6 resta intatto. Prima del ripristino viene creato un checkpoint automatico.");
    if (!ok) return;
    status("Ripristino del backup in corso…", "neutral");
    const result = await backup.importBackup(pendingBackup, "replace");
    await initialize();
    $("[data-rollback-import]").hidden = false;
    $("[data-import-actions]").hidden = true;
    pendingBackup = null;
    status(`Backup ripristinato. ${formatCounts(result.imported)}. Le altre pagine useranno subito i dati ripristinati.`);
  }

  async function rollback() {
    if (!window.confirm("Annullare l'ultimo ripristino e tornare al checkpoint creato immediatamente prima?")) return;
    status("Ripristino del checkpoint precedente…", "neutral");
    await backup.rollbackLastImport();
    await initialize();
    status("Ultimo ripristino annullato. I dati precedenti sono stati recuperati.");
  }

  async function init() {
    try { await initialize(); }
    catch (error) { status(`Archivio locale non disponibile: ${error.message}`, "error"); return; }
    $("[data-v5-export='full']")?.addEventListener("click", () => exportBackup().catch((error) => status(error.message, "error")));
    $("[data-v5-import-file]")?.addEventListener("change", async (event) => {
      try { await chooseBackup(event.target.files?.[0]); }
      catch (error) { pendingBackup = null; $("[data-import-actions]").hidden = true; status(error.message, "error"); }
      event.target.value = "";
    });
    $("[data-v5-restore-backup]")?.addEventListener("click", () => restoreBackup().catch((error) => status(`Ripristino non riuscito: ${error.message}`, "error")));
    $("[data-rollback-import]")?.addEventListener("click", () => rollback().catch((error) => status(`Rollback non riuscito: ${error.message}`, "error")));
  }
  init();
})();
