const data = window.PILATES_DATA || { muscleGroups: [], exercises: [], tagCounts: {} };

const state = {
  muscle: "all",
  tag: "",
  query: "",
  source: "all",
  selectedId: "",
  detailOpen: false,
  lightbox: null,
};

let lastLightboxTrigger = null;
let lightboxTouchStart = null;

const els = {
  exerciseCount: document.getElementById("exerciseCount"),
  activeFilter: document.getElementById("activeFilter"),
  muscleFilters: document.getElementById("muscleFilters"),
  tagFilters: document.getElementById("tagFilters"),
  mobileTagFilters: document.getElementById("mobileTagFilters"),
  activeTags: document.getElementById("activeTags"),
  exerciseList: document.getElementById("exerciseList"),
  exerciseDetail: document.getElementById("exerciseDetail"),
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
    const row = button("", `exercise-row ${state.selectedId === exercise.id ? "is-active" : ""}`, () => {
      state.selectedId = exercise.id;
      state.detailOpen = true;
      closeLightbox();
      render();
    }, { pressed: state.selectedId === exercise.id, title: exercise.title });
    const tags = exercise.tags.slice(0, 4).map((tag) => `<span class="mini-tag">${escapeHtml(tag)}</span>`).join("");
    row.innerHTML = `
      <img class="thumb" src="${escapeAttr(exercise.images[0] || "")}" alt="${escapeAttr(exercise.title)}">
      <span class="row-main">
        <span class="row-title">
          <span>${escapeHtml(exercise.title)}</span>
          <span class="page-label">${escapeHtml(exercise.pageLabel)}</span>
        </span>
        <span class="row-subtitle">${escapeHtml(exercise.english || exercise.equipment)}</span>
        <span class="row-tags">${tags}</span>
      </span>
    `;
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
}

function render() {
  const exercises = filteredExercises();
  document.body.classList.toggle("detail-open", state.detailOpen);
  renderMuscles();
  renderTags();
  renderActiveTags();
  renderList(exercises);
  renderDetail();
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
