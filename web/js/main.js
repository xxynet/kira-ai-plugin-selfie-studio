/**
 * Selfie Studio — page logic.
 *
 * Vanilla ES modules: bridge context → data load → render three views
 * (wardrobe / scenes / studio) plus the catalog preview, with dialog and
 * toast plumbing. All icons are lucide, refreshed after DOM updates.
 */

import { api } from './api.js';
import { applyStatic, onLocaleChange, setLocale, t } from './i18n.js';

const WARDROBE_CATS = ['top', 'bottom', 'dress', 'shoes', 'accessory', 'other'];
const SCENE_CATS = ['indoor', 'outdoor', 'urban', 'nature', 'vehicle', 'other'];

const state = {
  items: [],
  loaded: false,
  filters: { wardrobe: 'all', scene: 'all' },
  search: { wardrobe: '', scene: '' },
  uploadKind: 'wardrobe',
  queue: [],
  uploading: false,
  editItem: null,
  confirmResolve: null,
  studio: {
    outfits: new Set(),
    scene: null,
    busy: false,
    result: null,
  },
  catalogLoaded: false,
};

const $ = (selector) => document.querySelector(selector);

const KIND_CATS = { wardrobe: WARDROBE_CATS, scene: SCENE_CATS };
const KIND_KEY = { wardrobe: 'wardrobe', scene: 'scenes' };

function esc(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#39;');
}

function refreshIcons() {
  if (window.lucide) window.lucide.createIcons();
}

function catLabel(item) {
  return t(`cat.${item.category || 'other'}`);
}

function itemsOf(kind) {
  return state.items.filter((item) => item.kind === kind);
}

/* ── Toasts ──────────────────────────────────────────────────────────── */

function toast(kind, key, vars) {
  const icons = { success: 'circle-check', error: 'circle-x', info: 'info' };
  const node = document.createElement('div');
  node.className = `toast is-${kind}`;
  node.innerHTML = `<i data-lucide="${icons[kind] || 'info'}"></i><span></span>`;
  node.querySelector('span').textContent = t(key, vars);
  $('#toasts').appendChild(node);
  refreshIcons();
  setTimeout(() => {
    node.classList.add('is-leaving');
    setTimeout(() => node.remove(), 240);
  }, 3400);
}

/* ── Dialog plumbing ─────────────────────────────────────────────────── */

function openDialog(id) {
  $(id).hidden = false;
  refreshIcons();
}

function closeDialog(id) {
  $(id).hidden = true;
}

function confirmDialog(title, text) {
  $('#confirm-title').textContent = title;
  $('#confirm-text').textContent = text;
  openDialog('#dialog-confirm');
  return new Promise((resolve) => { state.confirmResolve = resolve; });
}

/* ── Data ────────────────────────────────────────────────────────────── */

async function loadItems() {
  const data = await api.items();
  state.items = data.items || [];
  state.loaded = true;
}

/* ── Rendering: filters & grids ──────────────────────────────────────── */

function renderCounts() {
  $('#count-wardrobe').textContent = itemsOf('wardrobe').length || '';
  $('#count-scenes').textContent = itemsOf('scene').length || '';
}

function renderFilters(kind) {
  const wrap = $(`#${KIND_KEY[kind]}-filters`);
  const items = itemsOf(kind);
  const current = state.filters[kind];
  const chips = [['all', items.length]];
  for (const cat of KIND_CATS[kind]) {
    chips.push([cat, items.filter((item) => (item.category || 'other') === cat).length]);
  }
  wrap.innerHTML = chips.map(([cat, count]) => `
    <button type="button" class="chip${cat === current ? ' is-active' : ''}" data-cat="${cat}">
      <span>${esc(t(`cat.${cat}`))}</span><em>${count}</em>
    </button>`).join('');
}

