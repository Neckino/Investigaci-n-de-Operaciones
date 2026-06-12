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
    planta:       { bg: '#1E40AF', border: '#60A5FA', text: '#DBEAFE' },
    cliente:      { bg: '#14532D', border: '#4ADE80', text: '#DCFCE7' },
    cliente_def:  { bg: '#7F1D1D', border: '#F87171', text: '#FEE2E2' },
    centro_open:  { bg: '#78350F', border: '#FCD34D', text: '#FEF3C7' },
    centro_close: { bg: '#1C2128', border: '#6E7681', text: '#8B949E' },
    edge_active:  '#60A5FA',
    edge_cd:      '#FCD34D',
    edge_inactive:'#3D444D',
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
    const COL = { planta: -380, cd: 0, cliente: 380 }
    const GAP = 110  // espaciado vertical entre nodos

    // Centrar verticalmente cada columna
    const centerY = (count) => (idx) => (idx - (count - 1) / 2) * GAP

    const yPlanta  = centerY(data.plantas.length)
    const yCentro  = centerY(data.centros.length)
    const yCliente = centerY(data.clientes.length)

    data.plantas.forEach((p, i) => nodes.push({
      id: p.id,
      label: `${p.id}\n${p.oferta}u`,
      title: `<b>Planta ${p.id}</b><br>Oferta: <b>${p.oferta} u.</b>`,
      group: 'planta',
      color: {
        background: COLOR.planta.bg,
        border: COLOR.planta.border,
        highlight: { background: '#2563EB', border: '#93C5FD' },
        hover: { background: '#1D4ED8', border: '#93C5FD' },
      },
      font: { color: COLOR.planta.text, multi: false },
      x: COL.planta, y: yPlanta(i),
      fixed: { x: true, y: true },
      _data: p,
    }))

    data.centros.forEach((d, i) => nodes.push({
      id: d.id,
      label: `${d.id}\n$${d.costo_fijo.toLocaleString()}`,
      title: `<b>Centro ${d.id}</b><br>Cap: <b>${d.capacidad} u.</b><br>Fijo: <b>$${d.costo_fijo.toLocaleString()}</b>`,
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
      title: `<b>Cliente ${c.id}</b><br>Demanda: <b>${c.demanda} u.</b><br>Penaliz: <b>$${c.penalizacion}/u.</b>`,
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

  /* ── Construir aristas con colores contrastados ─────────────────────────── */
  function buildEdges(data) {
    const edges = []
    let eid = 0

    // Planta → Cliente (directas) — línea continua azul
    Object.entries(data.costos_planta_cliente).forEach(([key, cost]) => {
      const [p, c] = key.replace('(', '').replace(')', '').split(', ').map(s => s.replace(/'/g, '').trim())
      edges.push({
        id: `dir_${eid++}`,
        from: p, to: c,
        label: `$${cost}`,
        color: { color: COLOR.edge_inactive, highlight: COLOR.edge_active, hover: '#5E6E80', opacity: 0.55 },
        width: 1.2,
        dashes: false,
        font: { color: '#8B949E', background: '#161B22', size: 10, strokeWidth: 2, strokeColor: '#161B22' },
        _type: 'direct', _cost: cost, _key: `${p}_${c}`,
      })
    })

    // Planta → CD — línea punteada amarilla
    Object.entries(data.costos_planta_cd).forEach(([key, cost]) => {
      const [p, d] = key.replace('(', '').replace(')', '').split(', ').map(s => s.replace(/'/g, '').trim())
      edges.push({
        id: `pcd_${eid++}`,
        from: p, to: d,
        label: `$${cost}`,
        color: { color: '#4A3F20', highlight: COLOR.edge_cd, hover: '#5E5030', opacity: 0.55 },
        width: 1.2,
        dashes: [6, 4],
        font: { color: '#8B949E', background: '#161B22', size: 10, strokeWidth: 2, strokeColor: '#161B22' },
        _type: 'planta_cd', _cost: cost, _key: `${p}_${d}`,
      })
    })

    // CD → Cliente — línea guión-punto naranja/ámbar
    Object.entries(data.costos_cd_cliente).forEach(([key, cost]) => {
      const [d, c] = key.replace('(', '').replace(')', '').split(', ').map(s => s.replace(/'/g, '').trim())
      edges.push({
        id: `cdc_${eid++}`,
        from: d, to: c,
        label: `$${cost}`,
        color: { color: '#3D3420', highlight: COLOR.edge_cd, hover: '#4A3F28', opacity: 0.55 },
        width: 1.2,
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
        updates.title = `<b>Centro ${node.id}</b><br>Cap: <b>${node._data.capacidad} u.</b><br>Fijo: <b>$${node._data.costo_fijo.toLocaleString()}</b><br>${open ? '✓ Abierto' : '✗ Cerrado'}`
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
        updates.title = `<b>Cliente ${node.id}</b><br>Demanda: <b>${dem} u.</b><br>Recibido: <b>${rec} u.</b>${hasDeficit ? `<br>⚠ Déficit: <b>${def} u.</b>` : '<br>✓ Satisfecho'}`
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
      const lbl = active ? `${flujo.toFixed(0)}u` : `$${edge._cost}`

      edgesDS.update({
        id: edge.id,
        width: w,
        label: lbl,
        color: {
          color:     active ? accentColor : COLOR.edge_inactive,
          highlight: accentColor,
          hover:     active ? accentColor : '#5E6E80',
          opacity:   active ? 1.0 : 0.2,
        },
        font: {
          color:       active ? accentColor : '#484F58',
          background:  '#161B22',
          strokeWidth: 2,
          strokeColor: '#161B22',
          size:        active ? 12 : 10,
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

    nodesDS.forEach(node => {
      const updates = { id: node.id }
      if (node.group === 'planta') {
        updates.color = { background: COLOR.planta.bg, border: COLOR.planta.border }
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
        width: 1.2,
        label: `$${edge._cost}`,
        color: { color: COLOR.edge_inactive, opacity: 0.5 },
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
  return { init, applySolution, resetVisual, fitAll, zoomIn, zoomOut, resetPhys }
})()
