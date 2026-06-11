const data = window.PILATES_DATA || { muscleGroups: [], exercises: [], tagCounts: {} };

const state = {
  mode: "index",
  plannerTab: "edit",
  muscle: "all",
  tag: "",
  query: "",
  source: "all",
  selectedId: "",
  detailOpen: false,
  lightbox: null,
  plan: null,
  draggedItemId: "",
  plannerStatus: "",
};

let lastLightboxTrigger = null;
let lightboxTouchStart = null;
let saveTimer = null;
let pointerDrag = null;

const PLAN_STORAGE_KEY = "pilatesWiki.activeClassPlan.v1";
const PLAN_SCHEMA_VERSION = 1;
const SHARE_HASH_PREFIX = "#plan=";
const SHARE_HASH_LIMIT = 1800;

const els = {
  exerciseCount: document.getElementById("exerciseCount"),
  activeFilter: document.getElementById("activeFilter"),
  plannerCount: document.getElementById("plannerCount"),
  indexModeButton: document.getElementById("indexModeButton"),
  plannerModeButton: document.getElementById("plannerModeButton"),
  muscleFilters: document.getElementById("muscleFilters"),
  tagFilters: document.getElementById("tagFilters"),
  mobileTagFilters: document.getElementById("mobileTagFilters"),
  activeTags: document.getElementById("activeTags"),
  exerciseList: document.getElementById("exerciseList"),
  exerciseDetail: document.getElementById("exerciseDetail"),
  plannerView: document.getElementById("plannerView"),
  planImportInput: document.getElementById("planImportInput"),
  searchInput: document.getElementById("searchInput"),
  sourceFilter: document.getElementById("sourceFilter"),
  imageLightbox: document.getElementById("imageLightbox"),
  lightboxImage: document.getElementById("lightboxImage"),
  lightboxCaption: document.getElementById("lightboxCaption"),
  lightboxClose: document.getElementById("lightboxClose"),
  lightboxPrev: document.getElementById("lightboxPrev"),
  lightboxNext: document.getElementById("lightboxNext"),
};

const byId = new Map(data.exercises.map((exercise) => [exercise.id, exercise]));

state.plan = loadInitialPlan();