function visibleItems(kind) {
  const query = state.search[kind].trim().toLowerCase();
  return itemsOf(kind).filter((item) => {
    if (state.filters[kind] !== 'all' && (item.category || 'other') !== state.filters[kind]) {
      return false;
    }
    if (!query) return true;
    return `${item.name} ${item.note || ''}`.toLowerCase().includes(query);
  });
}

function cardHTML(item, kind, index) {
  const off = item.enabled ? '' : ' is-off';
  const toggleTitle = item.enabled ? t('actions.pause') : t('actions.resume');
  return `
  <article class="item-card${off}" data-id="${item.id}" style="animation-delay:${Math.min(index * 30, 240)}ms">
    <figure class="item-figure" data-act="edit" title="${t('actions.edit')}">
      <img src="${api.imageURL(item)}" alt="${esc(item.name)}" loading="lazy" draggable="false">
      <span class="item-cat">${esc(catLabel(item))}</span>
      ${item.enabled ? '' : `<span class="off-badge"><i data-lucide="eye-off"></i>${t('actions.off')}</span>`}
      <div class="item-rail">
        <button type="button" class="rail-btn" data-act="edit" title="${t('actions.edit')}"><i data-lucide="pencil"></i></button>
        <button type="button" class="rail-btn" data-act="toggle" title="${toggleTitle}"><i data-lucide="${item.enabled ? 'pause' : 'play'}"></i></button>
        <button type="button" class="rail-btn is-danger" data-act="delete" title="${t('actions.delete')}"><i data-lucide="trash-2"></i></button>
      </div>
    </figure>
    <div class="item-meta">
      <span class="item-name">${esc(item.name)}</span>
      <span class="item-note">${esc(item.note || '')}</span>
    </div>
  </article>`;
}

function emptyHTML(kind) {
  const query = state.search[kind].trim();
  const filtered = state.filters[kind] !== 'all' || query;
  if (filtered && itemsOf(kind).length) {
    return `<div class="empty"><p class="empty-title">${t('empty.filter')}</p></div>`;
  }
  return `
  <div class="empty">
    <span class="empty-orb"><i data-lucide="${kind === 'wardrobe' ? 'shirt' : 'images'}"></i></span>
    <p class="empty-title">${t(`empty.${KIND_KEY[kind]}.title`)}</p>
    <p class="empty-sub">${t(`empty.${KIND_KEY[kind]}.sub`)}</p>
    <button type="button" class="primary-btn" data-empty-upload>
      <i data-lucide="plus"></i><span>${t(`empty.${KIND_KEY[kind]}.cta`)}</span>
    </button>
  </div>`;
}

function renderGrid(kind) {
  renderFilters(kind);
  const grid = $(`#${KIND_KEY[kind]}-grid`);
  const items = visibleItems(kind);
  grid.innerHTML = items.length
    ? items.map((item, index) => cardHTML(item, kind, index)).join('')
    : emptyHTML(kind);
  refreshIcons();
}

/* ── Rendering: studio picks ─────────────────────────────────────────── */

function pickHTML(item, picked) {
  return `
  <button type="button" class="pick-tile${picked ? ' is-picked' : ''}" data-id="${item.id}"
          title="${esc(item.name)}">
    <img src="${api.imageURL(item)}" alt="${esc(item.name)}" loading="lazy" draggable="false">
    <span class="pick-check"><i data-lucide="check"></i></span>
  </button>`;
}

function renderStudioPicks() {
  const outfits = $('#studio-outfits');
  const scenes = $('#studio-scenes');
  const enabledOutfits = itemsOf('wardrobe').filter((item) => item.enabled);
  const enabledScenes = itemsOf('scene').filter((item) => item.enabled);

  outfits.innerHTML = enabledOutfits.length
    ? enabledOutfits.map((item) => pickHTML(item, state.studio.outfits.has(item.id))).join('')
    : `<p class="pick-empty">${t('studio.emptyWardrobe')}</p>`;
  scenes.innerHTML = enabledScenes.length
    ? enabledScenes.map((item) => pickHTML(item, state.studio.scene === item.id)).join('')
    : `<p class="pick-empty">${t('studio.emptyScenes')}</p>`;
  refreshIcons();
}

