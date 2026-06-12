/* editor.js — vis.js network editor para OptiNet */
/* Depende de: vis-network (CDN), dashboard.js, state global window.APP */

window.Editor = (() => {

  /* ── Estado local ──────────────────────────────────────────────────────── */
  let network = null
  let nodesDS = null
  let edgesDS = null
  let lastSolution = null
  const selectedNode = { id: null }

  /* ── Paleta sincronizada con style.css ─────────────────────────────────── */
  const COLOR = {
    planta:       { bg: '#1D4ED8', border: '#3B82F6', text: '#E6EDF3' },
    cliente:      { bg: '#15803D', border: '#22C55E', text: '#E6EDF3' },
    cliente_def:  { bg: '#991B1B', border: '#EF4444', text: '#E6EDF3' },
    centro_open:  { bg: '#92400E', border: '#F59E0B', text: '#E6EDF3' },
    centro_close: { bg: '#21262D', border: '#484F58', text: '#6B7280' },
    edge_active:  '#3B82F6',
    edge_cd:      '#F59E0B',
    edge_inactive:'#2D333B',
  }

  /* ── vis.js options ─────────────────────────────────────────────────────── */
  const NETWORK_OPTIONS = {
    physics: {
      enabled: true,
      solver: 'forceAtlas2Based',
      forceAtlas2Based: {
        gravitationalConstant: -80,
        centralGravity: 0.005,
        springLength: 140,
        springConstant: 0.06,
        damping: 0.4,
        avoidOverlap: 0.8,
      },
      stabilization: { iterations: 180, updateInterval: 25 },
    },
    nodes: {
      shape: 'dot',
      size: 18,
      font: { face: 'JetBrains Mono, monospace', size: 12, color: '#E6EDF3', bold: true },
      borderWidth: 2,
      borderWidthSelected: 3,
      shadow: false,
    },
    edges: {
      width: 1.5,
      smooth: { enabled: true, type: 'curvedCW', roundness: 0.12 },
      arrows: { to: { enabled: true, scaleFactor: 0.6 } },
      font: {
        face: 'JetBrains Mono, monospace',
        size: 10,
        color: '#8B949E',
        background: '#161B22',
        strokeWidth: 0,
        align: 'middle',
      },
      selectionWidth: 2,
    },
    interaction: {
      hover: true,
      tooltipDelay: 200,
      hideEdgesOnDrag: false,
      multiselect: false,
      selectConnectedEdges: false,
    },
    layout: { randomSeed: 42 },
  }

  /* ── Construir nodos vis desde datos de la API ──────────────────────────── */
  function buildNodes(data) {
    const nodes = []

    data.plantas.forEach(p => nodes.push({
      id: p.id,
      label: p.id,
      title: `Planta ${p.id}\nOferta: ${p.oferta} u.`,
      group: 'planta',
      color: { background: COLOR.planta.bg, border: COLOR.planta.border, highlight: { background: '#2563EB', border: '#60A5FA' } },
      x: -300, y: (nodes.length - 1) * 120,
      _data: p,
    }))

    data.centros.forEach((d, i) => nodes.push({
      id: d.id,
      label: d.id,
      title: `Centro ${d.id}\nCap: ${d.capacidad} u.\nFijo: $${d.costo_fijo}`,
      group: 'centro',
      shape: 'diamond',
      size: 16,
      color: { background: COLOR.centro_close.bg, border: COLOR.centro_close.border, highlight: { background: '#374151', border: '#9CA3AF' } },
      x: 0, y: i * 160 - 80,
      _data: d,
    }))

    data.clientes.forEach((c, i) => nodes.push({
      id: c.id,
      label: c.id,
      title: `Cliente ${c.id}\nDemanda: ${c.demanda} u.\nPenaliz: $${c.penalizacion}/u.`,
      group: 'cliente',
      color: { background: COLOR.cliente.bg, border: COLOR.cliente.border, highlight: { background: '#16A34A', border: '#4ADE80' } },
      x: 300, y: (i - 2) * 100,
      _data: c,
    }))

    return nodes
  }

  /* ── Construir aristas desde costos ─────────────────────────────────────── */
  function buildEdges(data) {
    const edges = []
    let eid = 0

    // Planta → Cliente (directas)
    Object.entries(data.costos_planta_cliente).forEach(([key, cost]) => {
      const [p, c] = key.replace('(', '').replace(')', '').split(', ').map(s => s.replace(/'/g, '').trim())
      edges.push({
        id: `dir_${eid++}`,
        from: p, to: c,
        label: `$${cost}`,
        color: { color: COLOR.edge_inactive, highlight: COLOR.edge_active, hover: '#484F58' },
        width: 1,
        dashes: false,
        _type: 'direct',
        _cost: cost,
        _key: `${p}_${c}`,
      })
    })

    // Planta → CD
    Object.entries(data.costos_planta_cd).forEach(([key, cost]) => {
      const [p, d] = key.replace('(', '').replace(')', '').split(', ').map(s => s.replace(/'/g, '').trim())
      edges.push({
        id: `pcd_${eid++}`,
        from: p, to: d,
        label: `$${cost}`,
        color: { color: COLOR.edge_inactive, highlight: COLOR.edge_cd, hover: '#484F58' },
        width: 1,
        dashes: [4, 3],
        _type: 'planta_cd',
        _cost: cost,
        _key: `${p}_${d}`,
      })
    })

    // CD → Cliente
    Object.entries(data.costos_cd_cliente).forEach(([key, cost]) => {
      const [d, c] = key.replace('(', '').replace(')', '').split(', ').map(s => s.replace(/'/g, '').trim())
      edges.push({
        id: `cdc_${eid++}`,
        from: d, to: c,
        label: `$${cost}`,
        color: { color: COLOR.edge_inactive, highlight: COLOR.edge_cd, hover: '#484F58' },
        width: 1,
        dashes: [2, 4],
        _type: 'cd_cliente',
        _cost: cost,
        _key: `${d}_${c}`,
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
          ? { background: COLOR.centro_open.bg, border: COLOR.centro_open.border, highlight: { background: '#B45309', border: '#FCD34D' } }
          : { background: COLOR.centro_close.bg, border: COLOR.centro_close.border }
        updates.title = `Centro ${node.id}\nCap: ${node._data.capacidad} u.\nFijo: $${node._data.costo_fijo}\n${open ? '✓ Abierto' : '✗ Cerrado'}`
      }

      if (node.group === 'cliente') {
        const def = deficit[node.id] || 0
        const hasDeficit = def > 0
        updates.color = hasDeficit
          ? { background: COLOR.cliente_def.bg, border: COLOR.cliente_def.border, highlight: { background: '#B91C1C', border: '#F87171' } }
          : { background: COLOR.cliente.bg, border: COLOR.cliente.border }
        const dem = node._data.demanda
        const rec = dem - def
        updates.title = `Cliente ${node.id}\nDemanda: ${dem} u.\nRecibido: ${rec} u.${hasDeficit ? `\nDéficit: ${def} u. ⚠` : '\n✓ Satisfecho'}`
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
        accentColor = COLOR.edge_active
      } else if (edge._type === 'planta_cd') {
        active = activePCD.has(edge._key)
        flujo  = sol.flujo_planta_cd[`('${edge.from}', '${edge.to}')`] || 0
        accentColor = COLOR.edge_cd
      } else if (edge._type === 'cd_cliente') {
        active = activeCDC.has(edge._key)
        flujo  = sol.flujo_cd_cliente[`('${edge.from}', '${edge.to}')`] || 0
        accentColor = COLOR.edge_cd
      }

      const w = active ? 1.5 + 4 * (flujo / maxFlujo) : 1
      const lbl = active ? `${flujo.toFixed(0)}u` : `$${edge._cost}`

      edgesDS.update({
        id: edge.id,
        width: w,
        label: lbl,
        color: {
          color:     active ? accentColor : COLOR.edge_inactive,
          highlight: accentColor,
          hover:     active ? accentColor : '#484F58',
          opacity:   active ? 1.0 : 0.25,
        },
        font: {
          color:      active ? accentColor : '#484F58',
          background: '#161B22',
          size:       active ? 11 : 9,
          bold:       active,
        },
      })
    })
  }

  /* ── Reset a estado inicial (sin solución) ──────────────────────────────── */
  function resetVisual() {
    if (!network) return
    lastSolution = null

    nodesDS.forEach(node => {
      const updates = { id: node.id }
      if (node.group === 'planta')
        updates.color = { background: COLOR.planta.bg, border: COLOR.planta.border }
      if (node.group === 'cliente')
        updates.color = { background: COLOR.cliente.bg, border: COLOR.cliente.border }
      if (node.group === 'centro')
        updates.color = { background: COLOR.centro_close.bg, border: COLOR.centro_close.border }
      nodesDS.update(updates)
    })

    edgesDS.forEach(edge => {
      edgesDS.update({
        id: edge.id,
        width: 1,
        label: `$${edge._cost}`,
        color: { color: COLOR.edge_inactive, opacity: 0.6 },
        font: { color: '#484F58', size: 9, bold: false },
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

    network.on('stabilizationIterationsDone', () => {
      network.setOptions({ physics: { enabled: false } })
    })

    // Hover tooltip nativo de vis (title del nodo)
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
