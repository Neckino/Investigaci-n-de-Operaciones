/* dashboard.js — Panel de resultados y sidebar de nodos para OptiNet */

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
window.Sidebar = (() => {

  let currentData = null

  function render(data) {
    currentData = data
    renderPlantas(data.plantas)
    renderCentros(data.centros)
    renderClientes(data.clientes)
    renderParams(data)
  }

  function renderPlantas(plantas) {
    const container = document.getElementById('plantas-list')
    if (!container) return
    container.innerHTML = plantas.map(p => `
      <div class="node-card" data-id="${p.id}" onclick="Sidebar.selectNode('${p.id}', ${JSON.stringify(p)}, 'planta')">
        <div class="node-card-header">
          <span class="node-id">${p.id}</span>
          <span class="node-type-badge badge-planta">Planta</span>
        </div>
        <div class="node-fields">
          <div class="node-field">
            <span class="field-label">Oferta</span>
            <span class="field-value" id="val-${p.id}-oferta">${p.oferta} u.</span>
          </div>
        </div>
      </div>
    `).join('')
  }

  function renderCentros(centros) {
    const container = document.getElementById('centros-list')
    if (!container) return
    container.innerHTML = centros.map(d => `
      <div class="node-card" data-id="${d.id}" onclick="Sidebar.selectNode('${d.id}', ${JSON.stringify(d)}, 'centro')">
        <div class="node-card-header">
          <span class="node-id">${d.id}</span>
          <span class="node-type-badge badge-centro">CD</span>
        </div>
        <div class="node-fields">
          <div class="node-field">
            <span class="field-label">Capacidad</span>
            <span class="field-value" id="val-${d.id}-capacidad">${d.capacidad} u.</span>
          </div>
          <div class="node-field">
            <span class="field-label">Costo fijo</span>
            <span class="field-value" id="val-${d.id}-costo_fijo">$${d.costo_fijo.toLocaleString()}</span>
          </div>
        </div>
      </div>
    `).join('')
  }

  function renderClientes(clientes) {
    const container = document.getElementById('clientes-list')
    if (!container) return
    container.innerHTML = clientes.map(c => `
      <div class="node-card" data-id="${c.id}" onclick="Sidebar.selectNode('${c.id}', ${JSON.stringify(c)}, 'cliente')">
        <div class="node-card-header">
          <span class="node-id">${c.id}</span>
          <span class="node-type-badge badge-cliente">Cliente</span>
        </div>
        <div class="node-fields">
          <div class="node-field">
            <span class="field-label">Demanda</span>
            <span class="field-value" id="val-${c.id}-demanda">${c.demanda} u.</span>
          </div>
          <div class="node-field">
            <span class="field-label">Penalización</span>
            <span class="field-value" id="val-${c.id}-penalizacion">$${c.penalizacion}/u.</span>
          </div>
        </div>
      </div>
    `).join('')
  }

  function renderParams(data) {
    const el = document.getElementById('param-max-rutas')
    if (el) el.value = data.max_rutas_activas ?? 8
  }

  function selectNode(id, nodeData, group) {
    // Highlight card
    document.querySelectorAll('.node-card').forEach(c => c.classList.remove('selected'))
    const card = document.querySelector(`.node-card[data-id="${id}"]`)
    if (card) {
      card.classList.add('selected')
      card.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
    // Show edit panel
    renderEditPanel(id, nodeData, group)
  }

  function renderEditPanel(id, data, group) {
    const panel = document.getElementById('edit-panel')
    if (!panel) return

    const fields = getFields(group, data)
    panel.innerHTML = `
      <div class="desglose-title" style="padding:12px 16px 8px; border-bottom:1px solid var(--border)">
        Editar ${id}
      </div>
      <div style="padding:12px 16px; display:flex; flex-direction:column; gap:8px;">
        ${fields.map(f => `
          <div class="node-field">
            <span class="field-label">${f.label}</span>
            <input class="field-input" type="number" step="${f.step || 1}" min="0"
              value="${data[f.key]}"
              onchange="Sidebar.updateField('${id}', '${f.key}', this.value)"
            >
          </div>
        `).join('')}
        <button class="btn btn-primary" style="margin-top:4px; width:100%; justify-content:center"
          onclick="Sidebar.saveNode('${id}', '${group}')">
          Guardar cambios
        </button>
      </div>
    `
    panel.style.display = 'block'
  }

  function getFields(group, data) {
    if (group === 'planta')  return [{ key: 'oferta',        label: 'Oferta (u.)',      step: 1 }]
    if (group === 'centro')  return [
      { key: 'capacidad',   label: 'Capacidad (u.)',  step: 1 },
      { key: 'costo_fijo',  label: 'Costo fijo ($)',  step: 100 },
    ]
    if (group === 'cliente') return [
      { key: 'demanda',      label: 'Demanda (u.)',    step: 1 },
      { key: 'penalizacion', label: 'Penalización ($/u.)', step: 1 },
    ]
    return []
  }

  const pendingEdits = {}

  function updateField(id, key, value) {
    if (!pendingEdits[id]) pendingEdits[id] = {}
    pendingEdits[id][key] = parseFloat(value)
  }

  async function saveNode(id, group) {
    if (!pendingEdits[id]) return
    try {
      const res = await fetch('/api/nodes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, group, changes: pendingEdits[id] })
      })
      if (!res.ok) throw new Error('Error al guardar')
      const updated = await res.json()
      toast('Nodo actualizado. Resuelve de nuevo para ver el efecto.', 'success')
      delete pendingEdits[id]
      // Refresh sidebar data
      window.APP && window.APP.loadData()
      Dashboard.clearResults()
    } catch (e) {
      toast('Error al guardar cambios', 'error')
    }
  }

  function clearSelection() {
    document.querySelectorAll('.node-card').forEach(c => c.classList.remove('selected'))
    const panel = document.getElementById('edit-panel')
    if (panel) panel.style.display = 'none'
  }

  return { render, selectNode, updateField, saveNode, clearSelection }
})()