/* ── Rendering: catalog ──────────────────────────────────────────────── */

async function renderCatalog(force = false) {
  if (state.catalogLoaded && !force) return;
  try {
    const data = await api.catalog();
    state.catalogLoaded = true;
    const pill = $('#catalog-state');
    pill.className = `state-pill ${data.enabled ? 'is-on' : 'is-off'}`;
    pill.innerHTML = `<i data-lucide="${data.enabled ? 'circle-check' : 'eye-off'}"></i><span></span>`;
    pill.querySelector('span').textContent = data.enabled ? t('catalog.on') : t('catalog.off');
    $('#catalog-text').textContent = data.text || '';
  } catch (e) {
    $('#catalog-text').textContent = e.message;
  }
  refreshIcons();
}

/* ── Global re-render ────────────────────────────────────────────────── */

function renderAll() {
  renderCounts();
  renderGrid('wardrobe');
  renderGrid('scene');
  renderStudioPicks();
  if (state.catalogLoaded) renderCatalog(true);
}

function reload() {
  return loadItems()
    .then(renderAll)
    .catch((e) => toast('error', 'toast.loadFailed', { reason: e.message }));
}

/* ── View switching ──────────────────────────────────────────────────── */

function switchView(view) {
  document.querySelectorAll('.nav-item').forEach((node) => {
    node.classList.toggle('is-active', node.dataset.view === view);
  });
  document.querySelectorAll('.view').forEach((node) => {
    node.classList.toggle('is-active', node.dataset.view === view);
  });
  if (view === 'catalog') renderCatalog();
}

/* ── Upload flow ─────────────────────────────────────────────────────── */

function openUpload(kind, files) {
  state.uploadKind = kind;
  state.queue = [];
  $('#upload-title').textContent = t(kind === 'wardrobe' ? 'upload.wardrobe' : 'upload.scenes');
  $('#upload-input').value = '';
  if (files && files.length) addFiles(files);
  renderQueue();
  openDialog('#dialog-upload');
  if (!files || !files.length) $('#upload-dropzone').focus();
}

function addFiles(fileList) {
  const cats = KIND_CATS[state.uploadKind];
  for (const file of fileList) {
    const okType = ['image/png', 'image/jpeg', 'image/webp'].includes(file.type);
    const okSize = file.size > 0 && file.size <= 10 * 1024 * 1024;
    state.queue.push({
      file,
      url: URL.createObjectURL(file),
      name: file.name.replace(/\.[a-z0-9]+$/i, '').slice(0, 40) || 'Untitled',
      note: '',
      category: cats[0],
      error: !okType ? t('upload.formats') : (!okSize ? '10 MB' : ''),
    });
  }
  renderQueue();
}

function renderQueue() {
  const wrap = $('#upload-queue');
  if (!state.queue.length) {
    wrap.innerHTML = `<p class="queue-empty">${t('upload.queueEmpty')}</p>`;
  } else {
    const cats = KIND_CATS[state.uploadKind];
    wrap.innerHTML = state.queue.map((row, index) => `
      <div class="queue-row${row.error ? ' is-error' : ''}" data-index="${index}">
        <img class="queue-thumb" src="${row.url}" alt="">
        <div class="queue-fields">
          <input type="text" maxlength="40" data-field="name" value="${esc(row.name)}"
                 placeholder="${t('upload.namePh')}" autocomplete="off">
          <input type="text" class="note" maxlength="200" data-field="note" value="${esc(row.note)}"
                 placeholder="${t('upload.notePh')}" autocomplete="off">
        </div>
        <select data-field="category">
          ${cats.map((cat) => `<option value="${cat}"${cat === row.category ? ' selected' : ''}>${esc(t(`cat.${cat}`))}</option>`).join('')}
        </select>
        <button type="button" class="queue-remove" data-remove title="${t('actions.delete')}">
          <i data-lucide="x"></i>
        </button>
        ${row.error ? `<span class="queue-error">${esc(row.error)}</span>` : ''}
      </div>`).join('');
  }
  const ready = state.queue.some((row) => !row.error);
  $('#upload-start').disabled = state.uploading || !ready;
  refreshIcons();
}

