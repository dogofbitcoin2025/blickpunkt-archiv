/* ===================================================
   BlickPUNKT Archiv – app.js
   Zentrale JavaScript-Logik für alle Seiten
   =================================================== */

const API = '';

// === Utilities ===
function qs(sel, root = document) { return root.querySelector(sel); }
function qsa(sel, root = document) { return [...root.querySelectorAll(sel)]; }
function el(tag, attrs = {}, children = []) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
        if (k === 'text') e.textContent = v;
        else if (k === 'html') e.innerHTML = v;
        else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
        else if (k === 'class') e.className = v;
        else if (k === 'dataset') Object.assign(e.dataset, v);
        else e.setAttribute(k, v);
    }
    for (const c of children) {
        if (typeof c === 'string') e.appendChild(document.createTextNode(c));
        else if (c) e.appendChild(c);
    }
    return e;
}

async function apiFetch(path, opts = {}) {
    try {
        const resp = await fetch(API + path, opts);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const ct = resp.headers.get('content-type') || '';
        if (ct.includes('json')) return await resp.json();
        return await resp.text();
    } catch (err) {
        console.error('API Error:', err);
        showToast('Fehler: ' + err.message, 'error');
        throw err;
    }
}

function showToast(msg, type = 'info') {
    let container = qs('.toast-container');
    if (!container) {
        container = el('div', { class: 'toast-container' });
        document.body.appendChild(container);
    }
    const t = el('div', { class: `toast toast-${type}`, text: msg });
    container.appendChild(t);
    setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 300); }, 3500);
}

