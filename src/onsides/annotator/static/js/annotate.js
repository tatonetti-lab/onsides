// State
let state = {
    taskId: null,
    task: null,
    annotator: null,
    labelId: null,
    label: null,
    currentSection: null,
    doc: null,
    saveTimer: null,
};

// -- Initialization --

async function initAnnotatePage() {
    const params = new URLSearchParams(window.location.search);
    state.taskId = params.get('task_id');
    state.labelId = params.get('label_id');
    state.annotator = localStorage.getItem('annotator') || 'anonymous';

    if (!state.taskId || !state.labelId) {
        document.getElementById('workspace').innerHTML = '<p style="padding:40px">Missing task_id or label_id parameter.</p>';
        return;
    }

    document.getElementById('annotator-name').textContent = state.annotator;

    const [task, label, existingDoc] = await Promise.all([
        API.getTask(state.taskId),
        API.getLabel(state.taskId, state.labelId),
        API.loadAnnotation(state.taskId, state.annotator, state.labelId),
    ]);

    state.task = task;
    state.label = label;

    document.getElementById('drug-title').textContent = label.title;

    if (existingDoc) {
        state.doc = existingDoc;
    } else {
        const sections = {};
        for (const sec of label.sections) {
            sections[sec.section_code] = [];
        }
        state.doc = {
            task_id: state.taskId,
            label_id: state.labelId,
            label_title: label.title,
            annotator: state.annotator,
            status: 'in_progress',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            sections: sections,
            notes: '',
        };
    }

    renderSectionTabs();
    if (label.sections.length > 0) {
        switchSection(label.sections[0].section_code);
    }

    document.getElementById('notes-input').value = state.doc.notes || '';
    updateCompleteButton();
    initVocabSearch();
}

// -- Section tabs --

function renderSectionTabs() {
    const container = document.getElementById('section-tabs');
    container.innerHTML = '';
    for (const sec of state.label.sections) {
        const btn = document.createElement('button');
        btn.className = 'section-tab';
        btn.textContent = sec.section_code;
        btn.dataset.section = sec.section_code;
        btn.onclick = () => switchSection(sec.section_code);
        container.appendChild(btn);
    }
}

function switchSection(code) {
    state.currentSection = code;
    document.querySelectorAll('.section-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.section === code);
    });
    renderSectionText();
    renderAnnotationList();
}

// -- Section text rendering with highlights --

function renderSectionText() {
    const sec = state.label.sections.find(s => s.section_code === state.currentSection);
    if (!sec) return;

    const container = document.getElementById('section-text');
    const text = sec.text;
    const matches = sec.vocab_matches;
    const annotations = state.doc.sections[state.currentSection] || [];
    const annotatedStarts = new Set(annotations.map(a => `${a.start}-${a.end}`));

    let html = '';
    let pos = 0;

    for (const m of matches) {
        if (m.start < pos) continue;
        if (m.start > pos) {
            html += escapeHtml(text.slice(pos, m.start));
        }
        const end = m.start + m.length;
        const key = `${m.start}-${end}`;
        const isAnnotated = annotatedStarts.has(key);
        const cls = isAnnotated ? 'vocab-match annotated' : 'vocab-match';
        html += `<span class="${cls}" data-start="${m.start}" data-end="${end}" `
            + `data-code="${esc(m.code)}" data-pt-code="${esc(m.pt_code || '')}" `
            + `data-pt-name="${esc(m.pt_name || '')}" data-term="${esc(m.term)}" `
            + `data-vocab-id="${esc(m.vocab_id)}">`
            + escapeHtml(text.slice(m.start, end))
            + '</span>';
        pos = end;
    }
    if (pos < text.length) {
        html += escapeHtml(text.slice(pos));
    }

    container.innerHTML = html;

    container.querySelectorAll('.vocab-match').forEach(el => {
        el.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleTerm(el);
        });
    });
}