async function startUpload() {
  if (state.uploading) return;
  const kind = state.uploadKind;
  const rows = state.queue.filter((row) => !row.error);
  if (!rows.length) return;

  state.uploading = true;
  const button = $('#upload-start');
  button.disabled = true;
  button.innerHTML = `<i data-lucide="loader-circle" class="is-spinning"></i><span>${t('upload.working')}</span>`;
  refreshIcons();

  let okCount = 0;
  const failures = [];
  for (let index = 0; index < state.queue.length; index += 1) {
    const row = state.queue[index];
    if (row.error) continue;
    const rowNode = wrapQueueRow(index);
    if (rowNode) rowNode.classList.add('is-uploading');
    try {
      const data = await api.upload(row.file, {
        kind, name: row.name, category: row.category, note: row.note,
      });
      okCount += 1;
      if (rowNode) {
        rowNode.classList.remove('is-uploading');
        rowNode.classList.add('is-done');
      }
      toast('success', 'toast.uploaded', { name: data.item.name });
    } catch (e) {
      row.error = e.message;
      failures.push(row.name);
      renderQueue();
    }
  }

  state.uploading = false;
  button.innerHTML = `<i data-lucide="upload"></i><span>${t('upload.start')}</span>`;

  if (okCount) {
    state.queue = state.queue.filter((row) => row.error);
    if (!state.queue.length) closeDialog('#dialog-upload');
    else renderQueue();
    await reload();
  }
  if (failures.length) toast('error', 'toast.someFailed');
}

function wrapQueueRow(index) {
  return $('#upload-queue').querySelector(`.queue-row[data-index="${index}"]`);
}

/* ── Edit flow ───────────────────────────────────────────────────────── */

function openEdit(item) {
  state.editItem = item;
  $('#edit-title').textContent = t(item.kind === 'wardrobe' ? 'edit.wardrobe' : 'edit.scenes');
  $('#edit-image').src = api.imageURL(item);
  $('#edit-name').value = item.name;
  const select = $('#edit-category');
  select.innerHTML = KIND_CATS[item.kind]
    .map((cat) => `<option value="${cat}"${cat === (item.category || 'other') ? ' selected' : ''}>${esc(t(`cat.${cat}`))}</option>`)
    .join('');
  $('#edit-note').value = item.note || '';
  $('#edit-enabled').checked = Boolean(item.enabled);
  openDialog('#dialog-edit');
}

async function saveEdit() {
  const item = state.editItem;
  if (!item) return;
  try {
    await api.update({
      id: item.id,
      name: $('#edit-name').value,
      category: $('#edit-category').value,
      note: $('#edit-note').value,
      enabled: $('#edit-enabled').checked,
    });
    closeDialog('#dialog-edit');
    toast('success', 'toast.saved');
    await reload();
  } catch (e) {
    toast('error', 'toast.loadFailed', { reason: e.message });
  }
}

async function deleteFromEdit() {
  const item = state.editItem;
  if (!item) return;
  const yes = await confirmDialog(
    t('confirm.deleteTitle'),
    t('confirm.deleteText', { name: item.name }),
  );
  if (!yes) return;
  try {
    await api.remove(item.id);
    closeDialog('#dialog-confirm');
    closeDialog('#dialog-edit');
    toast('success', 'toast.deleted', { name: item.name });
    await reload();
  } catch (e) {
    closeDialog('#dialog-confirm');
    toast('error', 'toast.loadFailed', { reason: e.message });
  }
}

