/* editor.js — vis.js network editor para OptiNet */
/* Depende de: vis-network (CDN), dashboard.js, state global window.APP */

window.Editor = (() => {

  /* ── Estado local ──────────────────────────────────────────────────────── */
  let network = null
  let nodesDS = null
  let edgesDS = null
  let lastSolution = null
  const selectedNode = { id: null }

  /* ── Paleta con alto contraste ─────────────────────────────────────────── */
  const COLOR = {
    planta:       { bg: '#3B1F6E', border: '#A78BFA', text: '#EDE9FE' },  // violeta
    cliente:      { bg: '#14532D', border: '#4ADE80', text: '#DCFCE7' },
    cliente_def:  { bg: '#7F1D1D', border: '#F87171', text: '#FEE2E2' },
    centro_open:  { bg: '#78350F', border: '#FCD34D', text: '#FEF3C7' },
    centro_close: { bg: '#1C2128', border: '#6E7681', text: '#8B949E' },
    edge_active:  '#60A5FA',
    edge_cd:      '#FCD34D',
    edge_inactive:'#3D444D',
  }

  /* ── Helper: convierte string HTML en elemento DOM para tooltips ─────────── */
  function htmlTip(html) {
    const div = document.createElement('div')
    div.innerHTML = html
    return div
  }

  /* ── vis.js options — física OFF, layout en cascada manual ──────────────── */
  const NETWORK_OPTIONS = {
    physics: { enabled: false },
    nodes: {
      shape: 'box',
      widthConstraint: { minimum: 72, maximum: 88 },
      heightConstraint: { minimum: 38 },
      margin: { top: 9, right: 14, bottom: 9, left: 14 },
      font: {
        face: 'JetBrains Mono, monospace',
        size: 13,
        color: '#E6EDF3',
        bold: false,
        multi: false,
      },
      borderWidth: 2,
      borderWidthSelected: 3,
      shadow: false,
      shapeProperties: { borderRadius: 6 },
    },
    edges: {
      width: 1.8,
      smooth: { enabled: true, type: 'cubicBezier', forceDirection: 'horizontal', roundness: 0.4 },
      arrows: { to: { enabled: true, scaleFactor: 0.55 } },
      font: {
        face: 'JetBrains Mono, monospace',
        size: 11,
        color: '#CDD9E5',
        background: '#1C2128',
        strokeWidth: 2,
        strokeColor: '#1C2128',
        align: 'middle',
      },
      selectionWidth: 2.5,
    },
    interaction: {
      hover: true,
      tooltipDelay: 150,
      hideEdgesOnDrag: false,
      multiselect: false,
      selectConnectedEdges: true,
    },
    layout: { hierarchical: false },
  }

  /* ── Construir nodos vis con layout en cascada (Plantas → CD → Clientes) ── */
  function buildNodes(data) {
    const nodes = []

    // Columnas X fijas: Plantas | CD | Clientes
    const COL = { planta: -500, cd: 0, cliente: 500 }
    const GAP = 140  // espaciado vertical entre nodos

    // Centrar verticalmente cada columna
    const centerY = (count) => (idx) => (idx - (count - 1) / 2) * GAP

    const yPlanta  = centerY(data.plantas.length)
    const yCentro  = centerY(data.centros.length)
    const yCliente = centerY(data.clientes.length)

    data.plantas.forEach((p, i) => nodes.push({
      id: p.id,
      label: `${p.id}\n${p.oferta}u`,
      title: htmlTip(`<b>Planta ${p.id}</b><br>Oferta: <b>${p.oferta} u.</b>`),
      group: 'planta',
      color: {
        background: COLOR.planta.bg,
        border: COLOR.planta.border,
        highlight: { background: '#5B21B6', border: '#C4B5FD' },
        hover: { background: '#4C1D95', border: '#C4B5FD' },
      },
      font: { color: COLOR.planta.text, multi: false },
      x: COL.planta, y: yPlanta(i),
      fixed: { x: true, y: true },
      _data: p,
    }))

    data.centros.forEach((d, i) => nodes.push({
      id: d.id,
      label: `${d.id}\n$${d.costo_fijo.toLocaleString()}`,
      title: htmlTip(`<b>Centro ${d.id}</b><br>Cap: <b>${d.capacidad} u.</b><br>Fijo: <b>$${d.costo_fijo.toLocaleString()}</b>`),
      group: 'centro',
      shape: 'box',
      color: {
        background: COLOR.centro_close.bg,
        border: COLOR.centro_close.border,
        highlight: { background: '#2D333B', border: '#9CA3AF' },
        hover: { background: '#2D333B', border: '#9CA3AF' },
      },
      font: { color: COLOR.centro_close.text, multi: false },
      x: COL.cd, y: yCentro(i),
      fixed: { x: true, y: true },
      _data: d,
    }))

    data.clientes.forEach((c, i) => nodes.push({
      id: c.id,
      label: `${c.id}\n${c.demanda}u`,
      title: htmlTip(`<b>Cliente ${c.id}</b><br>Demanda: <b>${c.demanda} u.</b><br>Penaliz: <b>$${c.penalizacion}/u.</b>`),
      group: 'cliente',
      color: {
        background: COLOR.cliente.bg,
        border: COLOR.cliente.border,
        highlight: { background: '#16A34A', border: '#86EFAC' },
        hover: { background: '#166534', border: '#86EFAC' },
      },
      font: { color: COLOR.cliente.text, multi: false },
      x: COL.cliente, y: yCliente(i),
      fixed: { x: true, y: true },
      _data: c,
    }))

    return nodes
  }

  /* ── Curvatura individual: evita que aristas con mismo origen/destino se solapen ── */
  function edgeSmooth(fromId, toId, allEdges) {
    // Contar cuántas aristas comparten el mismo par from→to o cruzan el mismo tramo
    const sameTarget = allEdges.filter(e => e.to === toId && e.from !== fromId).length
    const sameSource = allEdges.filter(e => e.from === fromId && e.to !== toId).length
    // Extraer índice numérico del nodo (P1→1, C3→3, CD2→2)
    const fi = parseInt(fromId.replace(/\D/g, '')) || 0
    const ti = parseInt(toId.replace(/\D/g, '')) || 0
    // Roundness escalonado según diferencia de índices — spread entre -0.6 y 0.6
    const spread = 0.25
    const steps  = Math.max(sameTarget, sameSource, 1)
    const base   = (fi - ti) / Math.max(fi + ti, 1)
    return Math.max(-0.7, Math.min(0.7, base * spread * steps))
  }

  /* ── Construir aristas con colores contrastados ─────────────────────────── */
  function buildEdges(data) {
    const edges = []
    let eid = 0

    // Pre-coleccionar pares para calcular curvatura relativa
    const dirPairs  = Object.keys(data.costos_planta_cliente).map(k => {
      const [p, c] = k.replace(/[()' ]/g, '').split(',')
      return { from: p, to: c }
    })
    const pcdPairs  = Object.keys(data.costos_planta_cd).map(k => {
      const [p, d] = k.replace(/[()' ]/g, '').split(',')
      return { from: p, to: d }
    })
    const cdcPairs  = Object.keys(data.costos_cd_cliente).map(k => {
      const [d, c] = k.replace(/[()' ]/g, '').split(',')
      return { from: d, to: c }
    })

    // Planta → Cliente (directas) — línea continua azul
    Object.entries(data.costos_planta_cliente).forEach(([key, cost]) => {
      const [p, c] = key.replace('(', '').replace(')', '').split(', ').map(s => s.replace(/'/g, '').trim())
      const r = edgeSmooth(p, c, dirPairs)
      edges.push({
        id: `dir_${eid++}`,
        from: p, to: c,
        label: '',
        title: `$${cost}`,
        smooth: { enabled: true, type: 'curvedCW', roundness: r },
        color: { color: COLOR.edge_inactive, highlight: COLOR.edge_active, hover: '#5E6E80', opacity: 0.35 },
        width: 1,
        dashes: false,
        font: { color: '#8B949E', background: '#161B22', size: 10, strokeWidth: 2, strokeColor: '#161B22' },
        _type: 'direct', _cost: cost, _key: `${p}_${c}`,
      })
    })

    // Planta → CD — línea punteada
    Object.entries(data.costos_planta_cd).forEach(([key, cost]) => {
      const [p, d] = key.replace('(', '').replace(')', '').split(', ').map(s => s.replace(/'/g, '').trim())
      const r = edgeSmooth(p, d, pcdPairs)
      edges.push({
        id: `pcd_${eid++}`,
        from: p, to: d,
        label: '',
        title: `$${cost}`,
        smooth: { enabled: true, type: 'curvedCW', roundness: r },
        color: { color: '#3A3020', highlight: COLOR.edge_cd, hover: '#5E5030', opacity: 0.35 },
        width: 1,
        dashes: [6, 4],
        font: { color: '#8B949E', background: '#161B22', size: 10, strokeWidth: 2, strokeColor: '#161B22' },
        _type: 'planta_cd', _cost: cost, _key: `${p}_${d}`,
      })
    })

    // CD → Cliente
    Object.entries(data.costos_cd_cliente).forEach(([key, cost]) => {
      const [d, c] = key.replace('(', '').replace(')', '').split(', ').map(s => s.replace(/'/g, '').trim())
      const r = edgeSmooth(d, c, cdcPairs)
      edges.push({
        id: `cdc_${eid++}`,
        from: d, to: c,
        label: '',
        title: `$${cost}`,
        smooth: { enabled: true, type: 'curvedCW', roundness: r },
        color: { color: '#2E2818', highlight: COLOR.edge_cd, hover: '#4A3F28', opacity: 0.35 },
        width: 1,
        dashes: [2, 5],
        font: { color: '#8B949E', background: '#161B22', size: 10, strokeWidth: 2, strokeColor: '#161B22' },
        _type: 'cd_cliente', _cost: cost, _key: `${d}_${c}`,
      })
    })

    return edges
  }

  /* ── Parsear clave de la API Python: "('P1', 'C1')" → "P1_C1" ──────────── */
  function parseKey(raw) {
    return raw.replace(/[()' ]/g, '').split(',').join('_')
  }

  /* ── Aplicar solución sobre la red ──────────────────────────────────────── */
  function applySolution(sol) {
    if (!network || !sol.factible) return
    lastSolution = sol

    const activeDir = new Set(Object.keys(sol.flujo_directo).map(parseKey))
    const activePCD = new Set(Object.keys(sol.flujo_planta_cd).map(parseKey))
    const activeCDC = new Set(Object.keys(sol.flujo_cd_cliente).map(parseKey))
    const abiertos  = new Set(sol.centros_abiertos)
    const deficit   = sol.deficit || {}

    const maxFlujo = Math.max(
      ...Object.values(sol.flujo_directo),
      ...Object.values(sol.flujo_planta_cd),
      ...Object.values(sol.flujo_cd_cliente),
      1
    )

    // Actualizar nodos
    nodesDS.forEach(node => {
      const updates = { id: node.id }

      if (node.group === 'centro') {
        const open = abiertos.has(node.id)
        updates.color = open
          ? { background: COLOR.centro_open.bg, border: COLOR.centro_open.border,
              highlight: { background: '#92400E', border: '#FDE68A' },
              hover: { background: '#92400E', border: '#FDE68A' } }
          : { background: COLOR.centro_close.bg, border: COLOR.centro_close.border,
              highlight: { background: '#2D333B', border: '#9CA3AF' } }
        updates.font = { color: open ? COLOR.centro_open.text : COLOR.centro_close.text }
        updates.label = `${node.id}\n${open ? '✓ Abierto' : '✗ Cerrado'}`
        updates.title = htmlTip(`<b>Centro ${node.id}</b><br>Cap: <b>${node._data.capacidad} u.</b><br>Fijo: <b>$${node._data.costo_fijo.toLocaleString()}</b><br>${open ? '✓ Abierto' : '✗ Cerrado'}`)
      }

      if (node.group === 'cliente') {
        const def = deficit[node.id] || 0
        const hasDeficit = def > 0
        const dem = node._data.demanda
        const rec = dem - def
        const pct = Math.round((rec / dem) * 100)
        updates.color = hasDeficit
          ? { background: COLOR.cliente_def.bg, border: COLOR.cliente_def.border,
              highlight: { background: '#991B1B', border: '#FCA5A5' },
              hover: { background: '#991B1B', border: '#FCA5A5' } }
          : { background: COLOR.cliente.bg, border: COLOR.cliente.border,
              highlight: { background: '#15803D', border: '#86EFAC' } }
        updates.font = { color: hasDeficit ? COLOR.cliente_def.text : COLOR.cliente.text }
        updates.label = `${node.id}\n${pct}% ✓`
        if (hasDeficit) updates.label = `${node.id}\n${pct}% ⚠`
        updates.title = htmlTip(`<b>Cliente ${node.id}</b><br>Demanda: <b>${dem} u.</b><br>Recibido: <b>${rec} u.</b>${hasDeficit ? `<br>⚠ Déficit: <b>${def} u.</b>` : '<br>✓ Satisfecho'}`)
      }

      nodesDS.update(updates)
    })

    // Actualizar aristas
    edgesDS.forEach(edge => {
      let active = false
      let flujo = 0
      let accentColor = COLOR.edge_active

      if (edge._type === 'direct') {
        active = activeDir.has(edge._key)
        flujo  = sol.flujo_directo[`('${edge.from}', '${edge.to}')`] || 0
        accentColor = COLOR.edge_active          // azul claro
      } else if (edge._type === 'planta_cd') {
        active = activePCD.has(edge._key)
        flujo  = sol.flujo_planta_cd[`('${edge.from}', '${edge.to}')`] || 0
        accentColor = COLOR.edge_cd              // ámbar
      } else if (edge._type === 'cd_cliente') {
        active = activeCDC.has(edge._key)
        flujo  = sol.flujo_cd_cliente[`('${edge.from}', '${edge.to}')`] || 0
        accentColor = COLOR.edge_cd              // ámbar
      }

      const w   = active ? Math.max(2.5, 2 + 5 * (flujo / maxFlujo)) : 1
      const lbl = active ? `${flujo.toFixed(0)}u` : ''
      const tip = active ? `${flujo.toFixed(0)} u.` : `$${edge._cost}`

      edgesDS.update({
        id: edge.id,
        width: w,
        label: lbl,
        title: tip,
        color: {
          color:     active ? accentColor : COLOR.edge_inactive,
          highlight: accentColor,
          hover:     active ? accentColor : '#5E6E80',
          opacity:   active ? 1.0 : 0.2,
        },
        font: {
          color:       active ? '#FFFFFF' : '#484F58',
          background:  active ? '#0D1117' : 'transparent',
          strokeWidth: active ? 3 : 0,
          strokeColor: '#0D1117',
          size:        active ? 13 : 10,
          bold:        active,
        },
      })
    })
  }

  /* ── Selección de nodo → sidebar ────────────────────────────────────────── */
  function onNodeSelect(params) {
    if (!params.nodes.length) {
      selectedNode.id = null
      window.Sidebar && window.Sidebar.clearSelection()
      return
    }
    const id = params.nodes[0]
    selectedNode.id = id
    const node = nodesDS.get(id)
    window.Sidebar && window.Sidebar.selectNode(id, node._data, node.group)
  }

  /* ── Reset a estado inicial (sin solución) ──────────────────────────────── */
  function resetVisual() {
    if (!network) return
    lastSolution = null
    centrosCerradosOcultos = false
    const btn = document.getElementById('btn-toggle-cd')
    if (btn) btn.classList.remove('active')

    nodesDS.forEach(node => {
      const updates = { id: node.id, hidden: false }
      if (node.group === 'planta') {
        updates.color = { background: COLOR.planta.bg, border: COLOR.planta.border,
          highlight: { background: '#5B21B6', border: '#C4B5FD' },
          hover: { background: '#4C1D95', border: '#C4B5FD' } }
        updates.font  = { color: COLOR.planta.text }
        updates.label = `${node.id}\n${node._data.oferta}u`
      }
      if (node.group === 'cliente') {
        updates.color = { background: COLOR.cliente.bg, border: COLOR.cliente.border }
        updates.font  = { color: COLOR.cliente.text }
        updates.label = `${node.id}\n${node._data.demanda}u`
      }
      if (node.group === 'centro') {
        updates.color = { background: COLOR.centro_close.bg, border: COLOR.centro_close.border }
        updates.font  = { color: COLOR.centro_close.text }
        updates.label = `${node.id}\n$${node._data.costo_fijo.toLocaleString()}`
      }
      nodesDS.update(updates)
    })

    edgesDS.forEach(edge => {
      edgesDS.update({
        id: edge.id,
        hidden: false,
        width: 1,
        label: '',
        title: `$${edge._cost}`,
        color: { color: COLOR.edge_inactive, opacity: 0.4 },
        font: { color: '#6E7681', size: 10, background: '#161B22', strokeWidth: 2, strokeColor: '#161B22', bold: false },
      })
    })
  }

  /* ── Init ───────────────────────────────────────────────────────────────── */
  function init(data) {
    const container = document.getElementById('network-canvas')
    const rawNodes  = buildNodes(data)
    const rawEdges  = buildEdges(data)

    nodesDS = new vis.DataSet(rawNodes)
    edgesDS = new vis.DataSet(rawEdges)

    network = new vis.Network(container, { nodes: nodesDS, edges: edgesDS }, NETWORK_OPTIONS)

    network.on('selectNode',   onNodeSelect)
    network.on('deselectNode', onNodeSelect)

    // Fit al canvas tras render inicial
    setTimeout(() => network.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } }), 100)

    return network
  }

  /* ── Toggle: ocultar/mostrar centros cerrados y sus aristas ────────────── */
  let centrosCerradosOcultos = false

  function toggleCentrosCerrados() {
    if (!network) return

    // Determinar qué centros están cerrados (sin solución = todos; con solución = los no abiertos)
    const abiertos = lastSolution ? new Set(lastSolution.centros_abiertos) : new Set()
    centrosCerradosOcultos = !centrosCerradosOcultos

    const btn = document.getElementById('btn-toggle-cd')
    if (btn) btn.classList.toggle('active', centrosCerradosOcultos)

    nodesDS.forEach(node => {
      if (node.group !== 'centro') return
      const esCerrado = !abiertos.has(node.id)
      if (!esCerrado) return  // nunca ocultar un centro abierto/usado

      nodesDS.update({ id: node.id, hidden: centrosCerradosOcultos })
    })

    // Ocultar/mostrar aristas conectadas a centros cerrados
    edgesDS.forEach(edge => {
      if (edge._type !== 'planta_cd' && edge._type !== 'cd_cliente') return
      const cdId = edge._type === 'planta_cd' ? edge.to : edge.from
      const cdNode = nodesDS.get(cdId)
      if (!cdNode || cdNode.group !== 'centro') return
      const esCerrado = !abiertos.has(cdId)
      if (!esCerrado) return
      edgesDS.update({ id: edge.id, hidden: centrosCerradosOcultos })
    })

    network.fit({ animation: { duration: 400, easingFunction: 'easeInOutQuad' } })
  }

  /* ── Fit / zoom controls ────────────────────────────────────────────────── */
  function fitAll()    { network && network.fit({ animation: { duration: 400, easingFunction: 'easeInOutQuad' } }) }
  function zoomIn()    { network && network.moveTo({ scale: network.getScale() * 1.25, animation: { duration: 250 } }) }
  function zoomOut()   { network && network.moveTo({ scale: network.getScale() * 0.8,  animation: { duration: 250 } }) }
  function resetPhys() {
    if (!network) return
    network.setOptions({ physics: { enabled: true } })
    setTimeout(() => network.setOptions({ physics: { enabled: false } }), 2000)
  }

  /* ── API pública ─────────────────────────────────────────────────────────── */
  return { init, applySolution, resetVisual, fitAll, zoomIn, zoomOut, resetPhys, toggleCentrosCerrados }
})()