function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function esc(str) {
    return (str || '').replace(/"/g, '&quot;');
}

// -- Toggle vocab term (click = immediate add/remove for ALL occurrences) --

function toggleTerm(el) {
    dismissSelectionBtn();
    const term = el.dataset.term;
    const code = el.dataset.code;
    const ptCode = el.dataset.ptCode;
    const ptName = el.dataset.ptName;
    const section = state.currentSection;

    if (!state.doc.sections[section]) state.doc.sections[section] = [];
    const annotations = state.doc.sections[section];

    const start = parseInt(el.dataset.start);
    const end = parseInt(el.dataset.end);
    const existing = annotations.find(a => a.start === start && a.end === end);

    if (existing) {
        // Remove ALL occurrences of this term in this section
        state.doc.sections[section] = annotations.filter(a => a.term_text !== term);
    } else {
        // Add ALL occurrences of this term in this section
        const allSpans = document.querySelectorAll(`.vocab-match[data-term="${CSS.escape(term)}"]`);
        for (const span of allSpans) {
            const s = parseInt(span.dataset.start);
            const e = parseInt(span.dataset.end);
            const dup = annotations.find(a => a.start === s && a.end === e);
            if (!dup) {
                annotations.push({
                    id: crypto.randomUUID(),
                    entity_type: state.task.annotation_schema.entity_type,
                    term_text: term,
                    term_code: code || null,
                    pt_code: ptCode || null,
                    pt_name: ptName || null,
                    start: s,
                    end: e,
                    section_code: section,
                    source: 'vocab_click',
                    extra_fields: {},
                });
            }
        }
    }

    renderSectionText();
    renderAnnotationList();
    scheduleSave();
}

function dismissSelectionBtn() {
    const btn = document.getElementById('selection-btn');
    if (btn) btn.remove();
}

// -- Annotations CRUD (for free-text selections) --

function addAnnotation(start, end, term, code, ptCode, ptName, source) {
    const section = state.currentSection;
    if (!state.doc.sections[section]) state.doc.sections[section] = [];

    const dup = state.doc.sections[section].find(a => a.start === start && a.end === end);
    if (dup) return;

    state.doc.sections[section].push({
        id: crypto.randomUUID(),
        entity_type: state.task.annotation_schema.entity_type,
        term_text: term,
        term_code: code || null,
        pt_code: ptCode || null,
        pt_name: ptName || null,
        start: start,
        end: end,
        section_code: section,
        source: source,
        extra_fields: {},
    });

    dismissSelectionBtn();
    renderSectionText();
    renderAnnotationList();
    scheduleSave();
}

function removeAnnotationByTerm(term) {
    const section = state.currentSection;
    state.doc.sections[section] = (state.doc.sections[section] || []).filter(
        a => a.term_text !== term
    );
    renderSectionText();
    renderAnnotationList();
    scheduleSave();
}

function removeAnnotation(start, end) {
    const section = state.currentSection;
    state.doc.sections[section] = (state.doc.sections[section] || []).filter(
        a => !(a.start === start && a.end === end)
    );
    renderSectionText();
    renderAnnotationList();
    scheduleSave();
}

// -- Annotation list sidebar --

function renderAnnotationList() {
    const container = document.getElementById('annotation-list');
    const annotations = state.doc.sections[state.currentSection] || [];

    if (annotations.length === 0) {
        container.innerHTML = '<p style="color:#999; font-size:0.9rem; padding:8px;">No annotations yet for this section.</p>';
        return;
    }

    // Group by term text, show count for multi-occurrence terms
    const byTerm = new Map();
    for (const a of annotations) {
        const key = a.term_text.toLowerCase();
        if (!byTerm.has(key)) {
            byTerm.set(key, { repr: a, count: 1 });
        } else {
            byTerm.get(key).count++;
        }
    }

    const groups = [...byTerm.values()].sort((a, b) =>
        a.repr.term_text.toLowerCase().localeCompare(b.repr.term_text.toLowerCase())
    );

    container.innerHTML = groups.map(g => {
        const a = g.repr;
        const countLabel = g.count > 1 ? ` <span style="color:#666">&times;${g.count}</span>` : '';
        return `
        <div class="ann-item">
            <div>
                <div class="ann-text">${escapeHtml(a.term_text)}${countLabel}</div>
                <div class="ann-pt">${a.pt_name ? escapeHtml(a.pt_name) : ''} ${a.pt_code ? '(' + a.pt_code + ')' : ''}</div>
            </div>
            <button class="ann-delete" onclick="removeAnnotationByTerm('${esc(a.term_text)}')" title="Remove">&times;</button>
        </div>
    `}).join('');
}

// -- Free text selection --

document.addEventListener('mouseup', (e) => {
    if (!state.task || !state.task.annotation_schema.allow_free_text) return;

    // Don't interfere if clicking the selection button itself
    if (e.target.id === 'selection-btn') return;

    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) {
        dismissSelectionBtn();
        return;
    }

    const range = sel.getRangeAt(0);
    const container = document.getElementById('section-text');
    if (!container.contains(range.startContainer)) return;

    const selectedText = sel.toString().trim();
    if (!selectedText || selectedText.length < 2) return;

    const textOffset = getTextOffset(container, range.startContainer, range.startOffset);
    const endOffset = textOffset + selectedText.length;

    dismissSelectionBtn();

    const btn = document.createElement('button');
    btn.className = 'selection-btn';
    btn.id = 'selection-btn';
    const entityLabel = state.task.annotation_schema.entity_type.replace(/_/g, ' ');
    btn.textContent = `Mark "${selectedText.slice(0, 30)}${selectedText.length > 30 ? '...' : ''}" as ${entityLabel}`;
    btn.addEventListener('click', (ev) => {
        ev.stopPropagation();
        addAnnotation(textOffset, endOffset, selectedText, null, null, null, 'text_select');
        sel.removeAllRanges();
    });

    const rect = range.getBoundingClientRect();
    btn.style.top = (rect.bottom + window.scrollY + 6) + 'px';
    btn.style.left = (rect.left + window.scrollX) + 'px';
    document.body.appendChild(btn);
});