/* ── Card actions ────────────────────────────────────────────────────── */

async function toggleItem(item) {
  try {
    await api.update({ id: item.id, enabled: !item.enabled });
    await reload();
  } catch (e) {
    toast('error', 'toast.loadFailed', { reason: e.message });
  }
}

async function deleteItem(item) {
  const yes = await confirmDialog(
    t('confirm.deleteTitle'),
    t('confirm.deleteText', { name: item.name }),
  );
  if (!yes) return;
  try {
    await api.remove(item.id);
    closeDialog('#dialog-confirm');
    toast('success', 'toast.deleted', { name: item.name });
    await reload();
  } catch (e) {
    closeDialog('#dialog-confirm');
    toast('error', 'toast.loadFailed', { reason: e.message });
  }
}

/* ── Studio (test shot) ──────────────────────────────────────────────── */

function renderStudioResult() {
  const wrap = $('#studio-result');
  const { result, busy } = state.studio;
  if (busy) {
    wrap.innerHTML = `
      <div class="result-loading">
        <i data-lucide="loader-circle"></i><span>${t('studio.loading')}</span>
      </div>`;
  } else if (result && result.error) {
    wrap.innerHTML = `
      <div class="result-error">
        <i data-lucide="circle-x"></i><span>${esc(result.error)}</span>
      </div>`;
  } else if (result && result.image) {
    wrap.innerHTML = `
      <div class="result-frame">
        <img src="${result.image}" alt="selfie preview" draggable="false">
        <div class="result-bar">
          <button type="button" class="ghost-btn" data-result="copy"><i data-lucide="text-quote"></i><span>${t('studio.copyTag')}</span></button>
          <a class="ghost-btn" href="${result.image}" download="selfie.png"><i data-lucide="upload"></i><span>${t('studio.download')}</span></a>
          <button type="button" class="primary-btn" data-result="again"><i data-lucide="refresh-cw"></i><span>${t('studio.again')}</span></button>
        </div>
      </div>`;
  } else {
    wrap.innerHTML = `
      <div class="result-empty">
        <span class="empty-orb"><i data-lucide="camera"></i></span>
        <p class="empty-title">${t('studio.emptyTitle')}</p>
        <p class="empty-sub">${t('studio.emptySub')}</p>
      </div>`;
  }
  refreshIcons();
}

function currentTag() {
  const prompt = $('#studio-prompt').value.trim();
  const names = (ids) => state.items
    .filter((item) => ids.includes(item.id))
    .map((item) => item.name)
    .join(',');
  const outfit = names([...state.studio.outfits]);
  const sceneName = state.items.find((item) => item.id === state.studio.scene);
  const attrs = [
    outfit ? `outfit="${outfit}"` : '',
    sceneName ? `scene="${sceneName.name}"` : '',
  ].filter(Boolean).join(' ');
  return `<dressup ${attrs}>${prompt}</dressup>`;
}

async function shoot() {
  if (state.studio.busy) return;
  const prompt = $('#studio-prompt').value.trim();
  if (!prompt) {
    toast('info', 'studio.needPrompt');
    $('#studio-prompt').focus();
    return;
  }
  state.studio.busy = true;
  state.studio.result = null;
  renderStudioResult();
  try {
    const data = await api.testshot({
      outfit_ids: [...state.studio.outfits],
      scene_id: state.studio.scene || '',
      prompt,
    });
    state.studio.result = data;
  } catch (e) {
    state.studio.result = { error: e.message };
  }
  state.studio.busy = false;
  renderStudioResult();
}

async function copyTag() {
  const text = currentTag();
  try {
    await navigator.clipboard.writeText(text);
    toast('success', 'toast.copied');
  } catch (_) {
    const helper = document.createElement('textarea');
    helper.value = text;
    helper.style.position = 'fixed';
    helper.style.opacity = '0';
    document.body.appendChild(helper);
    helper.select();
    const copied = document.execCommand('copy');
    helper.remove();
    toast(copied ? 'success' : 'error', copied ? 'toast.copied' : 'toast.copyFailed');
  }
}