function formatDate(d) {
    if (!d) return '–';
    return new Date(d).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function truncate(s, n = 120) {
    if (!s) return '';
    return s.length > n ? s.slice(0, n) + '…' : s;
}

function debounce(fn, ms = 300) {
    let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

function statusBadge(status) {
    const cls = { neu: 'status-neu', verarbeitet: 'status-verarbeitet', fehler: 'status-fehler', download: 'status-download' };
    return `<span class="status-badge ${cls[status] || 'status-neu'}">${status || 'neu'}</span>`;
}

function typeBadge(type) {
    const badges = {
        'anzeige': '<span class="article-type-badge badge-anzeige">Anzeige</span>',
        'advertorial': '<span class="article-type-badge badge-advertorial">Advertorial</span>',
        'veranstaltungshinweis': '<span class="article-type-badge badge-event">Veranstaltung</span>',
        'leseraktion': '<span class="article-type-badge badge-leser">Leseraktion</span>',
        'unklar': '<span class="article-type-badge badge-unklar">Unklar</span>',
        'redaktionell': '<span class="article-type-badge badge-redaktionell">Redaktionell</span>',
    };
    return badges[type] || badges['redaktionell'];
}

function confidenceBadge(type, confidence) {
    if (!type || !confidence) return '';
    return `<span class="confidence-badge">${confidence} %</span>`;
}

// === Mobile Menu ===
document.addEventListener('DOMContentLoaded', () => {
    const menuBtn = qs('.mobile-menu-btn');
    const nav = qs('nav');
    if (menuBtn && nav) {
        menuBtn.addEventListener('click', () => nav.classList.toggle('open'));
    }
    // Highlight active nav
    const path = location.pathname;
    qsa('nav a').forEach(a => {
        if (a.getAttribute('href') === path) a.classList.add('active');
    });
});


// ============================================================
//  INDEX PAGE – Article Search
// ============================================================
async function initSearchPage() {
    const searchInput = qs('#search-input');
    const articleList = qs('#article-list');
    const resultsCount = qs('#results-count');
    const filterKategorie = qs('#filter-kategorie');
    const filterGemeinde = qs('#filter-gemeinde');
    const filterJahr = qs('#filter-jahr');
    const filterSaison = qs('#filter-saison');
    const filterType = qs('#filter-type');
    if (!articleList) return;

    let currentPage = 1;
    const pageSize = 20;

    // Load filter options
    try {
        const [categories, gemeinden, jahre, saisons] = await Promise.all([
            apiFetch('/api/categories'),
            apiFetch('/api/gemeinden'),
            apiFetch('/api/jahre'),
            apiFetch('/api/saisons')
        ]);
        categories.forEach(c => {
            filterKategorie.appendChild(el('option', { value: c.name, text: c.name }));
        });
        gemeinden.forEach(g => {
            filterGemeinde.appendChild(el('option', { value: g, text: g }));
        });
        jahre.forEach(j => {
            filterJahr.appendChild(el('option', { value: j, text: j }));
        });
        saisons.forEach(s => {
            filterSaison.appendChild(el('option', { value: s, text: s }));
        });
    } catch (e) { /* filters won't populate but search still works */ }

    async function doSearch() {
        const params = new URLSearchParams();
        const q = searchInput.value.trim();
        if (q) params.set('q', q);
        if (filterKategorie.value) params.set('kategorie', filterKategorie.value);
        if (filterGemeinde.value) params.set('gemeinde', filterGemeinde.value);
        if (filterJahr.value) params.set('jahr', filterJahr.value);
        if (filterSaison.value) params.set('saison', filterSaison.value);
        if (filterType.value) params.set('content_type', filterType.value);
        const excludeAds = qs('#exclude-ads');
        if (excludeAds && excludeAds.checked && !filterType.value) {
            params.set('exclude_ads', 'true');
        }
        params.set('limit', pageSize);
        params.set('offset', (currentPage - 1) * pageSize);

        articleList.innerHTML = '<div style="padding:2rem;text-align:center"><div class="spinner"></div></div>';

        try {
            const data = await apiFetch(`/api/articles?${params}`);
            const articles = data.articles || data;
            const total = data.total || articles.length;
            resultsCount.textContent = `${total} Artikel gefunden`;
            renderArticles(articles, total);
        } catch (e) {
            articleList.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><h3>Fehler beim Laden</h3></div>';
        }
    }

    function renderArticles(articles, total) {
        if (!articles.length) {
            articleList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📰</div>
                    <h3>Keine Artikel gefunden</h3>
                    <p>Versuche andere Suchbegriffe oder Filter. Oder scanne zuerst Ausgaben im Admin-Bereich.</p>
                </div>`;
            return;
        }

        articleList.innerHTML = '';
        articles.forEach(a => {
            const cats = (a.categories || []).map(c => `<span class="tag tag-category">${c}</span>`).join('');
            const kws = (a.keywords || []).slice(0, 4).map(k => `<span class="tag">${k}</span>`).join('');
            const card = el('div', {
                class: 'article-card',
                onclick: () => location.href = `/article/${a.id}`,
                html: `
                    <div class="article-meta-side">
                        <div class="meta-year">${a.jahr || '–'}</div>
                        <div class="meta-saison">${a.saison || ''}</div>
                        <div class="meta-seite">${a.page_start ? 'S. ' + a.page_start : ''}</div>
                    </div>
                    <div class="article-body">
                        <div style="display:flex;gap:0.5rem;align-items:center;margin-bottom:0.25rem;flex-wrap:wrap">
                            ${typeBadge(a.content_type || a.article_type)}
                            ${a.content_type_confidence ? confidenceBadge(a.content_type, a.content_type_confidence) : ''}
                            ${a.gemeinde ? `<span class="tag tag-gemeinde">${a.gemeinde}</span>` : ''}
                        </div>
                        <div class="article-title">${a.title || 'Ohne Titel'}</div>
                        <div class="article-summary">${truncate(a.summary || a.full_text || '', 160)}</div>
                        <div class="article-tags">${cats}${kws}</div>
                    </div>
                `
            });
            articleList.appendChild(card);
        });

        // Pagination
        const totalPages = Math.ceil(total / pageSize);
        if (totalPages > 1) {
            const pag = el('div', { class: 'pagination' });
            pag.appendChild(el('button', { text: '← Zurück', onclick: () => { if (currentPage > 1) { currentPage--; doSearch(); } }, ...(currentPage <= 1 ? { disabled: '' } : {}) }));
            const start = Math.max(1, currentPage - 2);
            const end = Math.min(totalPages, currentPage + 2);
            for (let i = start; i <= end; i++) {
                pag.appendChild(el('button', { text: i.toString(), class: i === currentPage ? 'active' : '', onclick: () => { currentPage = i; doSearch(); } }));
            }
            pag.appendChild(el('button', { text: 'Weiter →', onclick: () => { if (currentPage < totalPages) { currentPage++; doSearch(); } }, ...(currentPage >= totalPages ? { disabled: '' } : {}) }));
            articleList.appendChild(pag);
        }
    }

    const debouncedSearch = debounce(() => { currentPage = 1; doSearch(); }, 350);
    searchInput.addEventListener('input', debouncedSearch);
    [filterKategorie, filterGemeinde, filterJahr, filterSaison, filterType].forEach(f => {
        f.addEventListener('change', () => { currentPage = 1; doSearch(); });
    });
    const excludeAdsBox = qs('#exclude-ads');
    if (excludeAdsBox) excludeAdsBox.addEventListener('change', () => { currentPage = 1; doSearch(); });

    // Export buttons
    qs('#export-csv')?.addEventListener('click', () => window.open('/api/export/csv', '_blank'));
    qs('#export-json')?.addEventListener('click', () => window.open('/api/export/json', '_blank'));
    qs('#export-excel')?.addEventListener('click', () => window.open('/api/export/excel', '_blank'));

    doSearch();
}


// ============================================================
//  ARTICLE DETAIL PAGE
// ============================================================
async function initArticlePage() {
    const wrap = qs('#article-detail');
    if (!wrap) return;
    const id = location.pathname.split('/').pop();
    if (!id || isNaN(id)) return;

    wrap.innerHTML = '<div style="padding:3rem;text-align:center"><div class="spinner"></div></div>';

    try {
        const a = await apiFetch(`/api/articles/${id}`);
        const cats = (a.categories || []).map(c => `<span class="tag tag-category">${c}</span>`).join(' ');
        const kws = (a.keywords || []).map(k => `<span class="tag">${k}</span>`).join(' ');

        const simHtml = (a.similar_articles || []).map(s => `
            <a href="/article/${s.id}" class="similar-article">
                <div class="similar-score">${s.score}%</div>
                <div>
                    <div class="similar-title">${s.title}</div>
                    <div class="similar-meta">${s.saison || ''} ${s.jahr || ''} · ${s.gemeinde || ''}</div>
                </div>
            </a>
        `).join('') || '<p style="color:var(--clr-ink-muted);font-size:0.9rem">Keine ähnlichen Artikel gefunden.</p>';

        const people = (a.people || []).join(', ') || '–';
        const companies = (a.companies || []).join(', ') || '–';
        const clubs = (a.clubs || []).join(', ') || '–';
        const locations = (a.locations || []).join(', ') || '–';

        // Erkannte Signale aufbereiten
        let signalsArr = [];
        try {
            signalsArr = typeof a.detected_signals === 'string' ? JSON.parse(a.detected_signals) : (a.detected_signals || []);
        } catch(e) { signalsArr = []; }
        const signalsHtml = signalsArr.length
            ? signalsArr.map(s => `<div class="signal-item">• ${s}</div>`).join('')
            : '<div style="color:var(--clr-ink-muted);font-size:0.85rem">Keine Signale erkannt</div>';

        const contentTypeLabel = {
            'redaktionell': 'Redaktionell',
            'anzeige': 'Anzeige',
            'advertorial': 'Advertorial / PR',
            'veranstaltungshinweis': 'Veranstaltungshinweis',
            'leseraktion': 'Leseraktion',
            'unklar': 'Unklar'
        };

        wrap.innerHTML = `
            <div class="article-detail-header">
                <a href="/" style="font-size:0.85rem;margin-bottom:0.5rem;display:inline-block">← Zurück zur Suche</a>
                <div class="article-title">${a.title || 'Ohne Titel'}</div>
                <div class="article-meta-row">
                    <span>📍 ${a.gemeinde || '–'}</span>
                    <span>📅 ${a.saison || ''} ${a.jahr || ''}</span>
                    <span>📄 ${a.page_start ? 'Seite ' + a.page_start + (a.page_end && a.page_end !== a.page_start ? '–' + a.page_end : '') : '–'}</span>
                    <span>${typeBadge(a.content_type || a.article_type)}</span>
                    ${a.content_type_confidence ? `<span class="confidence-badge">${a.content_type_confidence} %</span>` : ''}
                    <span class="status-badge ${a.status === 'manuell geprüft' ? 'status-verarbeitet' : 'status-neu'}">${a.status || 'erkannt'}</span>
                </div>
            </div>
            <div class="two-col">
                <div class="main-col">
                    ${a.summary ? `<div class="card" style="margin-bottom:1.5rem;background:var(--clr-bg-warm)"><strong>Zusammenfassung:</strong> ${a.summary}</div>` : ''}
                    <div class="article-content">${(a.full_text || 'Kein Text vorhanden.').replace(/\n/g, '<br>')}</div>
                </div>
                <div class="side-col">
                    <div class="card detection-card">
                        <div class="card-title">📊 Inhaltstyp-Erkennung</div>
                        <div class="detection-result">
                            <div class="detection-type">
                                ${typeBadge(a.content_type || a.article_type)}
                                <span class="detection-confidence">${a.content_type_confidence || 0} %</span>
                            </div>
                            <div class="detection-scores">
                                <div class="score-bar-row">
                                    <span class="score-label">Redaktionell</span>
                                    <div class="score-bar"><div class="score-fill score-editorial" style="width:${Math.min(a.editorial_score || 0, 100)}%"></div></div>
                                    <span class="score-value">${a.editorial_score || 0}</span>
                                </div>
                                <div class="score-bar-row">
                                    <span class="score-label">Anzeige</span>
                                    <div class="score-bar"><div class="score-fill score-ad" style="width:${Math.min(a.ad_score || 0, 100)}%"></div></div>
                                    <span class="score-value">${a.ad_score || 0}</span>
                                </div>
                            </div>
                            <div class="detection-signals">
                                <strong style="font-size:0.85rem">Erkannte Signale:</strong>
                                <div style="margin-top:0.3rem">${signalsHtml}</div>
                            </div>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-title">Kategorien</div>
                        <div style="margin-top:0.5rem">${cats || '<span style="color:var(--clr-ink-muted)">Keine</span>'}</div>
                    </div>
                    <div class="card">
                        <div class="card-title">Schlagwörter</div>
                        <div style="margin-top:0.5rem;display:flex;flex-wrap:wrap;gap:0.3rem">${kws || '<span style="color:var(--clr-ink-muted)">Keine</span>'}</div>
                    </div>
                    <div class="card">
                        <div class="card-title">Erkannte Entitäten</div>
                        <div style="margin-top:0.5rem;font-size:0.9rem">
                            <div style="margin-bottom:0.4rem"><strong>Personen:</strong> ${people}</div>
                            <div style="margin-bottom:0.4rem"><strong>Firmen:</strong> ${companies}</div>
                            <div style="margin-bottom:0.4rem"><strong>Vereine:</strong> ${clubs}</div>
                            <div><strong>Orte:</strong> ${locations}</div>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-title">Ähnliche Artikel</div>
                        <div style="margin-top:0.5rem">${simHtml}</div>
                    </div>
                    ${a.pdf_url ? `<div class="card"><a href="${a.pdf_url}" target="_blank" class="btn btn-secondary" style="width:100%;justify-content:center">📥 Original-PDF öffnen</a></div>` : ''}
                </div>
            </div>
        `;
    } catch (e) {
        wrap.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><h3>Artikel nicht gefunden</h3></div>';
    }
}


// ============================================================
//  DASHBOARD PAGE
// ============================================================
async function initDashboard() {
    const wrap = qs('#dashboard-content');
    if (!wrap) return;

    wrap.innerHTML = '<div style="padding:3rem;text-align:center"><div class="spinner"></div></div>';

    try {
        const d = await apiFetch('/api/dashboard');

        // Stats cards
        const statsHtml = `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">${d.total_issues || 0}</div>
                    <div class="stat-label">Ausgaben</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${d.total_articles || 0}</div>
                    <div class="stat-label">Artikel</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${d.processed_issues || 0}</div>
                    <div class="stat-label">Verarbeitet</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${d.unreviewed_articles || 0}</div>
                    <div class="stat-label">Ungeprüft</div>
                </div>
            </div>
        `;

        // Bar charts
        function barChart(title, data, maxBars = 10) {
            if (!data || !Object.keys(data).length) return `<div class="chart-card"><div class="chart-title">${title}</div><p style="color:var(--clr-ink-muted);font-size:0.9rem">Noch keine Daten.</p></div>`;
            const entries = Object.entries(data).sort((a, b) => b[1] - a[1]).slice(0, maxBars);
            const max = Math.max(...entries.map(e => e[1]), 1);
            const bars = entries.map(([label, val]) => `
                <div class="bar-row">
                    <div class="bar-label" title="${label}">${label}</div>
                    <div class="bar-track"><div class="bar-fill" style="width:${(val / max * 100).toFixed(1)}%"></div></div>
                    <div class="bar-value">${val}</div>
                </div>
            `).join('');
            return `<div class="chart-card"><div class="chart-title">${title}</div><div class="bar-chart">${bars}</div></div>`;
        }

        const chartsHtml = `
            <div class="charts-grid">
                ${barChart('Artikel pro Kategorie', d.articles_per_category)}
                ${barChart('Artikel pro Gemeinde', d.articles_per_gemeinde)}
                ${barChart('Artikel pro Jahr', d.articles_per_year)}
                ${barChart('Häufigste Schlagwörter', d.top_keywords, 12)}
            </div>
        `;

        // Recent issues
        const recentHtml = (d.recent_issues || []).length ? `
            <div class="card" style="margin-bottom:1.5rem">
                <div class="card-title">Zuletzt verarbeitete Ausgaben</div>
                <div style="margin-top:0.75rem">
                    ${d.recent_issues.map(i => `
                        <div style="display:flex;justify-content:space-between;padding:0.4rem 0;border-bottom:1px solid var(--clr-border-light);font-size:0.9rem">
                            <span>${i.title || 'Ausgabe'} <span class="tag tag-gemeinde">${i.gemeinde || ''}</span></span>
                            <span style="color:var(--clr-ink-muted)">${formatDate(i.processed_at || i.download_date)}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        ` : '';

        wrap.innerHTML = statsHtml + chartsHtml + recentHtml;
    } catch (e) {
        wrap.innerHTML = '<div class="empty-state"><div class="empty-icon">📊</div><h3>Dashboard konnte nicht geladen werden</h3><p>Starte den Server und scanne zuerst einige Ausgaben.</p></div>';
    }
}


// ============================================================
//  ADMIN PAGE
// ============================================================
async function initAdmin() {
    const wrap = qs('#admin-content');
    if (!wrap) return;

    // === Action Buttons ===
    qs('#btn-scan')?.addEventListener('click', async () => {
        showToast('Scan wird gestartet…', 'info');
        try {
            const r = await apiFetch('/api/scan', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
            showToast(r.message || 'Scan gestartet', 'success');
            setTimeout(loadIssues, 3000);
        } catch (e) {}
    });

    qs('#btn-process-all')?.addEventListener('click', async () => {
        showToast('Verarbeitung aller Ausgaben gestartet…', 'info');
        try {
            const r = await apiFetch('/api/process-all', { method: 'POST' });
            showToast(r.message || 'Verarbeitung läuft', 'success');
        } catch (e) {}
    });

    qs('#btn-similarity')?.addEventListener('click', async () => {
        showToast('Ähnlichkeitsberechnung gestartet…', 'info');
        try {
            const r = await apiFetch('/api/compute-similarities', { method: 'POST' });
            showToast(r.message || 'Berechnung läuft', 'success');
        } catch (e) {}
    });

    // === Upload ===
    const uploadArea = qs('#upload-area');
    const uploadInput = qs('#upload-input');
    if (uploadArea && uploadInput) {
        uploadArea.addEventListener('click', () => uploadInput.click());
        uploadArea.addEventListener('dragover', e => { e.preventDefault(); uploadArea.classList.add('drag-over'); });
        uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('drag-over'));
        uploadArea.addEventListener('drop', e => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            if (e.dataTransfer.files.length) handleUpload(e.dataTransfer.files[0]);
        });
        uploadInput.addEventListener('change', e => {
            if (e.target.files.length) handleUpload(e.target.files[0]);
        });
    }

    async function handleUpload(file) {
        if (!file.name.endsWith('.pdf')) {
            showToast('Bitte nur PDF-Dateien hochladen.', 'error');
            return;
        }
        const gemeinde = qs('#upload-gemeinde')?.value || '';
        const saison = qs('#upload-saison')?.value || '';
        const jahr = qs('#upload-jahr')?.value || '';

        const fd = new FormData();
        fd.append('file', file);
        if (gemeinde) fd.append('gemeinde', gemeinde);
        if (saison) fd.append('saison', saison);
        if (jahr) fd.append('jahr', jahr);

        showToast(`Lade "${file.name}" hoch…`, 'info');
        try {
            const r = await apiFetch('/api/upload', { method: 'POST', body: fd });
            showToast(r.message || 'Upload erfolgreich', 'success');
            loadIssues();
        } catch (e) {}
    }

    // === Issues Table ===
    async function loadIssues() {
        const tbody = qs('#issues-tbody');
        if (!tbody) return;
        try {
            const issues = await apiFetch('/api/issues');
            if (!issues.length) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:2rem;color:var(--clr-ink-muted)">Noch keine Ausgaben. Starte einen Scan oder lade eine PDF hoch.</td></tr>';
                return;
            }
            tbody.innerHTML = issues.map(i => `
                <tr>
                    <td><strong>${i.title || '–'}</strong></td>
                    <td>${i.gemeinde || '–'}</td>
                    <td>${i.saison || ''} ${i.jahr || ''}</td>
                    <td>${statusBadge(i.status)}</td>
                    <td>${i.article_count || 0}</td>
                    <td>${formatDate(i.download_date)}</td>
                    <td>
                        <button class="btn btn-sm btn-secondary" onclick="processIssue(${i.id})">Verarbeiten</button>
                        ${i.pdf_url ? `<a href="${i.pdf_url}" target="_blank" class="btn btn-sm btn-secondary">PDF</a>` : ''}
                    </td>
                </tr>
            `).join('');
        } catch (e) {
            tbody.innerHTML = '<tr><td colspan="7">Fehler beim Laden</td></tr>';
        }
    }

    window.processIssue = async function(id) {
        showToast('Verarbeitung gestartet…', 'info');
        try {
            const r = await apiFetch(`/api/process/${id}`, { method: 'POST' });
            showToast(r.message || 'Verarbeitung läuft', 'success');
            setTimeout(loadIssues, 5000);
        } catch (e) {}
    };

    // === Articles Management ===
    async function loadArticlesAdmin() {
        const tbody = qs('#articles-admin-tbody');
        if (!tbody) return;
        try {
            const data = await apiFetch('/api/articles?limit=100');
            const articles = data.articles || data;
            if (!articles.length) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:2rem;color:var(--clr-ink-muted)">Noch keine Artikel.</td></tr>';
                return;
            }
            tbody.innerHTML = articles.map(a => `
                <tr>
                    <td><a href="/article/${a.id}">${truncate(a.title || 'Ohne Titel', 50)}</a></td>
                    <td>${a.gemeinde || '–'}</td>
                    <td>${(a.categories || []).map(c => `<span class="tag tag-category">${c}</span>`).join(' ') || '–'}</td>
                    <td>${typeBadge(a.article_type)}</td>
                    <td><span class="status-badge ${a.status === 'manuell geprüft' ? 'status-verarbeitet' : 'status-neu'}">${a.status || 'erkannt'}</span></td>
                    <td>
                        <button class="btn btn-sm btn-secondary" onclick="editArticle(${a.id})">✏️</button>
                        <button class="btn btn-sm btn-secondary" onclick="deleteArticle(${a.id})" style="color:var(--clr-accent)">🗑️</button>
                    </td>
                </tr>
            `).join('');
        } catch (e) {}
    }

    window.editArticle = async function(id) {
        try {
            const a = await apiFetch(`/api/articles/${id}`);
            qs('#edit-id').value = a.id;
            qs('#edit-title').value = a.title || '';
            qs('#edit-summary').value = a.summary || '';
            qs('#edit-gemeinde').value = a.gemeinde || '';
            qs('#edit-saison').value = a.saison || '';
            qs('#edit-jahr').value = a.jahr || '';
            qs('#edit-type').value = a.content_type || a.article_type || 'redaktionell';
            qs('#edit-status').value = a.status || 'automatisch erkannt';
            qs('#edit-keywords').value = (a.keywords || []).join(', ');
            qs('#edit-modal').classList.add('active');
        } catch (e) {}
    };

    qs('#edit-modal .modal-close')?.addEventListener('click', () => qs('#edit-modal').classList.remove('active'));
    qs('#edit-form')?.addEventListener('submit', async e => {
        e.preventDefault();
        const id = qs('#edit-id').value;
        const payload = {
            title: qs('#edit-title').value,
            summary: qs('#edit-summary').value,
            gemeinde: qs('#edit-gemeinde').value,
            saison: qs('#edit-saison').value,
            jahr: parseInt(qs('#edit-jahr').value) || null,
            article_type: qs('#edit-type').value,
            content_type: qs('#edit-type').value,
            status: qs('#edit-status').value,
            keywords: qs('#edit-keywords').value.split(',').map(k => k.trim()).filter(Boolean)
        };
        try {
            await apiFetch(`/api/articles/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            showToast('Artikel gespeichert', 'success');
            qs('#edit-modal').classList.remove('active');
            loadArticlesAdmin();
        } catch (e) {}
    });

    window.deleteArticle = async function(id) {
        if (!confirm('Artikel wirklich löschen?')) return;
        try {
            await apiFetch(`/api/articles/${id}`, { method: 'DELETE' });
            showToast('Artikel gelöscht', 'success');
            loadArticlesAdmin();
        } catch (e) {}
    };

    // === Logs ===
    async function loadLogs() {
        const logList = qs('#log-list');
        if (!logList) return;
        try {
            const logs = await apiFetch('/api/logs?limit=50');
            if (!logs.length) {
                logList.innerHTML = '<div style="padding:1rem;color:var(--clr-ink-muted);font-size:0.9rem">Noch keine Logs.</div>';
                return;
            }
            logList.innerHTML = logs.map(l => `
                <div class="log-entry">
                    <span class="log-time">${formatDate(l.timestamp)}</span>
                    <span class="log-msg ${l.level === 'error' ? 'log-error' : l.level === 'success' ? 'log-success' : ''}">${l.message}</span>
                </div>
            `).join('');
        } catch (e) {}
    }

    // Initial load
    loadIssues();
    loadArticlesAdmin();
    loadLogs();

    // Auto-refresh
    setInterval(() => { loadIssues(); loadLogs(); }, 15000);
}