function getTextOffset(root, node, offset) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let total = 0;
    while (walker.nextNode()) {
        if (walker.currentNode === node) {
            return total + offset;
        }
        total += walker.currentNode.textContent.length;
    }
    return total;
}

// -- Vocab search --

function initVocabSearch() {
    const input = document.getElementById('vocab-search');
    let timer = null;
    input.addEventListener('input', () => {
        clearTimeout(timer);
        const q = input.value.trim();
        if (q.length < 2) {
            document.getElementById('vocab-results').innerHTML = '';
            return;
        }
        timer = setTimeout(async () => {
            const results = await API.searchVocab(state.taskId, q);
            renderVocabResults(results);
        }, 300);
    });
}

function renderVocabResults(results) {
    const container = document.getElementById('vocab-results');
    if (results.length === 0) {
        container.innerHTML = '<div style="padding:6px;color:#999;font-size:0.9rem;">No matches</div>';
        return;
    }
    container.innerHTML = results.slice(0, 30).map(r => `
        <div class="vocab-result" onclick="scrollToTerm('${esc(r.term)}')">
            ${escapeHtml(r.term)}
            <span class="vr-code">${r.pt_name && r.pt_name !== r.term ? '(' + escapeHtml(r.pt_name) + ')' : ''}</span>
        </div>
    `).join('');
}

function scrollToTerm(term) {
    const matches = document.querySelectorAll('.vocab-match');
    for (const el of matches) {
        if (el.dataset.term === term || el.textContent.toLowerCase() === term.toLowerCase()) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            el.style.outline = '2px solid #4a90d9';
            setTimeout(() => { el.style.outline = ''; }, 2000);
            return;
        }
    }
}

// -- Save --

function scheduleSave() {
    clearTimeout(state.saveTimer);
    state.saveTimer = setTimeout(doSave, 500);
}

async function doSave() {
    state.doc.updated_at = new Date().toISOString();
    state.doc.notes = document.getElementById('notes-input').value || '';
    await API.saveAnnotation(state.taskId, state.annotator, state.labelId, state.doc);
}

// -- Complete --

function updateCompleteButton() {
    const btn = document.getElementById('btn-complete');
    if (state.doc.status === 'complete') {
        btn.textContent = 'Completed (click to reopen)';
        btn.classList.add('completed');
    } else {
        btn.textContent = 'Mark Complete';
        btn.classList.remove('completed');
    }
}

function toggleComplete() {
    state.doc.status = state.doc.status === 'complete' ? 'in_progress' : 'complete';
    updateCompleteButton();
    scheduleSave();
}

// -- Notes auto-save --