/* ── Grid & dialog event wiring ──────────────────────────────────────── */

function bindGrid(kind) {
  const grid = $(`#${KIND_KEY[kind]}-grid`);

  grid.addEventListener('click', (event) => {
    if (event.target.closest('[data-empty-upload]')) {
      openUpload(kind);
      return;
    }
    const button = event.target.closest('[data-act]');
    if (!button) return;
    const card = button.closest('.item-card');
    const item = state.items.find((entry) => entry.id === card?.dataset.id);
    if (!item) return;
    const act = button.dataset.act;
    if (act === 'edit') openEdit(item);
    else if (act === 'toggle') toggleItem(item);
    else if (act === 'delete') deleteItem(item);
  });

  let dragDepth = 0;
  grid.addEventListener('dragenter', (event) => {
    event.preventDefault();
    dragDepth += 1;
    if (!grid.querySelector('.grid-drop')) {
      const veil = document.createElement('div');
      veil.className = 'grid-drop';
      veil.innerHTML = `<i data-lucide="image-plus"></i><span>${t('upload.drop')}</span>`;
      grid.appendChild(veil);
      refreshIcons();
    }
  });
  grid.addEventListener('dragover', (event) => event.preventDefault());
  grid.addEventListener('dragleave', () => {
    dragDepth = Math.max(0, dragDepth - 1);
    if (!dragDepth) grid.querySelector('.grid-drop')?.remove();
  });
  grid.addEventListener('drop', (event) => {
    event.preventDefault();
    dragDepth = 0;
    grid.querySelector('.grid-drop')?.remove();
    const files = [...(event.dataTransfer?.files || [])].filter((f) => f.type.startsWith('image/'));
    if (files.length) openUpload(kind, files);
  });
}

function bindFilters(kind) {
  $(`#${KIND_KEY[kind]}-filters`).addEventListener('click', (event) => {
    const chip = event.target.closest('.chip');
    if (!chip) return;
    state.filters[kind] = chip.dataset.cat;
    renderGrid(kind);
  });
  $(`#${KIND_KEY[kind]}-search`).addEventListener('input', (event) => {
    state.search[kind] = event.target.value;
    renderGrid(kind);
  });
}

function bindDialogChrome(rootId) {
  const root = $(rootId);
  root.addEventListener('click', (event) => {
    if (event.target.closest('[data-close]')) closeDialog(rootId);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !root.hidden) closeDialog(rootId);
  });
}

function bindUploadDialog() {
  const dropzone = $('#upload-dropzone');
  const input = $('#upload-input');

  dropzone.addEventListener('click', () => input.click());
  dropzone.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') input.click();
  });
  input.addEventListener('change', () => {
    if (input.files.length) addFiles([...input.files]);
    input.value = '';
  });
  dropzone.addEventListener('dragover', (event) => {
    event.preventDefault();
    dropzone.classList.add('is-over');
  });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('is-over'));
  dropzone.addEventListener('drop', (event) => {
    event.preventDefault();
    dropzone.classList.remove('is-over');
    const files = [...(event.dataTransfer?.files || [])].filter((f) => f.type.startsWith('image/'));
    if (files.length) addFiles(files);
  });

  $('#upload-queue').addEventListener('input', (event) => {
    const rowNode = event.target.closest('.queue-row');
    if (!rowNode) return;
    const row = state.queue[Number(rowNode.dataset.index)];
    if (!row) return;
    const field = event.target.dataset.field;
    if (field === 'name') row.name = event.target.value;
    if (field === 'note') row.note = event.target.value;
  });
  $('#upload-queue').addEventListener('change', (event) => {
    const rowNode = event.target.closest('.queue-row');
    if (!rowNode) return;
    const row = state.queue[Number(rowNode.dataset.index)];
    if (row && event.target.dataset.field === 'category') {
      row.category = event.target.value;
    }
  });
  $('#upload-queue').addEventListener('click', (event) => {
    const remove = event.target.closest('[data-remove]');
    if (!remove) return;
    const rowNode = remove.closest('.queue-row');
    const [row] = state.queue.splice(Number(rowNode.dataset.index), 1);
    if (row) URL.revokeObjectURL(row.url);
    renderQueue();
  });

  $('#upload-start').addEventListener('click', startUpload);
}

