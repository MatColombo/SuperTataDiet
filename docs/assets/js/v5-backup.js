(function (global, factory) {
  const api = factory(global.TataDietDB);
  if (typeof module === "object" && module.exports) module.exports = api;
  global.TataDietBackup = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (dbApi) {
  "use strict";
  const FORMAT = "tatadiet-backup";
  const SCHEMA_VERSION = 2;
  const APP_VERSION = "6.0.4";
  const dataKeys = ["ingredients", "ingredientRevisions", "recipes", "recipeVersions", "planInstances", "calendarDays", "operations", "shoppingChecklists", "diaryDays", "settings"];
  const START_STORAGE_KEY = "diet-plan:start-date:v2";

  function canonical(value) {
    if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
    if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
    return JSON.stringify(value);
  }

  async function sha256(text) {
    if (!globalThis.crypto?.subtle) throw new Error("SHA-256 non disponibile in questo browser");
    const bytes = new TextEncoder().encode(text);
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  async function baseInfo() {
    const id = (await dbApi.get("meta", "baseDatasetId"))?.value;
    const sourceSha256 = (await dbApi.get("meta", "baseDatasetSourceSha256"))?.value;
    if (!id || !sourceSha256) throw new Error("Dataset base non inizializzato");
    return { id, sourceSha256 };
  }

  function isPersonal(record) { return record && !String(record.id || "").startsWith("base:") && record.origin !== "base" && !record.immutable; }
  function emptyData() { return { ingredients: [], ingredientRevisions: [], recipes: [], recipeVersions: [], planInstances: [], calendarDays: [], operations: [], shoppingChecklists: [], diaryDays: [], settings: {} }; }

  async function collect(mode = "full") {
    const data = emptyData();
    if (["full", "recipes"].includes(mode)) {
      data.ingredients = (await dbApi.getAll("ingredients")).filter(isPersonal);
      data.ingredientRevisions = (await dbApi.getAll("ingredientRevisions")).filter(isPersonal);
      data.recipes = (await dbApi.getAll("recipes")).filter(isPersonal);
      data.recipeVersions = (await dbApi.getAll("recipeVersions")).filter(isPersonal);
    }
    if (["full", "calendar"].includes(mode)) {
      data.planInstances = await dbApi.getAll("planInstances");
      data.calendarDays = await dbApi.getAll("calendarDays");
      data.operations = await dbApi.getAll("operations");
      data.diaryDays = await dbApi.getAll("diaryDays");
    }
    if (mode === "full") data.shoppingChecklists = await dbApi.getAll("shoppingChecklists");
    if (["full", "settings"].includes(mode)) data.settings = await dbApi.allSettingsObject();
    return data;
  }

  function newestPlan(plans) {
    return [...(plans || [])].sort((a, b) => String(b.updatedAt || b.createdAt || "").localeCompare(String(a.updatedAt || a.createdAt || "")))[0] || null;
  }

  function resolveSavestate(backup) {
    const plans = backup?.data?.planInstances || [];
    const settings = backup?.data?.settings || {};
    const requestedId = backup?.savestate?.activePlanInstanceId || settings.activePlanInstanceId || null;
    const requested = requestedId ? plans.find((plan) => plan.id === requestedId) : null;
    const activeCandidates = plans.filter((plan) => plan.status === "active");
    const selected = requested || newestPlan(activeCandidates) || newestPlan(plans);
    return {
      activePlanInstanceId: selected?.id || null,
      planStartDate: backup?.savestate?.planStartDate || settings.planStartDate || selected?.startDate || null,
      selectedPlan: selected || null,
      requestedId,
      activeCandidates,
    };
  }

  function normalizedPlanRecords(records, activePlanInstanceId) {
    return (records || []).map((row) => {
      const copy = structuredClone(row);
      if (!activePlanInstanceId) return copy;
      if (copy.id === activePlanInstanceId) copy.status = "active";
      else if (copy.status === "active") copy.status = "archived";
      return copy;
    });
  }

  function restoredSettings(backup, savestate) {
    const settings = { ...(backup?.data?.settings || {}) };
    if (savestate.activePlanInstanceId) settings.activePlanInstanceId = savestate.activePlanInstanceId;
    if (savestate.planStartDate) settings.planStartDate = savestate.planStartDate;
    return settings;
  }

  function collectClientState(storage = globalThis.localStorage) {
    const local = {};
    try {
      if (!storage) return { localStorage: local };
      for (let index = 0; index < storage.length; index += 1) {
        const key = storage.key(index);
        if (key && key.startsWith("diet-plan")) local[key] = storage.getItem(key);
      }
    } catch { /* storage may be unavailable */ }
    return { localStorage: local };
  }

  function syncClientState(settings, savestate = {}, storage = globalThis.localStorage) {
    const start = settings?.planStartDate;
    try {
      if (!storage) return { synced: false, reason: "storage-unavailable", planStartDate: start || null, keys: 0 };
      const savedLocal = savestate?.localStorage;
      if (savedLocal && typeof savedLocal === "object") {
        const toRemove = [];
        for (let index = 0; index < storage.length; index += 1) { const key = storage.key(index); if (key && key.startsWith("diet-plan")) toRemove.push(key); }
        toRemove.forEach((key) => storage.removeItem(key));
        Object.entries(savedLocal).forEach(([key, value]) => { if (key.startsWith("diet-plan") && value !== null && value !== undefined) storage.setItem(key, String(value)); });
      }
      if (/^\d{4}-\d{2}-\d{2}$/.test(start || "")) storage.setItem(START_STORAGE_KEY, start);
      else storage.removeItem(START_STORAGE_KEY);
      return { synced: true, planStartDate: start || null, keys: savedLocal && typeof savedLocal === "object" ? Object.keys(savedLocal).length : 1 };
    } catch (error) {
      return { synced: false, reason: error?.message || "storage-error", planStartDate: start || null, keys: 0 };
    }
  }

  async function createBackup(mode = "full") {
    if (!["full", "recipes", "calendar", "settings"].includes(mode)) throw new Error("Modalità backup non valida");
    const data = await collect(mode);
    const temporary = { data };
    const state = resolveSavestate(temporary);
    if (data.planInstances?.length && state.activePlanInstanceId) data.planInstances = normalizedPlanRecords(data.planInstances, state.activePlanInstanceId);
    if (state.activePlanInstanceId) data.settings.activePlanInstanceId = state.activePlanInstanceId;
    if (state.planStartDate) data.settings.planStartDate = state.planStartDate;
    const envelope = {
      recordType: "backup", format: FORMAT, schemaVersion: SCHEMA_VERSION, appVersion: APP_VERSION,
      exportedAt: new Date().toISOString(), baseDataset: await baseInfo(), mode, data,
      savestate: { activePlanInstanceId: state.activePlanInstanceId, planStartDate: state.planStartDate, ...collectClientState() },
      integrity: { algorithm: "sha256", digest: "" },
    };
    envelope.integrity.digest = await sha256(canonical({ ...envelope, integrity: { algorithm: "sha256", digest: "" } }));
    return envelope;
  }

  function validateShape(backup) {
    const errors = [];
    if (!backup || typeof backup !== "object") return ["Il file non contiene un oggetto JSON."];
    if (backup.recordType !== "backup" || backup.format !== FORMAT) errors.push("Formato TataDiet non riconosciuto.");
    if (backup.schemaVersion !== SCHEMA_VERSION) errors.push(`Schema ${backup.schemaVersion ?? "?"} non supportato.`);
    if (!["full", "recipes", "calendar", "settings"].includes(backup.mode)) errors.push("Modalità backup non valida.");
    if (!backup.baseDataset?.id || !/^[a-f0-9]{64}$/.test(backup.baseDataset?.sourceSha256 || "")) errors.push("Riferimento al dataset base non valido.");
    if (!backup.data || typeof backup.data !== "object") errors.push("Sezione dati mancante.");
    else dataKeys.forEach((key) => {
      if (key === "settings") { if (typeof backup.data[key] !== "object" || Array.isArray(backup.data[key])) errors.push("Impostazioni non valide."); }
      else if (!Array.isArray(backup.data[key])) errors.push(`${key} deve essere un array.`);
    });
    if (backup.integrity?.algorithm !== "sha256" || !/^[a-f0-9]{64}$/.test(backup.integrity?.digest || "")) errors.push("Checksum SHA-256 mancante o non valido.");
    return errors;
  }

  async function verifyIntegrity(backup) {
    const actual = await sha256(canonical({ ...backup, integrity: { algorithm: "sha256", digest: "" } }));
    return { valid: actual === backup.integrity.digest, actual, expected: backup.integrity.digest };
  }

  async function preview(backup) {
    const errors = validateShape(backup);
    if (errors.length) return { valid: false, errors, warnings: [], conflicts: [], counts: {} };
    const integrity = await verifyIntegrity(backup);
    if (!integrity.valid) errors.push("Checksum non valido: il file è stato modificato o corrotto.");
    const currentBase = await baseInfo();
    if (backup.baseDataset.id !== currentBase.id || backup.baseDataset.sourceSha256 !== currentBase.sourceSha256) errors.push("Il backup usa un dataset base incompatibile con questa installazione.");
    const warnings = [];
    if (backup.appVersion && backup.appVersion !== APP_VERSION) warnings.push(`Backup creato con TataDiet ${backup.appVersion}; lo schema ${SCHEMA_VERSION} è compatibile con TataDiet ${APP_VERSION}.`);
    const savestate = resolveSavestate(backup);
    const planIds = new Set((backup.data.planInstances || []).map((plan) => plan.id));
    const dayIds = new Map((backup.data.calendarDays || []).map((day) => [day.id, day]));
    if (savestate.requestedId && !planIds.has(savestate.requestedId)) errors.push("Il piano attivo indicato dal backup non è presente nei dati del calendario.");
    for (const day of backup.data.calendarDays || []) if (!planIds.has(day.planInstanceId)) errors.push(`Giornata ${day.id} collegata a un piano inesistente.`);
    for (const plan of backup.data.planInstances || []) {
      const missing = (plan.dayIds || []).filter((id) => !dayIds.has(id) || dayIds.get(id)?.planInstanceId !== plan.id);
      if (missing.length) errors.push(`Piano ${plan.id}: ${missing.length} giornate referenziate mancanti o incoerenti.`);
    }
    if (savestate.activeCandidates.length > 1) warnings.push(`Il backup contiene ${savestate.activeCandidates.length} piani marcati attivi. Verrà ripristinato come unico piano attivo ${savestate.activePlanInstanceId || "quello più recente"}.`);
    if (backup.data.planInstances?.length && !savestate.activePlanInstanceId) errors.push("Impossibile determinare il piano attivo del savestate.");
    const conflicts = [];
    for (const store of ["ingredients", "ingredientRevisions", "recipes", "recipeVersions", "planInstances", "calendarDays", "operations", "diaryDays"]) {
      for (const row of backup.data[store] || []) {
        const current = await dbApi.get(store, row.id);
        if (current && canonical(current) !== canonical(row)) conflicts.push({ store, id: row.id, kind: "different-content" });
      }
    }
    const counts = Object.fromEntries(dataKeys.map((key) => [key, key === "settings" ? Object.keys(backup.data.settings || {}).length : (backup.data[key] || []).length]));
    if (conflicts.length) warnings.push("Sono presenti record con lo stesso ID ma contenuto diverso.");
    return { valid: !errors.length, errors, warnings, conflicts, counts, integrity, mode: backup.mode, exportedAt: backup.exportedAt, savestate: { activePlanInstanceId: savestate.activePlanInstanceId, planStartDate: savestate.planStartDate } };
  }

  async function snapshotCurrent() {
    return createBackup("full");
  }

  function remapConflictId(id) {
    const suffix = globalThis.crypto?.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    return `${id}:import:${suffix}`;
  }

  function deepRemap(value, idMap) {
    if (Array.isArray(value)) return value.map((item) => deepRemap(item, idMap));
    if (value && typeof value === "object") {
      const out = {};
      Object.entries(value).forEach(([key, item]) => { out[key] = deepRemap(item, idMap); });
      return out;
    }
    return typeof value === "string" && idMap.has(value) ? idMap.get(value) : value;
  }

  async function prepareImportRecords(backup, mode) {
    const allowed = mode === "recipes" ? ["ingredients", "ingredientRevisions", "recipes", "recipeVersions"]
      : mode === "calendar" ? ["planInstances", "calendarDays", "operations", "diaryDays"]
      : mode === "settings" ? []
      : ["ingredients", "ingredientRevisions", "recipes", "recipeVersions", "planInstances", "calendarDays", "operations", "shoppingChecklists", "diaryDays"];
    const idMap = new Map();
    if (mode === "merge") {
      for (const store of allowed) {
        for (const row of backup.data[store] || []) {
          const current = await dbApi.get(store, row.id);
          if (current && canonical(current) !== canonical(row)) {
            if (current.origin === "base" || current.immutable) throw new Error(`Conflitto con record base immutabile: ${row.id}`);
            idMap.set(row.id, remapConflictId(row.id));
          }
        }
      }
    }
    return {
      allowed,
      idMap,
      records: Object.fromEntries(allowed.map((store) => [store, (backup.data[store] || []).map((row) => deepRemap(row, idMap))])),
    };
  }

  async function importBackup(backup, mode = "replace") {
    const report = await preview(backup);
    if (!report.valid) throw new Error(report.errors.join(" "));
    if (!["replace", "merge", "recipes", "calendar", "settings"].includes(mode)) throw new Error("Modalità di import non valida");
    const safetyBackup = await snapshotCurrent();
    const prepared = await prepareImportRecords(backup, mode);
    const savestate = resolveSavestate(backup);
    const settingsToRestore = restoredSettings(backup, savestate);
    if (["replace", "calendar", "merge"].includes(mode) && prepared.records.planInstances) prepared.records.planInstances = normalizedPlanRecords(prepared.records.planInstances, savestate.activePlanInstanceId);
    const allStores = ["meta", "settings", "ingredients", "ingredientRevisions", "recipes", "recipeVersions", "planInstances", "calendarDays", "operations", "shoppingChecklists", "diaryDays"];
    const currentPersonal = {};
    for (const store of ["ingredients", "ingredientRevisions", "recipes", "recipeVersions"]) currentPersonal[store] = (await dbApi.getAll(store)).filter(isPersonal);

    const db = await dbApi.openDatabase();
    try {
      const tx = db.transaction(allStores, "readwrite");
      const now = new Date().toISOString();
      tx.objectStore("meta").put({ key: "preImportRollback", value: safetyBackup, updatedAt: now });
      tx.objectStore("meta").put({ key: "preImportRollbackCreatedAt", value: now });

      if (mode === "replace") {
        ["ingredients", "ingredientRevisions", "recipes", "recipeVersions"].forEach((store) => currentPersonal[store].forEach((row) => tx.objectStore(store).delete(row.id)));
        ["planInstances", "calendarDays", "operations", "shoppingChecklists", "diaryDays"].forEach((store) => tx.objectStore(store).clear());
      } else if (mode === "recipes") {
        ["ingredients", "ingredientRevisions", "recipes", "recipeVersions"].forEach((store) => currentPersonal[store].forEach((row) => tx.objectStore(store).delete(row.id)));
      } else if (mode === "calendar") {
        ["planInstances", "calendarDays", "operations", "diaryDays"].forEach((store) => tx.objectStore(store).clear());
      }

      for (const store of prepared.allowed) prepared.records[store].forEach((row) => tx.objectStore(store).put(row));
      if (["replace", "merge", "settings"].includes(mode)) {
        if (mode === "replace" || mode === "settings") tx.objectStore("settings").clear();
        Object.entries(settingsToRestore).forEach(([key, value]) => tx.objectStore("settings").put({ key, value, source: "import", updatedAt: now }));
      }
      tx.objectStore("meta").put({ key: "lastImportAt", value: now });
      tx.objectStore("meta").put({ key: "lastImportMode", value: mode });
      await new Promise((resolve, reject) => { tx.oncomplete = resolve; tx.onerror = () => reject(tx.error); tx.onabort = () => reject(tx.error); });
    } finally { db.close(); }
    const clientState = syncClientState(settingsToRestore, backup.savestate || {});
    return {
      imported: Object.fromEntries(prepared.allowed.map((store) => [store, prepared.records[store].length])),
      remappedIds: prepared.idMap.size,
      safetyBackup,
      report,
      activePlanInstanceId: savestate.activePlanInstanceId,
      planStartDate: savestate.planStartDate,
      clientState,
    };
  }

  async function rollbackLastImport() {
    const row = await dbApi.get("meta", "preImportRollback");
    if (!row?.value) throw new Error("Nessun backup preventivo disponibile per il rollback.");
    const result = await importBackup(row.value, "replace");
    await dbApi.put("meta", { key: "lastRollbackAt", value: new Date().toISOString() });
    return result;
  }

  async function parseFile(file) {
    if (!file) throw new Error("Seleziona un file JSON.");
    const text = await file.text();
    try { return JSON.parse(text); } catch { throw new Error("Il file non contiene JSON valido."); }
  }

  function filename(mode) {
    return `tatadiet-backup-${mode}-${new Date().toISOString().slice(0, 10)}.json`;
  }

  return { FORMAT, SCHEMA_VERSION, APP_VERSION, START_STORAGE_KEY, canonical, sha256, createBackup, validateShape, verifyIntegrity, preview, importBackup, rollbackLastImport, parseFile, filename, collect, baseInfo, resolveSavestate, collectClientState, syncClientState };
});