/* ── Dashboard (panel de resultados) ─────────────────────────────────────── */
window.Dashboard = (() => {

  function showEmpty() {
    document.getElementById('results-empty').style.display    = 'flex'
    document.getElementById('results-content').style.display  = 'none'
    document.getElementById('results-state').textContent      = 'Sin resolver'
    document.getElementById('results-state').className        = 'results-state empty'
  }

  function clearResults() {
    showEmpty()
    window.Editor && window.Editor.resetVisual()
  }

  function render(sol) {
    if (!sol.factible) {
      document.getElementById('results-state').textContent = 'Infactible'
      document.getElementById('results-state').className   = 'results-state infeasible'
      document.getElementById('results-empty').style.display   = 'flex'
      document.getElementById('results-content').style.display = 'none'
      document.getElementById('results-empty').innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <p>Sin solución factible.<br>Revisa los parámetros de la red.</p>
      `
      return
    }

    document.getElementById('results-empty').style.display   = 'none'
    document.getElementById('results-content').style.display = 'block'
    document.getElementById('results-state').textContent     = sol.estado
    document.getElementById('results-state').className       = 'results-state optimal'

    renderCostHero(sol)
    renderKPIs(sol)
    renderDesglose(sol)
    renderFlujos(sol)
    renderClientes(sol)
  }

  function renderCostHero(sol) {
    const el = document.getElementById('cost-value')
    if (!el) return
    const formatted = sol.costo_total.toLocaleString('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    el.innerHTML = `<span class="cost-prefix">$</span>${formatted}`
  }

  function renderKPIs(sol) {
    const d        = sol.desglose
    const deficit  = sol.deficit || {}
    const totalDef = Object.values(deficit).reduce((a, b) => a + b, 0)
    const nRutas   = (sol.rutas_directas?.length || 0) + (sol.rutas_cd?.length || 0)

    setKPI('kpi-fijos',    `$${d.costos_fijos.toLocaleString()}`,    d.costos_fijos > 0 ? 'warning' : '')
    setKPI('kpi-penaliz',  `$${d.penalizaciones.toLocaleString()}`,  d.penalizaciones > 0 ? 'danger' : 'success')
    setKPI('kpi-centros',  `${sol.centros_abiertos?.length || 0} / 2`, '')
    setKPI('kpi-rutas',    `${nRutas} / 8`,                          nRutas >= 8 ? 'warning' : '')
    setKPI('kpi-deficit',  `${totalDef.toFixed(0)} u.`,              totalDef > 0 ? 'danger' : 'success')
    setKPI('kpi-gap',      `${(475 - 400)} u.`,                      'warning')
  }

  function setKPI(id, value, cls) {
    const el = document.getElementById(id)
    if (!el) return
    el.textContent = value
    el.className = `kpi-val ${cls || ''}`
  }

  function renderDesglose(sol) {
    const d    = sol.desglose
    const total = sol.costo_total || 1
    const items = [
      { label: 'Costos fijos',    val: d.costos_fijos,          color: '#F59E0B' },
      { label: 'P → C directo',   val: d.transporte_directo,    color: '#3B82F6' },
      { label: 'P → CD',          val: d.transporte_planta_cd,  color: '#8B5CF6' },
      { label: 'CD → C',          val: d.transporte_cd_cliente, color: '#6366F1' },
      { label: 'Penalizaciones',  val: d.penalizaciones,        color: '#EF4444' },
    ]

    const container = document.getElementById('desglose-rows')
    if (!container) return
    container.innerHTML = items.map(item => {
      const pct = Math.round((item.val / total) * 100)
      return `
        <div class="desglose-row">
          <span class="desglose-label">${item.label}</span>
          <div class="desglose-bar-wrap">
            <div class="desglose-bar-bg">
              <div class="desglose-bar-fill" style="width:${pct}%; background:${item.color}"></div>
            </div>
            <span class="desglose-val">$${item.val.toLocaleString()}</span>
          </div>
        </div>
      `
    }).join('')
  }

  function renderFlujos(sol) {
    const container = document.getElementById('flujos-rows')
    if (!container) return

    const rows = []

    Object.entries(sol.flujo_directo || {}).forEach(([key, v]) => {
      const [p, c] = parseKey(key)
      rows.push({ from: p, to: c, amount: v, type: 'directo' })
    })
    Object.entries(sol.flujo_planta_cd || {}).forEach(([key, v]) => {
      const [p, d] = parseKey(key)
      rows.push({ from: p, to: d, amount: v, type: 'P→CD' })
    })
    Object.entries(sol.flujo_cd_cliente || {}).forEach(([key, v]) => {
      const [d, c] = parseKey(key)
      rows.push({ from: d, to: c, amount: v, type: 'CD→C' })
    })

    container.innerHTML = rows.length
      ? rows.map(r => `
          <div class="flujo-row">
            <span class="flujo-route">
              <span>${r.from}</span>
              <span class="flujo-arrow">→</span>
              <span>${r.to}</span>
            </span>
            <span class="flujo-amount">${r.amount.toFixed(0)} u.</span>
          </div>
        `).join('')
      : '<span style="color:var(--text-3);font-size:11px">Sin flujos activos</span>'
  }

  function renderClientes(sol) {
    const deficit = sol.deficit || {}
    const container = document.getElementById('clientes-bars')
    if (!container) return

    // Reconstruir demandas desde los flujos
    const received = {}
    Object.entries(sol.flujo_directo || {}).forEach(([key, v]) => {
      const [, c] = parseKey(key)
      received[c] = (received[c] || 0) + v
    })
    Object.entries(sol.flujo_cd_cliente || {}).forEach(([key, v]) => {
      const [, c] = parseKey(key)
      received[c] = (received[c] || 0) + v
    })

    const clienteIds = [...new Set([
      ...Object.keys(received),
      ...Object.keys(deficit)
    ])].sort()

    container.innerHTML = clienteIds.map(cid => {
      const def   = deficit[cid] || 0
      const rec   = received[cid] || 0
      const dem   = rec + def
      const pct   = dem > 0 ? Math.round((rec / dem) * 100) : 100
      const defPct = dem > 0 ? Math.round((def / dem) * 100) : 0

      return `
        <div class="cliente-row">
          <span class="cliente-id">${cid}</span>
          <div class="cliente-bar-wrap">
            <div class="cliente-bar-bg"></div>
            <div class="cliente-bar-fill"  style="width:${pct}%"></div>
            <div class="cliente-bar-deficit" style="left:${pct}%; width:${defPct}%"></div>
          </div>
          <span class="cliente-pct ${def > 0 ? 'danger' : ''}">${pct}%</span>
        </div>
      `
    }).join('')
  }

  /* ── Util ────────────────────────────────────────────────────────────────── */
  function parseKey(raw) {
    return raw.replace(/[()' ]/g, '').split(',')
  }

  return { render, showEmpty, clearResults }
})()


/* ── Toast notifications ─────────────────────────────────────────────────── */
window.toast = function(msg, type = '') {
  const container = document.getElementById('toast-container')
  if (!container) return
  const t = document.createElement('div')
  t.className = `toast ${type}`
  t.textContent = msg
  container.appendChild(t)
  setTimeout(() => t.remove(), 3200)
}


/* ── Status bar ──────────────────────────────────────────────────────────── */
window.setStatus = function(state, msg) {
  const dot  = document.getElementById('status-dot')
  const text = document.getElementById('status-text')
  if (dot)  dot.className  = `status-dot ${state}`
  if (text) text.textContent = msg
}


/* ── Accordion sidebar sections ──────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.sidebar-section-header').forEach(header => {
    header.addEventListener('click', () => {
      const body    = header.nextElementSibling
      const chevron = header.querySelector('.chevron')
      const isOpen  = body.classList.contains('open')
      body.classList.toggle('open', !isOpen)
      if (chevron) chevron.classList.toggle('open', !isOpen)
    })
  })

  // Abrir la primera sección por defecto
  const first = document.querySelector('.sidebar-section-body')
  if (first) {
    first.classList.add('open')
    const ch = first.previousElementSibling?.querySelector('.chevron')
    if (ch) ch.classList.add('open')
  }
})