document.addEventListener('DOMContentLoaded', () => {
    const notes = document.getElementById('notes-input');
    if (notes) {
        notes.addEventListener('input', scheduleSave);
    }
});

// -- Keyboard shortcuts --

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closePopover();
});

// -- Back navigation --

function goBack() {
    window.location.href = `/annotate.html?task_id=${state.taskId}&view=list`;
}

// Boot
document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('label_id')) {
        initAnnotatePage();
    } else {
        initLabelList();
    }
});

// -- Label list view --

let listState = { page: 1, search: '', total: 0, perPage: 50, activeTab: 'all' };

async function initLabelList() {
    const params = new URLSearchParams(window.location.search);
    state.taskId = params.get('task_id');
    state.annotator = localStorage.getItem('annotator') || 'anonymous';

    if (!state.taskId) {
        window.location.href = '/';
        return;
    }

    state.task = await API.getTask(state.taskId);

    document.getElementById('workspace').classList.add('hidden');
    document.getElementById('label-list-view').classList.remove('hidden');
    document.getElementById('list-task-name').textContent = state.task.name;
    document.getElementById('list-annotator').textContent = state.annotator;

    const searchInput = document.getElementById('list-search');
    let timer = null;
    searchInput.addEventListener('input', () => {
        clearTimeout(timer);
        timer = setTimeout(() => {
            listState.search = searchInput.value.trim();
            listState.page = 1;
            loadLabelList();
        }, 300);
    });

    loadMyAnnotations();
    loadLabelList();
}

function switchListTab(tab) {
    listState.activeTab = tab;
    document.getElementById('tab-all').classList.toggle('active', tab === 'all');
    document.getElementById('tab-mine').classList.toggle('active', tab === 'mine');
    document.getElementById('panel-all').classList.toggle('hidden', tab !== 'all');
    document.getElementById('panel-mine').classList.toggle('hidden', tab !== 'mine');
}

async function loadMyAnnotations() {
    const myAnnotations = await API.listAnnotations(state.taskId, state.annotator);
    const countEl = document.getElementById('my-count');
    countEl.textContent = myAnnotations.length > 0 ? `(${myAnnotations.length})` : '';

    const tbody = document.getElementById('my-tbody');
    const emptyMsg = document.getElementById('my-empty');

    if (myAnnotations.length === 0) {
        tbody.innerHTML = '';
        emptyMsg.classList.remove('hidden');
        return;
    }
    emptyMsg.classList.add('hidden');

    myAnnotations.sort((a, b) => {
        if (a.status === 'complete' && b.status !== 'complete') return 1;
        if (a.status !== 'complete' && b.status === 'complete') return -1;
        return b.updated_at.localeCompare(a.updated_at);
    });

    tbody.innerHTML = myAnnotations.map(a => {
        const badge = a.status === 'complete'
            ? `<span class="badge badge-complete">Complete</span>`
            : `<span class="badge badge-progress">In progress</span>`;
        const date = a.updated_at ? new Date(a.updated_at).toLocaleDateString() : '';
        return `<tr onclick="openLabel('${esc(a.label_id)}')">
            <td>${escapeHtml(a.label_title)}</td>
            <td>${a.annotation_count}</td>
            <td>${badge}</td>
            <td>${date}</td>
        </tr>`;
    }).join('');
}

async function loadLabelList() {
    const data = await API.getLabels(state.taskId, listState.page, listState.perPage, listState.search);
    listState.total = data.total;

    const tbody = document.getElementById('label-tbody');
    tbody.innerHTML = data.items.map(item => {
        return `<tr onclick="openLabel('${esc(item.set_id)}')">
            <td>${escapeHtml(item.title)}</td>
            <td>${item.sections_available.join(', ')}</td>
            <td></td>
        </tr>`;
    }).join('');

    document.getElementById('list-page-info').textContent =
        `Page ${listState.page} of ${data.pages} (${data.total} labels)`;
    document.getElementById('btn-prev').disabled = listState.page <= 1;
    document.getElementById('btn-next').disabled = listState.page >= data.pages;
}

function listPrev() { listState.page--; loadLabelList(); }
function listNext() { listState.page++; loadLabelList(); }

function openLabel(setId) {
    window.location.href = `/annotate.html?task_id=${state.taskId}&label_id=${setId}`;
}