function bindEditDialog() {
  $('#edit-save').addEventListener('click', saveEdit);
  $('#edit-delete').addEventListener('click', deleteFromEdit);
}

function bindConfirmDialog() {
  $('#confirm-accept').addEventListener('click', () => {
    closeDialog('#dialog-confirm');
    if (state.confirmResolve) {
      state.confirmResolve(true);
      state.confirmResolve = null;
    }
  });
  $('#dialog-confirm').addEventListener('click', (event) => {
    if (event.target.closest('[data-close]') && state.confirmResolve) {
      closeDialog('#dialog-confirm');
      state.confirmResolve(false);
      state.confirmResolve = null;
    }
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !$('#dialog-confirm').hidden) {
      closeDialog('#dialog-confirm');
      if (state.confirmResolve) {
        state.confirmResolve(false);
        state.confirmResolve = null;
      }
    }
  });
}

/* ── Studio wiring ───────────────────────────────────────────────────── */

function bindStudio() {
  $('#studio-outfits').addEventListener('click', (event) => {
    const tile = event.target.closest('.pick-tile');
    if (!tile) return;
    const id = tile.dataset.id;
    if (state.studio.outfits.has(id)) state.studio.outfits.delete(id);
    else state.studio.outfits.add(id);
    renderStudioPicks();
  });
  $('#studio-scenes').addEventListener('click', (event) => {
    const tile = event.target.closest('.pick-tile');
    if (!tile) return;
    state.studio.scene = state.studio.scene === tile.dataset.id ? null : tile.dataset.id;
    renderStudioPicks();
  });
  $('#studio-form').addEventListener('submit', (event) => {
    event.preventDefault();
    shoot();
  });
  $('#studio-result').addEventListener('click', (event) => {
    const action = event.target.closest('[data-result]');
    if (!action) return;
    if (action.dataset.result === 'again') shoot();
    if (action.dataset.result === 'copy') copyTag();
  });
}

/* ── Locale (always follows the WebUI host via the bridge) ───────────── */

function bindLocaleSync() {
  onLocaleChange(() => {
    applyStatic();
    renderAll();
  });
}

/* ── Boot ────────────────────────────────────────────────────────────── */

async function init() {
  const ctx = await window.PluginPageContext.ready();
  setLocale(ctx.locale || 'zh');

  document.querySelectorAll('.nav-item').forEach((node) => {
    node.addEventListener('click', () => switchView(node.dataset.view));
  });

  $('#wardrobe-upload').addEventListener('click', () => openUpload('wardrobe'));
  $('#scenes-upload').addEventListener('click', () => openUpload('scene'));
  bindGrid('wardrobe');
  bindGrid('scene');
  bindFilters('wardrobe');
  bindFilters('scene');
  bindUploadDialog();
  bindEditDialog();
  bindConfirmDialog();
  bindDialogChrome('#dialog-upload');
  bindDialogChrome('#dialog-edit');
  bindStudio();
  bindLocaleSync();

  await loadItems();
  applyStatic();
  renderAll();

  // Locale changes always come from the WebUI host context.
  window.PluginPageContext.onContext((next) => {
    if (next.locale) setLocale(next.locale);
  });
}

init().catch((e) => toast('error', 'toast.loadFailed', { reason: e.message }));
