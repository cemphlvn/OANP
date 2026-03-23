import { onMounted, onUnmounted, watch, ref } from 'vue'
import * as d3 from 'd3'

/**
 * D3 force-directed graph composable for negotiation visualization.
 * Structured layout: parties on sides, issues in center, criteria clustered.
 */
export function useForceGraph(svgRef, { nodes, edges, onNodeClick }) {
  let simulation = null
  let svg = null
  let container = null
  let width = 0
  let height = 0
  const hoveredNode = ref(null)

  function init() {
    if (!svgRef.value) return

    const rect = svgRef.value.parentElement.getBoundingClientRect()
    width = rect.width || 400
    height = rect.height || 400

    // Skip init if container isn't visible yet (zero dimensions)
    if (width < 10 || height < 10) {
      // Retry after a frame
      requestAnimationFrame(() => init())
      return
    }

    svg = d3.select(svgRef.value)
      .attr('width', width)
      .attr('height', height)

    svg.selectAll('*').remove()

    // Defs
    const defs = svg.append('defs')

    // Glow filter
    const glow = defs.append('filter').attr('id', 'glow')
      .attr('x', '-50%').attr('y', '-50%').attr('width', '200%').attr('height', '200%')
    glow.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'blur')
    const merge = glow.append('feMerge')
    merge.append('feMergeNode').attr('in', 'blur')
    merge.append('feMergeNode').attr('in', 'SourceGraphic')

    // Soft shadow for nodes
    const shadow = defs.append('filter').attr('id', 'shadow')
      .attr('x', '-20%').attr('y', '-20%').attr('width', '140%').attr('height', '140%')
    shadow.append('feDropShadow')
      .attr('dx', '0').attr('dy', '1').attr('stdDeviation', '2').attr('flood-opacity', '0.08')

    // Container with zoom
    container = svg.append('g').attr('class', 'graph-container')

    svg.call(d3.zoom()
      .scaleExtent([0.4, 2.5])
      .on('zoom', (event) => container.attr('transform', event.transform))
    )

    // Background click to deselect
    svg.on('click', () => { if (onNodeClick) onNodeClick(null) })

    // Layers
    container.append('g').attr('class', 'edges-layer')
    container.append('g').attr('class', 'nodes-layer')
    container.append('g').attr('class', 'labels-layer')

    // Structured simulation
    simulation = d3.forceSimulation()
      .force('link', d3.forceLink().id(d => d.id).distance(d => {
        if (d.type === 'party-issue') return 100
        if (d.type === 'interest-issue') return 60
        if (d.type === 'criterion-issue') return 70
        if (d.type === 'move') return 160
        return 90
      }).strength(d => {
        if (d.type === 'move') return 0.05
        return 0.3
      }))
      .force('charge', d3.forceManyBody().strength(d => {
        if (d.nodeType === 'party') return -300
        if (d.nodeType === 'issue') return -120
        return -60
      }))
      .force('collision', d3.forceCollide().radius(d => {
        if (d.nodeType === 'party') return 45
        if (d.nodeType === 'issue') return 35
        return 18
      }))
      // Party nodes: push to left/right sides
      .force('partyX', d3.forceX().x(d => {
        if (d.nodeType !== 'party') return width / 2
        return d._partyIndex === 0 ? width * 0.2 : width * 0.8
      }).strength(d => d.nodeType === 'party' ? 0.4 : 0))
      .force('partyY', d3.forceY(height / 2).strength(d =>
        d.nodeType === 'party' ? 0.15 : 0.02
      ))
      // Issues: cluster in center
      .force('issueX', d3.forceX(width / 2).strength(d =>
        d.nodeType === 'issue' ? 0.15 : 0
      ))
      .force('issueY', d3.forceY(height / 2).strength(d =>
        d.nodeType === 'issue' ? 0.05 : 0
      ))
      .alphaDecay(0.025)
      .velocityDecay(0.45)

    updateGraph()
  }

  function updateGraph() {
    if (!svg || !container) return

    const nodeData = nodes.value || []
    const edgeData = edges.value || []

    // Assign party index for positioning
    let partyIdx = 0
    nodeData.forEach(d => {
      if (d.nodeType === 'party') { d._partyIndex = partyIdx++; }
    })

    // ---- EDGES ----
    const edgesLayer = container.select('.edges-layer')
    const edgeSel = edgesLayer.selectAll('.graph-edge').data(edgeData, d => d.id)

    edgeSel.exit().transition().duration(200).attr('opacity', 0).remove()

    const edgeEnter = edgeSel.enter()
      .append('line')
      .attr('class', 'graph-edge')
      .attr('stroke', d => d.color || '#E0E0E0')
      .attr('stroke-width', d => d.width || 1)
      .attr('stroke-dasharray', d => d.dashed ? '4 3' : 'none')
      .attr('opacity', 0)

    edgeEnter.transition().duration(400).attr('opacity', d => d.opacity || 0.5)

    const allEdges = edgeSel.merge(edgeEnter)

    // ---- NODES ----
    const nodesLayer = container.select('.nodes-layer')
    const nodeSel = nodesLayer.selectAll('.graph-node').data(nodeData, d => d.id)

    nodeSel.exit().transition().duration(200).attr('opacity', 0).remove()

    const nodeEnter = nodeSel.enter()
      .append('g')
      .attr('class', 'graph-node')
      .style('cursor', 'pointer')
      .call(drag(simulation))
      .on('click', (event, d) => {
        event.stopPropagation()
        if (onNodeClick) onNodeClick(d)
      })
      .on('mouseenter', (event, d) => { hoveredNode.value = d.id })
      .on('mouseleave', () => { hoveredNode.value = null })

    nodeEnter.each(function(d) {
      const g = d3.select(this)

      if (d.nodeType === 'party') {
        // Large circle with ring
        g.append('circle')
          .attr('r', 0)
          .attr('fill', '#FFF')
          .attr('stroke', d.color)
          .attr('stroke-width', 3)
          .attr('filter', 'url(#shadow)')
          .transition().duration(500)
          .attr('r', 28)

        // Inner fill
        g.append('circle')
          .attr('r', 0)
          .attr('fill', d.color + '18')
          .transition().duration(500)
          .attr('r', 25)

        // Letter
        g.append('text')
          .attr('text-anchor', 'middle')
          .attr('dy', '0.35em')
          .attr('font-family', "'Space Grotesk', sans-serif")
          .attr('font-size', '14px')
          .attr('font-weight', '700')
          .attr('fill', d.color)
          .text(d.label?.[0] || '?')

      } else if (d.nodeType === 'issue') {
        // Rounded rectangle
        const w = Math.min(90, Math.max(60, (d.label?.length || 5) * 6.5))
        g.append('rect')
          .attr('x', -w/2).attr('y', -14)
          .attr('width', w).attr('height', 28)
          .attr('rx', 6).attr('ry', 6)
          .attr('fill', d.agreed ? '#F0FDF4' : '#FFF')
          .attr('stroke', d.agreed ? '#22c55e' : '#D0D0D0')
          .attr('stroke-width', 1.5)
          .attr('filter', 'url(#shadow)')
          .attr('opacity', 0)
          .transition().duration(400)
          .attr('opacity', 1)

      } else if (d.nodeType === 'interest') {
        const size = d.disclosed ? 11 : 8
        g.append('rect')
          .attr('x', -size/2).attr('y', -size/2)
          .attr('width', size).attr('height', size)
          .attr('transform', 'rotate(45)')
          .attr('fill', d.disclosed ? '#06b6d420' : '#F5F5F5')
          .attr('stroke', d.disclosed ? '#06b6d4' : '#CCC')
          .attr('stroke-width', 1)
          .attr('stroke-dasharray', d.disclosed ? 'none' : '2 2')
          .attr('opacity', 0)
          .transition().duration(400)
          .attr('opacity', d.disclosed ? 0.9 : 0.4)

      } else if (d.nodeType === 'criterion') {
        g.append('path')
          .attr('d', hexPath(10))
          .attr('fill', '#F8F0FF')
          .attr('stroke', '#a855f7')
          .attr('stroke-width', 1)
          .attr('opacity', 0)
          .transition().duration(400)
          .attr('opacity', 0.6)

      } else if (d.nodeType === 'mediator') {
        g.append('rect')
          .attr('x', -10).attr('y', -10)
          .attr('width', 20).attr('height', 20)
          .attr('transform', 'rotate(45)')
          .attr('fill', '#F0FDF4')
          .attr('stroke', '#22c55e')
          .attr('stroke-width', 2)
          .attr('opacity', 0)
          .transition().duration(400)
          .attr('opacity', 1)
      }
    })

    const allNodes = nodeSel.merge(nodeEnter)

    // ---- LABELS ----
    const labelsLayer = container.select('.labels-layer')
    const labelSel = labelsLayer.selectAll('.graph-label').data(nodeData, d => d.id)

    labelSel.exit().remove()

    const labelEnter = labelSel.enter()
      .append('text')
      .attr('class', 'graph-label')
      .attr('text-anchor', 'middle')
      .attr('dy', d => {
        if (d.nodeType === 'party') return 44
        if (d.nodeType === 'issue') return 0.35 * 14 // vertically centered in rect
        return 22
      })
      .attr('font-family', d =>
        d.nodeType === 'party' ? "'Space Grotesk', sans-serif" : "'JetBrains Mono', monospace"
      )
      .attr('font-size', d => {
        if (d.nodeType === 'party') return '12px'
        if (d.nodeType === 'issue') return '10px'
        return '8px'
      })
      .attr('font-weight', d => d.nodeType === 'party' ? '600' : '500')
      .attr('fill', d => {
        if (d.nodeType === 'party') return d.color || '#000'
        if (d.nodeType === 'issue') return '#444'
        if (d.nodeType === 'interest') return d.disclosed ? '#06b6d4' : '#BBB'
        return '#999'
      })
      .attr('opacity', 0)
      .text(d => {
        if (d.nodeType === 'party') return d.label
        if (d.nodeType === 'issue') return d.label?.length > 14 ? d.label.slice(0, 12) + '..' : d.label
        return d.label?.length > 20 ? d.label.slice(0, 18) + '..' : d.label
      })

    labelEnter.transition().duration(400).attr('opacity', d => {
      if (d.nodeType === 'interest' && !d.disclosed) return 0.3
      return 1
    })

    // Issue labels go inside the rect (centered)
    labelEnter.filter(d => d.nodeType === 'issue')
      .attr('dy', '0.35em')

    const allLabels = labelSel.merge(labelEnter)

    // ---- SIMULATION ----
    simulation.nodes(nodeData)
    simulation.force('link').links(edgeData)
    simulation.alpha(0.6).restart()

    simulation.on('tick', () => {
      allEdges
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y)

      allNodes.attr('transform', d => `translate(${d.x}, ${d.y})`)

      allLabels
        .attr('x', d => d.x)
        .attr('y', d => d.y)
    })
  }

  function pulseNode(partyId) {
    if (!container) return
    container.select('.nodes-layer')
      .selectAll('.graph-node')
      .filter(d => d.id === partyId)
      .select('circle')
      .transition().duration(300)
      .attr('stroke-width', 5)
      .transition().duration(500)
      .attr('stroke-width', 3)
  }

  function flashEdge(sourceId, targetId, color) {
    if (!container) return
    const src = simulation.nodes().find(n => n.id === sourceId)
    const tgt = simulation.nodes().find(n => n.id === targetId)
    if (!src || !tgt) return

    container.select('.edges-layer')
      .append('line')
      .attr('x1', src.x).attr('y1', src.y)
      .attr('x2', src.x).attr('y2', src.y)
      .attr('stroke', color).attr('stroke-width', 2.5).attr('opacity', 0.7)
      .transition().duration(350)
      .attr('x2', tgt.x).attr('y2', tgt.y)
      .transition().duration(500)
      .attr('opacity', 0)
      .remove()
  }

  function markAgreed(issueId) {
    if (!container) return
    container.select('.nodes-layer')
      .selectAll('.graph-node')
      .filter(d => d.id === issueId)
      .select('rect')
      .transition().duration(500)
      .attr('fill', '#F0FDF4').attr('stroke', '#22c55e').attr('filter', 'url(#glow)')
  }

  function revealInterest(interestId) {
    if (!container) return
    container.select('.nodes-layer')
      .selectAll('.graph-node')
      .filter(d => d.id === interestId)
      .select('rect')
      .transition().duration(500)
      .attr('fill', '#06b6d420').attr('stroke', '#06b6d4')
      .attr('stroke-dasharray', 'none').attr('opacity', 0.9)
  }

  function handleResize() {
    if (!svgRef.value) return
    const rect = svgRef.value.parentElement.getBoundingClientRect()
    width = rect.width || 400
    height = rect.height || 400
    svg?.attr('width', width).attr('height', height)
    // Update position forces
    simulation?.force('partyX')?.x(d => {
      if (d.nodeType !== 'party') return width / 2
      return d._partyIndex === 0 ? width * 0.2 : width * 0.8
    })
    simulation?.force('partyY')?.y(height / 2)
    simulation?.force('issueX')?.x(width / 2)
    simulation?.force('issueY')?.y(height / 2)
    simulation?.alpha(0.3).restart()
  }

  function drag(sim) {
    return d3.drag()
      .on('start', (event, d) => {
        if (!event.active) sim.alphaTarget(0.3).restart()
        d.fx = d.x; d.fy = d.y
      })
      .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y })
      .on('end', (event, d) => {
        if (!event.active) sim.alphaTarget(0)
        d.fx = null; d.fy = null
      })
  }

  function hexPath(r) {
    const pts = []
    for (let i = 0; i < 6; i++) {
      const a = (Math.PI / 3) * i - Math.PI / 6
      pts.push([r * Math.cos(a), r * Math.sin(a)])
    }
    return 'M' + pts.map(p => p.join(',')).join('L') + 'Z'
  }

  onMounted(() => {
    init()
    window.addEventListener('resize', handleResize)
  })

  onUnmounted(() => {
    simulation?.stop()
    if (updateTimer) clearTimeout(updateTimer)
    window.removeEventListener('resize', handleResize)
  })

  // Debounced update — prevents rapid-fire rebuilds during live negotiation
  let updateTimer = null
  watch([nodes, edges], () => {
    if (updateTimer) clearTimeout(updateTimer)
    updateTimer = setTimeout(() => updateGraph(), 300)
  })

  return { hoveredNode, pulseNode, flashEdge, markAgreed, revealInterest, reinit: init }
}