function uid(prefix) {
  if (window.crypto?.randomUUID) return `${prefix}-${window.crypto.randomUUID()}`;
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function createDefaultPlan() {
  return {
    id: uid("class"),
    title: "60 分鐘器械流動課",
    durationTarget: 60,
    items: [],
    updatedAt: new Date().toISOString(),
    schemaVersion: PLAN_SCHEMA_VERSION,
  };
}

function normalizePlan(raw) {
  const base = raw && typeof raw === "object" ? raw : {};
  const warnings = [];
  const items = Array.isArray(base.items) ? base.items.map((item) => {
    const exerciseId = String(item.exerciseId || "");
    const exercise = byId.get(exerciseId);
    if (exerciseId && !exercise) {
      warnings.push("部分動作在目前動作庫中找不到。");
    }
    return {
      id: String(item.id || uid("item")),
      exerciseId,
      exerciseTitleSnapshot: String(item.exerciseTitleSnapshot || exercise?.title || "動作庫中找不到"),
      minutes: sanitizeMinutes(item.minutes),
      note: String(item.note || ""),
      cues: String(item.cues || ""),
      apparatusSetup: String(item.apparatusSetup || ""),
      alternatives: String(item.alternatives || ""),
    };
  }) : [];
  return {
    plan: {
      id: String(base.id || uid("class")),
      title: String(base.title || "60 分鐘器械流動課"),
      durationTarget: sanitizeMinutes(base.durationTarget, 60),
      items,
      updatedAt: String(base.updatedAt || new Date().toISOString()),
      schemaVersion: PLAN_SCHEMA_VERSION,
    },
    warnings: [...new Set(warnings)],
  };
}

function loadInitialPlan() {
  const shared = readSharedPlan();
  if (shared) return shared;
  try {
    const saved = localStorage.getItem(PLAN_STORAGE_KEY);
    if (saved) return normalizePlan(JSON.parse(saved)).plan;
  } catch (error) {
    state.plannerStatus = "讀取本機課表失敗，已建立新課表。";
  }
  return createDefaultPlan();
}

function readSharedPlan() {
  if (!location.hash.startsWith(SHARE_HASH_PREFIX)) return null;
  try {
    const hasLocalPlan = Boolean(localStorage.getItem(PLAN_STORAGE_KEY));
    if (hasLocalPlan && !window.confirm("偵測到分享課表，要用它取代目前本機課表嗎？")) {
      state.plannerStatus = "已保留本機課表。";
      return null;
    }
    const encoded = location.hash.slice(SHARE_HASH_PREFIX.length);
    const json = decodeURIComponent(escape(atob(encoded)));
    const { plan, warnings } = normalizePlan(JSON.parse(json));
    state.plannerStatus = warnings.length
      ? `已從分享連結載入，${warnings.join(" ")}`
      : "已從分享連結載入課表。";
    return plan;
  } catch (error) {
    state.plannerStatus = "分享連結無法讀取，已保留本機課表。";
    return null;
  }
}

function sanitizeMinutes(value, fallback = "") {
  if (value === "" || value === null || value === undefined) return fallback;
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? number : fallback;
}

function planTotalMinutes() {
  return state.plan.items.reduce((total, item) => total + (Number(item.minutes) || 0), 0);
}

function setPlannerStatus(message) {
  state.plannerStatus = message;
}

function schedulePlanSave(message = "已自動儲存。") {
  state.plan.updatedAt = new Date().toISOString();
  window.clearTimeout(saveTimer);
  saveTimer = window.setTimeout(() => {
    try {
      localStorage.setItem(PLAN_STORAGE_KEY, JSON.stringify(state.plan));
      setPlannerStatus(message);
      render();
    } catch (error) {
      setPlannerStatus("本機儲存失敗，請先匯出 JSON 備份。");
      render();
    }
  }, 160);
}

function muscleCount(key) {
  if (key === "all") return data.exercises.length;
  return data.exercises.filter((exercise) => exercise.muscleKeys.includes(key)).length;
}

function shortMuscleLabel(key, label) {
  const labels = {
    all: "全部",
    core: "核心",
    spine: "脊椎",
    scapula: "肩胛",
    lat: "背闊",
    arms: "手臂",
    hips_legs: "髖腿",
    mobility: "伸展",
  };
  return labels[key] || label.slice(0, 2);
}

function filteredExercises() {
  const query = state.query.trim().toLowerCase();
  return data.exercises.filter((exercise) => {
    const matchesMuscle = state.muscle === "all" || exercise.muscleKeys.includes(state.muscle);
    const matchesTag = !state.tag || exercise.tags.includes(state.tag);
    const matchesSource = state.source === "all" || exercise.source === state.source;
    const haystack = [
      exercise.title,
      exercise.english,
      exercise.equipment,
      exercise.summary,
      exercise.pageLabel,
      exercise.tags.join(" "),
      exercise.muscles.join(" "),
    ].join(" ").toLowerCase();
    return matchesMuscle && matchesTag && matchesSource && (!query || haystack.includes(query));
  });
}

function button(label, className, onClick, options = {}) {
  const el = document.createElement("button");
  el.type = "button";
  el.className = className;
  el.textContent = label;
  if (options.pressed !== undefined) {
    el.setAttribute("aria-pressed", String(options.pressed));
  }
  if (options.title) {
    el.title = options.title;
  }
  el.addEventListener("click", onClick);
  return el;
}

function renderMuscles() {
  els.muscleFilters.innerHTML = "";
  const groups = [{ key: "all", label: "全部肌群" }, ...data.muscleGroups];
  groups.forEach((group) => {
    const el = button("", `muscle-button ${state.muscle === group.key ? "is-active" : ""}`, () => {
      state.muscle = group.key;
      state.detailOpen = false;
      closeLightbox();
      render();
    }, { pressed: state.muscle === group.key });
    el.innerHTML = `
      <span class="muscle-label" data-short="${escapeAttr(shortMuscleLabel(group.key, group.label))}">${escapeHtml(group.label)}</span>
      <span class="count">${muscleCount(group.key)}</span>
    `;
    els.muscleFilters.appendChild(el);
  });
}

function renderTags() {
  const containers = [els.tagFilters, els.mobileTagFilters].filter(Boolean);
  containers.forEach((container) => {
    container.innerHTML = "";
  });
  Object.entries(data.tagCounts)
    .slice(0, 28)
    .forEach(([tag, count]) => {
      containers.forEach((container) => {
        const el = button(`${tag} ${count}`, `tag-button ${state.tag === tag ? "is-active" : ""}`, () => {
          state.tag = state.tag === tag ? "" : tag;
          state.detailOpen = false;
          closeLightbox();
          render();
        }, { pressed: state.tag === tag });
        container.appendChild(el);
      });
    });
}

function renderActiveTags() {
  els.activeTags.innerHTML = "";
  if (!state.tag) return;
  const clear = button(`Tag: ${state.tag} ×`, "clear-button", () => {
    state.tag = "";
    state.detailOpen = false;
    closeLightbox();
    render();
  });
  els.activeTags.appendChild(clear);
}

function renderList(exercises) {
  els.exerciseList.innerHTML = "";
  if (!exercises.length) {
    els.exerciseList.innerHTML = `<div class="empty-state">沒有符合條件的動作</div>`;
    return;
  }

  if (!state.selectedId || !exercises.some((exercise) => exercise.id === state.selectedId)) {
    state.selectedId = exercises[0].id;
  }

  exercises.forEach((exercise) => {
    const row = document.createElement("article");
    row.className = `exercise-row ${state.selectedId === exercise.id ? "is-active" : ""}`;
    const tags = exercise.tags.slice(0, 4).map((tag) => `<span class="mini-tag">${escapeHtml(tag)}</span>`).join("");
    row.innerHTML = `
      <button class="row-select" type="button" aria-pressed="${state.selectedId === exercise.id}" title="${escapeAttr(exercise.title)}">
        <img class="thumb" src="${escapeAttr(exercise.images[0] || "")}" alt="${escapeAttr(exercise.title)}">
        <span class="row-main">
          <span class="row-title">
            <span>${escapeHtml(exercise.title)}</span>
            <span class="page-label">${escapeHtml(exercise.pageLabel)}</span>
          </span>
          <span class="row-subtitle">${escapeHtml(exercise.english || exercise.equipment)}</span>
          <span class="row-tags">${tags}</span>
        </span>
      </button>
      <button class="row-add" type="button" aria-label="加入 ${escapeAttr(exercise.title)} 到課表">加入</button>
    `;
    row.querySelector(".row-select").addEventListener("click", () => {
      state.selectedId = exercise.id;
      state.detailOpen = true;
      closeLightbox();
      render();
    });
    row.querySelector(".row-add").addEventListener("click", () => {
      addExerciseToPlan(exercise.id);
      state.mode = "planner";
      state.plannerTab = "edit";
      state.detailOpen = false;
      closeLightbox();
      render();
    });
    els.exerciseList.appendChild(row);
  });
}

function renderDetail() {
  const exercise = byId.get(state.selectedId);
  if (!exercise) {
    els.exerciseDetail.innerHTML = `<div class="empty-state">請選擇動作</div>`;
    return;
  }

  const tags = exercise.tags.map((tag) => {
    const active = state.tag === tag ? " is-active" : "";
    return `<button type="button" class="tag-button${active}" data-tag="${escapeAttr(tag)}">${escapeHtml(tag)}</button>`;
  }).join("");

  const images = exercise.images.map((src, index) => `
    <figure class="figure">
      <button class="figure-button" type="button" data-lightbox-index="${index}">
        <img src="${escapeAttr(src)}" alt="${escapeAttr(`${exercise.title} 動作圖 ${index + 1}`)}" loading="lazy">
      </button>
      <figcaption>${escapeHtml(exercise.pageLabel)} · 圖 ${index + 1}</figcaption>
    </figure>
  `).join("");

  els.exerciseDetail.innerHTML = `
    <div class="detail-head">
      <button type="button" class="detail-close" aria-label="關閉詳情">×</button>
      <div class="detail-kicker">
        <span class="meta-chip">${escapeHtml(exercise.sourceLabel)}</span>
        <span class="meta-chip">${escapeHtml(exercise.difficulty)}</span>
        <span class="meta-chip">${escapeHtml(exercise.equipment)}</span>
        <span class="meta-chip">${escapeHtml(exercise.pageLabel)}</span>
      </div>
      <h2>${escapeHtml(exercise.title)}</h2>
      ${exercise.english ? `<p class="english-title">${escapeHtml(exercise.english)}</p>` : ""}
      <p class="summary">${escapeHtml(exercise.summary || "")}</p>
      <div class="detail-tags">${tags}</div>
      <button class="detail-add" type="button">加入課表</button>
    </div>

    <div class="detail-grid">
      <section class="info-block">
        <h3>器材設置</h3>
        <p>${escapeHtml(exercise.setup)}</p>
      </section>
      <section class="info-block">
        <h3>起始姿勢</h3>
        <p>${escapeHtml(exercise.startPosition)}</p>
      </section>
      <section class="info-block">
        <h3>動作流程</h3>
        <p>${escapeHtml(exercise.flow)}</p>
      </section>
    </div>

    <div class="image-grid">${images}</div>
  `;

  els.exerciseDetail.querySelectorAll("[data-tag]").forEach((tagButton) => {
    tagButton.addEventListener("click", () => {
      const tag = tagButton.getAttribute("data-tag") || "";
      state.tag = state.tag === tag ? "" : tag;
      state.detailOpen = false;
      closeLightbox();
      render();
    });
  });

  els.exerciseDetail.querySelectorAll("[data-lightbox-index]").forEach((imageButton) => {
    imageButton.addEventListener("click", () => {
      const index = Number(imageButton.getAttribute("data-lightbox-index"));
      const src = exercise.images[index];
      if (!src) return;
      openLightbox(exercise, index, imageButton);
    });
  });

  els.exerciseDetail.querySelector(".detail-close")?.addEventListener("click", () => {
    state.detailOpen = false;
    closeLightbox();
    render();
  });

  els.exerciseDetail.querySelector(".detail-add")?.addEventListener("click", () => {
    addExerciseToPlan(exercise.id);
    state.mode = "planner";
    state.plannerTab = "edit";
    state.detailOpen = false;
    closeLightbox();
    render();
  });
}

function addExerciseToPlan(exerciseId) {
  const exercise = byId.get(exerciseId);
  if (!exercise) return;
  state.plan.items.push({
    id: uid("item"),
    exerciseId,
    exerciseTitleSnapshot: exercise.title,
    minutes: "",
    note: "",
    cues: "",
    apparatusSetup: exercise.setup || "",
    alternatives: "",
  });
  setPlannerStatus(`已加入「${exercise.title}」。`);
  schedulePlanSave(`已加入「${exercise.title}」。`);
}

function renderPlanner() {
  const plan = state.plan;
  const total = planTotalMinutes();
  const target = Number(plan.durationTarget) || 0;
  const delta = target ? total - target : 0;
  const deltaText = target
    ? delta === 0 ? "剛好符合目標" : `${Math.abs(delta)} 分鐘${delta > 0 ? "超過" : "未滿"}`
    : "未設定目標";
  const tabs = `
    <div class="planner-tabs" role="tablist" aria-label="排課表分頁">
      <button class="planner-tab ${state.plannerTab === "edit" ? "is-active" : ""}" type="button" data-planner-action="tab" data-tab="edit">課表</button>
      <button class="planner-tab ${state.plannerTab === "preview" ? "is-active" : ""}" type="button" data-planner-action="tab" data-tab="preview">預覽</button>
    </div>
  `;
  els.plannerView.innerHTML = `
    <div class="planner-head">
      <div>
        <p class="eyebrow">Class Planner</p>
        <h2>排課表</h2>
        <p class="planner-subtitle">本機自動儲存，可列印、匯出 JSON，短課表可產生分享連結。</p>
      </div>
      <div class="planner-actions">
        <button type="button" class="planner-action" data-planner-action="print">列印</button>
        <button type="button" class="planner-action" data-planner-action="export">匯出 JSON</button>
        <button type="button" class="planner-action" data-planner-action="import">匯入 JSON</button>
        <button type="button" class="planner-action is-primary" data-planner-action="share">分享連結</button>
      </div>
    </div>

    ${tabs}

    <div class="planner-summary">
      <label>
        <span>課表名稱</span>
        <input value="${escapeAttr(plan.title)}" data-plan-field="title">
      </label>
      <label>
        <span>目標分鐘</span>
        <input type="number" min="0" step="1" value="${escapeAttr(plan.durationTarget)}" data-plan-field="durationTarget">
      </label>
      <div class="duration-card">
        <span>目前總長</span>
        <strong>${total} 分鐘</strong>
        <em>${escapeHtml(deltaText)}</em>
      </div>
    </div>

    ${state.plannerStatus ? `<div class="planner-status">${escapeHtml(state.plannerStatus)}</div>` : ""}

    ${state.plannerTab === "preview" ? renderPlanPreview() : renderPlanEditor()}
  `;
}

function renderPlanEditor() {
  return `
    <div class="planner-editor" aria-label="課表動作排序">
      <div class="planner-list">
        ${state.plan.items.length
          ? state.plan.items.map((item, index) => renderPlanItem(item, index)).join("")
          : `<div class="empty-state">課表還沒有任何動作，請從動作索引加入。</div>`}
      </div>
    </div>
  `;
}

function renderPlanItem(item, index) {
  const exercise = byId.get(item.exerciseId);
  const title = exercise?.title || item.exerciseTitleSnapshot || "動作庫中找不到";
  const subtitle = exercise ? `${exercise.english || exercise.equipment} · ${exercise.pageLabel}` : "動作庫中找不到";
  const image = exercise?.images?.[0] || "";
  const missing = exercise ? "" : `<span class="planner-warning">動作庫中找不到</span>`;
  return `
    <article class="planner-item ${state.draggedItemId === item.id ? "is-dragging" : ""}" data-item-id="${escapeAttr(item.id)}" draggable="true">
      <div class="planner-drag-row">
        <span class="drag-handle" aria-hidden="true">⋮⋮</span>
        <span class="planner-order">${index + 1}</span>
      </div>
      <div class="planner-item-main">
        ${image ? `<img class="planner-thumb" src="${escapeAttr(image)}" alt="${escapeAttr(title)}">` : `<div class="planner-thumb planner-thumb-empty"></div>`}
        <div class="planner-item-copy">
          <strong>${escapeHtml(title)}</strong>
          <span>${escapeHtml(subtitle)}</span>
          ${missing}
        </div>
      </div>
      <div class="planner-item-fields">
        <label>
          <span>分鐘</span>
          <input type="number" min="0" step="1" value="${escapeAttr(item.minutes)}" data-item-field="minutes">
        </label>
        <label class="planner-note-field">
          <span>備註</span>
          <input value="${escapeAttr(item.note)}" data-item-field="note" placeholder="教學重點、節奏或限制">
        </label>
      </div>
      <details class="advanced-fields">
        <summary>進階欄位</summary>
        <label>
          <span>教學提示</span>
          <textarea data-item-field="cues">${escapeHtml(item.cues)}</textarea>
        </label>
        <label>
          <span>器材設定</span>
          <textarea data-item-field="apparatusSetup">${escapeHtml(item.apparatusSetup)}</textarea>
        </label>
        <label>
          <span>替代動作</span>
          <textarea data-item-field="alternatives">${escapeHtml(item.alternatives)}</textarea>
        </label>
      </details>
      <div class="planner-item-actions">
        <button type="button" data-planner-action="remove" data-item-id="${escapeAttr(item.id)}">移除</button>
      </div>
    </article>
  `;
}

function renderPlanPreview() {
  return `
    <div class="plan-preview">
      <div class="print-title">
        <h2>${escapeHtml(state.plan.title)}</h2>
        <p>目標 ${Number(state.plan.durationTarget) || 0} 分鐘 · 目前 ${planTotalMinutes()} 分鐘</p>
      </div>
      ${state.plan.items.length ? `
        <section class="print-section">
          <h3>課表順序 · ${state.plan.items.length} 個動作</h3>
          ${state.plan.items.map((item, index) => renderPreviewItem(item, index)).join("")}
        </section>
      ` : `<div class="empty-state">課表還沒有任何動作</div>`}
    </div>
  `;
}

function renderPreviewItem(item, index) {
  const exercise = byId.get(item.exerciseId);
  const title = exercise?.title || item.exerciseTitleSnapshot || "動作庫中找不到";
  const image = exercise?.images?.[0] || "";
  return `
    <article class="preview-item">
      ${image ? `<img src="${escapeAttr(image)}" alt="${escapeAttr(title)}">` : ""}
      <div>
        <strong>${index + 1}. ${escapeHtml(title)} ${item.minutes ? `· ${escapeHtml(item.minutes)} 分鐘` : ""}</strong>
        ${item.note ? `<p>${escapeHtml(item.note)}</p>` : ""}
        ${item.apparatusSetup ? `<p><b>器材設定：</b>${escapeHtml(item.apparatusSetup)}</p>` : ""}
        ${item.cues ? `<p><b>教學提示：</b>${escapeHtml(item.cues)}</p>` : ""}
        ${item.alternatives ? `<p><b>替代動作：</b>${escapeHtml(item.alternatives)}</p>` : ""}
      </div>
    </article>
  `;
}

function updatePlanField(field, value) {
  if (field === "durationTarget") {
    state.plan.durationTarget = sanitizeMinutes(value, "");
  } else {
    state.plan[field] = value;
  }
  schedulePlanSave();
  render();
}

function updatePlanItem(itemId, field, value) {
  const item = state.plan.items.find((candidate) => candidate.id === itemId);
  if (!item) return;
  item[field] = field === "minutes" ? sanitizeMinutes(value, "") : value;
  schedulePlanSave();
  render();
}

function reorderPlanItem(draggedId, targetId) {
  if (!draggedId || !targetId || draggedId === targetId) return;
  const fromIndex = state.plan.items.findIndex((item) => item.id === draggedId);
  const toIndex = state.plan.items.findIndex((item) => item.id === targetId);
  if (fromIndex < 0 || toIndex < 0) return;
  const [item] = state.plan.items.splice(fromIndex, 1);
  state.plan.items.splice(toIndex, 0, item);
  state.draggedItemId = "";
  schedulePlanSave();
  render();
}

function clearPlannerDropTargets() {
  els.plannerView.querySelectorAll(".is-drop-target").forEach((item) => {
    item.classList.remove("is-drop-target");
  });
}

function endPointerDrag(targetId = "") {
  const draggedId = pointerDrag?.itemId || "";
  pointerDrag = null;
  state.draggedItemId = "";
  clearPlannerDropTargets();
  if (targetId) {
    reorderPlanItem(draggedId, targetId);
    return;
  }
  render();
}

function removePlanItem(itemId) {
  state.plan.items = state.plan.items.filter((item) => item.id !== itemId);
  schedulePlanSave("已移除動作。");
  render();
}

function exportPlan() {
  const blob = new Blob([JSON.stringify(state.plan, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const filename = `${state.plan.title || "pilates-class-plan"}.json`.replace(/[\\/:*?"<>|]+/g, "-");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  setPlannerStatus("已匯出 JSON。");
  render();
}

function importPlanFile(file) {
  if (!file) return;
  const reader = new FileReader();
  reader.addEventListener("load", () => {
    try {
      const parsed = JSON.parse(String(reader.result || ""));
      if (!parsed || typeof parsed !== "object" || !Array.isArray(parsed.items)) {
        throw new Error("invalid plan shape");
      }
      const { plan, warnings } = normalizePlan(parsed);
      state.plan = plan;
      setPlannerStatus(warnings.length ? `已匯入，${warnings.join(" ")}` : "已匯入課表。");
      schedulePlanSave(state.plannerStatus);
      render();
    } catch (error) {
      setPlannerStatus("檔案格式不正確。");
      render();
    } finally {
      els.planImportInput.value = "";
    }
  });
  reader.readAsText(file);
}

function sharePlan() {
  const encoded = btoa(unescape(encodeURIComponent(JSON.stringify(state.plan))));
  const hash = `${SHARE_HASH_PREFIX}${encoded}`;
  if (hash.length > SHARE_HASH_LIMIT) {
    setPlannerStatus("課表太長，請改用 JSON 匯出。");
    render();
    return;
  }
  const url = `${location.origin}${location.pathname}${hash}`;
  navigator.clipboard?.writeText(url).then(() => {
    setPlannerStatus("分享連結已複製。");
    location.hash = hash;
    render();
  }).catch(() => {
    setPlannerStatus("分享連結已產生，請從網址列複製。");
    location.hash = hash;
    render();
  });
}

function handlePlannerAction(action, target) {
  if (action === "tab") {
    state.plannerTab = target.dataset.tab || "edit";
    render();
    return;
  }
  if (action === "remove") {
    removePlanItem(target.dataset.itemId);
    return;
  }
  if (action === "print") {
    state.plannerTab = "preview";
    render();
    window.setTimeout(() => window.print(), 80);
    return;
  }
  if (action === "export") {
    exportPlan();
    return;
  }
  if (action === "import") {
    els.planImportInput.click();
    return;
  }
  if (action === "share") {
    sharePlan();
  }
}

function openLightbox(exercise, index, trigger) {
  state.lightbox = {
    title: exercise.title,
    pageLabel: exercise.pageLabel,
    images: exercise.images.slice(),
    index,
  };
  lastLightboxTrigger = trigger || null;
  renderLightbox();
}

function closeLightbox() {
  if (!state.lightbox) return;
  state.lightbox = null;
  lightboxTouchStart = null;
  renderLightbox();
  if (lastLightboxTrigger?.isConnected) {
    lastLightboxTrigger.focus();
  }
  lastLightboxTrigger = null;
}

function renderLightbox() {
  if (!state.lightbox) {
    els.imageLightbox.hidden = true;
    els.lightboxImage.removeAttribute("src");
    els.lightboxImage.alt = "";
    els.lightboxCaption.textContent = "";
    els.lightboxPrev.disabled = true;
    els.lightboxNext.disabled = true;
    els.lightboxPrev.hidden = true;
    els.lightboxNext.hidden = true;
    document.body.classList.remove("lightbox-open");
    return;
  }

  const shouldFocusClose = els.imageLightbox.hidden;
  const { title, pageLabel, images, index } = state.lightbox;
  const total = images.length;
  const src = images[index];
  els.lightboxImage.src = src;
  els.lightboxImage.alt = `${title} 動作圖 ${index + 1}`;
  els.lightboxCaption.textContent = `${title} · ${pageLabel} · 圖 ${index + 1} / ${total}`;
  els.lightboxPrev.disabled = index <= 0;
  els.lightboxNext.disabled = index >= total - 1;
  els.lightboxPrev.hidden = total <= 1;
  els.lightboxNext.hidden = total <= 1;
  els.imageLightbox.hidden = false;
  document.body.classList.add("lightbox-open");
  if (shouldFocusClose) {
    els.lightboxClose.focus();
  }
}

function showLightboxImage(delta) {
  if (!state.lightbox) return;
  const nextIndex = state.lightbox.index + delta;
  if (nextIndex < 0 || nextIndex >= state.lightbox.images.length) return;
  state.lightbox.index = nextIndex;
  renderLightbox();
}

function renderStats(exercises) {
  els.exerciseCount.textContent = `${exercises.length} / ${data.exercises.length} 動作`;
  const muscleLabel = state.muscle === "all"
    ? "全部肌群"
    : data.muscleGroups.find((group) => group.key === state.muscle)?.label || "全部肌群";
  els.activeFilter.textContent = state.tag ? `${muscleLabel} · ${state.tag}` : muscleLabel;
  els.plannerCount.textContent = `課表 ${planTotalMinutes()} 分`;
  els.indexModeButton.classList.toggle("is-active", state.mode === "index");
  els.plannerModeButton.classList.toggle("is-active", state.mode === "planner");
  els.indexModeButton.setAttribute("aria-pressed", String(state.mode === "index"));
  els.plannerModeButton.setAttribute("aria-pressed", String(state.mode === "planner"));
}

function render() {
  const exercises = filteredExercises();
  document.body.classList.toggle("planner-open", state.mode === "planner");
  document.body.classList.toggle("detail-open", state.mode === "index" && state.detailOpen);
  renderMuscles();
  renderTags();
  renderActiveTags();
  renderList(exercises);
  renderDetail();
  renderPlanner();
  renderLightbox();
  renderStats(exercises);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value);
}

els.searchInput.addEventListener("input", (event) => {
  state.query = event.target.value;
  state.detailOpen = false;
  closeLightbox();
  render();
});

els.sourceFilter.addEventListener("change", (event) => {
  state.source = event.target.value;
  state.detailOpen = false;
  closeLightbox();
  render();
});

els.indexModeButton.addEventListener("click", () => {
  state.mode = "index";
  state.detailOpen = false;
  closeLightbox();
  render();
});

els.plannerModeButton.addEventListener("click", () => {
  state.mode = "planner";
  state.plannerTab = "edit";
  state.detailOpen = false;
  closeLightbox();
  render();
});

els.plannerView.addEventListener("click", (event) => {
  const actionTarget = event.target.closest("[data-planner-action]");
  if (!actionTarget) return;
  handlePlannerAction(actionTarget.dataset.plannerAction, actionTarget);
});

els.plannerView.addEventListener("dragstart", (event) => {
  const item = event.target.closest(".planner-item");
  if (!item) return;
  state.draggedItemId = item.dataset.itemId || "";
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", state.draggedItemId);
  item.classList.add("is-dragging");
});

els.plannerView.addEventListener("dragover", (event) => {
  const item = event.target.closest(".planner-item");
  if (!item || !state.draggedItemId || item.dataset.itemId === state.draggedItemId) return;
  event.preventDefault();
  event.dataTransfer.dropEffect = "move";
  item.classList.add("is-drop-target");
});

els.plannerView.addEventListener("dragleave", (event) => {
  event.target.closest(".planner-item")?.classList.remove("is-drop-target");
});

els.plannerView.addEventListener("drop", (event) => {
  const item = event.target.closest(".planner-item");
  if (!item) return;
  event.preventDefault();
  reorderPlanItem(state.draggedItemId || event.dataTransfer.getData("text/plain"), item.dataset.itemId);
});

els.plannerView.addEventListener("dragend", () => {
  state.draggedItemId = "";
  els.plannerView.querySelectorAll(".is-dragging, .is-drop-target").forEach((item) => {
    item.classList.remove("is-dragging", "is-drop-target");
  });
});

els.plannerView.addEventListener("pointerdown", (event) => {
  const handle = event.target.closest(".drag-handle");
  if (!handle) return;
  const item = handle.closest(".planner-item");
  if (!item) return;
  pointerDrag = {
    itemId: item.dataset.itemId || "",
    pointerId: event.pointerId,
    targetId: "",
  };
  state.draggedItemId = pointerDrag.itemId;
  item.classList.add("is-dragging");
  handle.setPointerCapture?.(event.pointerId);
});

els.plannerView.addEventListener("pointermove", (event) => {
  if (!pointerDrag) return;
  event.preventDefault();
  const element = document.elementFromPoint(event.clientX, event.clientY);
  const item = element?.closest?.(".planner-item");
  clearPlannerDropTargets();
  if (!item || item.dataset.itemId === pointerDrag.itemId) {
    pointerDrag.targetId = "";
    return;
  }
  pointerDrag.targetId = item.dataset.itemId || "";
  item.classList.add("is-drop-target");
});

els.plannerView.addEventListener("pointerup", (event) => {
  if (!pointerDrag) return;
  const targetId = pointerDrag.targetId;
  event.target.releasePointerCapture?.(event.pointerId);
  endPointerDrag(targetId);
});

els.plannerView.addEventListener("pointercancel", () => {
  if (!pointerDrag) return;
  endPointerDrag();
});

els.plannerView.addEventListener("change", (event) => {
  const target = event.target;
  if (target.matches("[data-plan-field]")) {
    updatePlanField(target.dataset.planField, target.value);
    return;
  }
  if (target.matches("[data-item-field]")) {
    const item = target.closest("[data-item-id]");
    if (!item) return;
    updatePlanItem(item.dataset.itemId, target.dataset.itemField, target.value);
  }
});

els.planImportInput.addEventListener("change", (event) => {
  importPlanFile(event.target.files?.[0]);
});

document.addEventListener("keydown", (event) => {
  if (state.lightbox) {
    if (event.key === "Escape") {
      closeLightbox();
      return;
    }
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      showLightboxImage(-1);
      return;
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      showLightboxImage(1);
      return;
    }
  }
  if (event.key !== "Escape" || !state.detailOpen) return;
  state.detailOpen = false;
  render();
});

els.lightboxClose.addEventListener("click", closeLightbox);
els.lightboxPrev.addEventListener("click", () => showLightboxImage(-1));
els.lightboxNext.addEventListener("click", () => showLightboxImage(1));

els.imageLightbox.addEventListener("click", (event) => {
  if (event.target === els.imageLightbox) {
    closeLightbox();
  }
});

els.imageLightbox.addEventListener("touchstart", (event) => {
  if (!state.lightbox || state.lightbox.images.length <= 1) return;
  const touch = event.changedTouches[0];
  lightboxTouchStart = {
    x: touch.clientX,
    y: touch.clientY,
  };
}, { passive: true });

els.imageLightbox.addEventListener("touchend", (event) => {
  if (!state.lightbox || !lightboxTouchStart) return;
  const touch = event.changedTouches[0];
  const deltaX = touch.clientX - lightboxTouchStart.x;
  const deltaY = touch.clientY - lightboxTouchStart.y;
  lightboxTouchStart = null;
  if (Math.abs(deltaX) < 48 || Math.abs(deltaX) < Math.abs(deltaY) * 1.25) return;
  showLightboxImage(deltaX < 0 ? 1 : -1);
}, { passive: true });

render();
