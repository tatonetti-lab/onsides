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
    pendingSelection: null,  // {start, end, text} when user has selected text for vocab assignment
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

    document.getElementById('drug-title').textContent = label.drug_name || label.title;

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
    const vocabMatches = sec.vocab_matches;
    const annotations = state.doc.sections[state.currentSection] || [];
    // Build a unified list of highlight regions: vocab matches + free-text annotations
    const regions = [];

    // Check if a position range is covered by any annotation (exact match or contained within)
    function isAnnotated(start, end) {
        return annotations.some(a =>
            (a.start === start && a.end === end) ||
            (a.start <= start && a.end >= end)
        );
    }

    for (const m of vocabMatches) {
        const end = m.start + m.length;
        regions.push({
            start: m.start, end,
            type: 'vocab',
            annotated: isAnnotated(m.start, end),
            code: m.code, ptCode: m.pt_code || '', ptName: m.pt_name || '',
            term: m.term, vocabId: m.vocab_id,
        });
    }

    // Add free-text annotation spans for parts that don't overlap vocab matches
    for (const a of annotations) {
        if (a.source !== 'text_select') continue;
        // Find gaps in this annotation range not covered by vocab regions
        const overlapping = regions
            .filter(r => r.type === 'vocab' && !(a.end <= r.start || a.start >= r.end))
            .sort((x, y) => x.start - y.start);
        if (overlapping.length === 0) {
            regions.push({
                start: a.start, end: a.end,
                type: 'freetext', annotated: true,
                code: '', ptCode: '', ptName: '',
                term: a.term_text, vocabId: '',
            });
        } else {
            let cursor = a.start;
            for (const r of overlapping) {
                if (r.start > cursor) {
                    regions.push({
                        start: cursor, end: r.start,
                        type: 'freetext', annotated: true,
                        code: '', ptCode: '', ptName: '',
                        term: a.term_text, vocabId: '',
                    });
                }
                cursor = Math.max(cursor, r.end);
            }
            if (cursor < a.end) {
                regions.push({
                    start: cursor, end: a.end,
                    type: 'freetext', annotated: true,
                    code: '', ptCode: '', ptName: '',
                    term: a.term_text, vocabId: '',
                });
            }
        }
    }

    regions.sort((a, b) => a.start - b.start || b.end - a.end);

    let html = '';
    let pos = 0;

    for (const r of regions) {
        if (r.start < pos) continue;
        if (r.start > pos) {
            html += escapeHtml(text.slice(pos, r.start));
        }
        const cls = r.type === 'vocab'
            ? (r.annotated ? 'vocab-match annotated' : 'vocab-match')
            : 'freetext-match annotated';
        html += `<span class="${cls}" data-start="${r.start}" data-end="${r.end}" `
            + `data-code="${esc(r.code)}" data-pt-code="${esc(r.ptCode)}" `
            + `data-pt-name="${esc(r.ptName)}" data-term="${esc(r.term)}" `
            + `data-vocab-id="${esc(r.vocabId)}" data-type="${r.type}">`
            + escapeHtml(text.slice(r.start, r.end))
            + '</span>';
        pos = r.end;
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
    container.querySelectorAll('.freetext-match').forEach(el => {
        el.addEventListener('click', (e) => {
            e.stopPropagation();
            removeAnnotation(parseInt(el.dataset.start), parseInt(el.dataset.end));
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

function addAllTerms(termDataList) {
    const section = state.currentSection;
    if (!state.doc.sections[section]) state.doc.sections[section] = [];
    const annotations = state.doc.sections[section];

    // Collect unique terms from the selection, then add all occurrences of each
    const uniqueTerms = new Map();
    for (const td of termDataList) {
        if (!uniqueTerms.has(td.term)) {
            uniqueTerms.set(td.term, td);
        }
    }

    const sec = state.label.sections.find(s => s.section_code === section);
    if (!sec) return;

    for (const [term, td] of uniqueTerms) {
        for (const m of sec.vocab_matches) {
            if (m.term !== term) continue;
            const mEnd = m.start + m.length;
            const dup = annotations.find(a => a.start === m.start && a.end === mEnd);
            if (!dup) {
                annotations.push({
                    id: crypto.randomUUID(),
                    entity_type: state.task.annotation_schema.entity_type,
                    term_text: term,
                    term_code: m.code || null,
                    pt_code: m.pt_code || td.ptCode || null,
                    pt_name: m.pt_name || td.ptName || null,
                    start: m.start,
                    end: mEnd,
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

function clearPendingSelection() {
    state.pendingSelection = null;
    updatePendingSelectionIndicator();
}

function updatePendingSelectionIndicator() {
    const indicator = document.getElementById('pending-selection-indicator');
    if (!indicator) return;
    if (state.pendingSelection) {
        const text = state.pendingSelection.text;
        const display = text.length > 30 ? text.slice(0, 30) + '...' : text;
        indicator.innerHTML = `Assigning to: <strong>${escapeHtml(display)}</strong> `
            + `<button onclick="clearPendingSelection()" style="border:none;background:none;cursor:pointer;color:#999;font-size:1rem;">&times;</button>`;
        indicator.classList.remove('hidden');
    } else {
        indicator.classList.add('hidden');
    }
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
        let ptLine = '';
        if (a.pt_name && a.pt_name.toLowerCase() !== a.term_text.toLowerCase()) {
            ptLine = `<div class="ann-mapped">&rarr; ${escapeHtml(a.pt_name)}${a.pt_code ? ' (' + a.pt_code + ')' : ''}</div>`;
        } else if (a.pt_name && a.pt_code) {
            ptLine = `<div class="ann-pt">${escapeHtml(a.pt_name)} (${a.pt_code})</div>`;
        }
        return `
        <div class="ann-item">
            <div>
                <div class="ann-text">${escapeHtml(a.term_text)}${countLabel}</div>
                ${ptLine}
            </div>
            <button class="ann-delete" onclick="removeAnnotationByTerm('${esc(a.term_text)}')" title="Remove">&times;</button>
        </div>
    `}).join('');
}

// -- Free text selection --

document.addEventListener('mouseup', (e) => {
    if (!state.task) return;

    // Don't interfere if clicking a selection action button
    if (e.target.closest('.selection-btn-group')) return;

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

    // Compute text offsets from both ends of the range independently
    const textOffset = getTextOffset(container, range.startContainer, range.startOffset);
    const endOffset = getTextOffset(container, range.endContainer, range.endOffset);

    // Find unannotated vocab matches fully inside the selection using text offsets
    const containedTerms = [];
    container.querySelectorAll('.vocab-match:not(.annotated)').forEach(el => {
        const s = parseInt(el.dataset.start);
        const e = parseInt(el.dataset.end);
        if (s >= textOffset && e <= endOffset) {
            containedTerms.push(el);
        }
    });

    // Store the pending selection so vocab search can assign a term to it
    state.pendingSelection = { start: textOffset, end: endOffset, text: selectedText };
    updatePendingSelectionIndicator();

    // Auto-populate vocab search with the selected text
    const vocabInput = document.getElementById('vocab-search');
    vocabInput.value = selectedText;
    vocabInput.dispatchEvent(new Event('input'));

    dismissSelectionBtn();

    const rect = range.getBoundingClientRect();
    const group = document.createElement('div');
    group.className = 'selection-btn-group';
    group.id = 'selection-btn';
    group.style.position = 'absolute';
    group.style.top = (rect.bottom + window.scrollY + 6) + 'px';
    group.style.left = (rect.left + window.scrollX) + 'px';
    group.style.zIndex = '200';
    group.style.display = 'flex';
    group.style.flexDirection = 'column';
    group.style.gap = '4px';

    // "Add All Events" button if multiple vocab terms are in the selection
    if (containedTerms.length > 1) {
        const termData = containedTerms.map(el => ({
            term: el.dataset.term,
            code: el.dataset.code,
            ptCode: el.dataset.ptCode,
            ptName: el.dataset.ptName,
            start: parseInt(el.dataset.start),
            end: parseInt(el.dataset.end),
        }));
        const addAllBtn = document.createElement('button');
        addAllBtn.className = 'selection-btn';
        addAllBtn.textContent = `Add All Events (${containedTerms.length})`;
        addAllBtn.addEventListener('click', (ev) => {
            ev.stopPropagation();
            addAllTerms(termData);
            sel.removeAllRanges();
            dismissSelectionBtn();
            clearPendingSelection();
        });
        group.appendChild(addAllBtn);
    }

    // Free-text annotation button
    if (state.task.annotation_schema.allow_free_text) {
        const entityLabel = state.task.annotation_schema.entity_type.replace(/_/g, ' ');
        const freeBtn = document.createElement('button');
        freeBtn.className = 'selection-btn';
        if (containedTerms.length > 1) {
            freeBtn.style.background = '#6c757d';
        }
        freeBtn.textContent = `Mark "${selectedText.slice(0, 25)}${selectedText.length > 25 ? '...' : ''}" as ${entityLabel}`;
        freeBtn.addEventListener('click', (ev) => {
            ev.stopPropagation();
            addAnnotation(textOffset, endOffset, selectedText, null, null, null, 'text_select');
            sel.removeAllRanges();
            clearPendingSelection();
        });
        group.appendChild(freeBtn);
    }

    if (group.children.length > 0) {
        document.body.appendChild(group);
    }
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
    container.innerHTML = results.slice(0, 30).map(r => {
        const ptInfo = r.pt_name && r.pt_name !== r.term ? '(' + escapeHtml(r.pt_name) + ')' : '';
        return `
        <div class="vocab-result" data-term="${esc(r.term)}" data-code="${esc(r.code)}"
             data-pt-code="${esc(r.pt_code || '')}" data-pt-name="${esc(r.pt_name || '')}">
            ${escapeHtml(r.term)}
            <span class="vr-code">${ptInfo}</span>
        </div>`;
    }).join('');

    container.querySelectorAll('.vocab-result').forEach(el => {
        el.addEventListener('click', () => onVocabResultClick(el));
    });
}

function onVocabResultClick(el) {
    const term = el.dataset.term;
    const code = el.dataset.code;
    const ptCode = el.dataset.ptCode || code;
    const ptName = el.dataset.ptName || term;

    if (state.pendingSelection) {
        const ps = state.pendingSelection;
        addAnnotationAllOccurrences(ps.text, code, ptCode, ptName);
        clearPendingSelection();
        document.getElementById('vocab-search').value = '';
        document.getElementById('vocab-results').innerHTML = '';
    } else {
        scrollToTerm(term);
    }
}

function addAnnotationAllOccurrences(text, code, ptCode, ptName) {
    const section = state.currentSection;
    if (!state.doc.sections[section]) state.doc.sections[section] = [];
    const annotations = state.doc.sections[section];

    const sec = state.label.sections.find(s => s.section_code === section);
    if (!sec) return;

    const searchText = text.toLowerCase();
    const sectionText = sec.text.toLowerCase();
    let idx = 0;
    while ((idx = sectionText.indexOf(searchText, idx)) !== -1) {
        const start = idx;
        const end = idx + text.length;
        const dup = annotations.find(a => a.start === start && a.end === end);
        if (!dup) {
            annotations.push({
                id: crypto.randomUUID(),
                entity_type: state.task.annotation_schema.entity_type,
                term_text: sec.text.slice(start, end),
                term_code: code || null,
                pt_code: ptCode || null,
                pt_name: ptName || null,
                start,
                end,
                section_code: section,
                source: 'text_select',
                extra_fields: {},
            });
        }
        idx = end;
    }

    renderSectionText();
    renderAnnotationList();
    scheduleSave();
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
    if (e.key === 'Escape') {
        dismissSelectionBtn();
        clearPendingSelection();
    }
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

let listState = { page: 1, search: '', total: 0, perPage: 50, activeTab: 'all', seed: 42 };

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
        const name = a.drug_name || a.label_title;
        return `<tr onclick="openLabel('${esc(a.label_id)}')">
            <td>${escapeHtml(name)}</td>
            <td style="font-size:0.8rem;color:#666;font-family:monospace;">${escapeHtml(a.label_id.slice(0, 8))}</td>
            <td>${a.annotation_count}</td>
            <td>${badge}</td>
            <td>${date}</td>
        </tr>`;
    }).join('');
}

async function loadLabelList() {
    const data = await API.getLabels(state.taskId, listState.page, listState.perPage, listState.search, listState.seed);
    listState.total = data.total;

    const tbody = document.getElementById('label-tbody');
    tbody.innerHTML = data.items.map(item => {
        const name = item.drug_name || item.title;
        return `<tr onclick="openLabel('${esc(item.set_id)}')">
            <td>${escapeHtml(name)}</td>
            <td style="font-size:0.8rem;color:#666;font-family:monospace;">${escapeHtml(item.set_id.slice(0, 8))}</td>
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
function shuffleLabels() { listState.seed = Math.floor(Math.random() * 100000); listState.page = 1; loadLabelList(); }

function openLabel(setId) {
    window.location.href = `/annotate.html?task_id=${state.taskId}&label_id=${setId}`;
}
