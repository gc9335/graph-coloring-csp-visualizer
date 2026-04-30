import { COLOR_PALETTE, SAMPLE_GRAPHS, VARIANTS, runVariant } from "./solver.js";

const $ = (id) => document.getElementById(id);

const els = {
  variantStrip: $("variant-strip"),
  heroMetrics: $("hero-metrics"),
  graphSelect: $("graph-select"),
  colorLimit: $("color-limit"),
  speedRange: $("speed-range"),
  speedLabel: $("speed-label"),
  nodeCount: $("node-count"),
  densityRange: $("density-range"),
  densityLabel: $("density-label"),
  randomBtn: $("random-btn"),
  restartBtn: $("restart-btn"),
  prevBtn: $("prev-btn"),
  playBtn: $("play-btn"),
  nextBtn: $("next-btn"),
  stepLabel: $("step-label"),
  progressFill: $("progress-fill"),
  stageCaption: $("stage-caption"),
  graphStage: $("graph-stage"),
  colorLegend: $("color-legend"),
  variantTitle: $("variant-title"),
  variantCore: $("variant-core"),
  variantVisual: $("variant-visual"),
  variantTime: $("variant-time"),
  variantSpace: $("variant-space"),
  eventTitle: $("event-title"),
  eventDetail: $("event-detail"),
  stackView: $("stack-view"),
  eventMeta: $("event-meta"),
  domainMatrix: $("domain-matrix"),
  pseudocodeList: $("pseudocode-list"),
  timeline: $("timeline"),
  treeLegend: $("tree-legend"),
  treeStageWrap: $("tree-stage-wrap"),
  searchTree: $("search-tree"),
};

const eventLabels = {
  "start-search": "初始化",
  "clique-prune": "团下界",
  "select-node": "选点",
  "order-colors": "排色",
  "try-color": "试色",
  "assign-color": "着色",
  "forward-check": "FC",
  "domain-prune": "削域",
  "domain-wipeout": "域清空",
  recurse: "递归",
  backtrack: "回溯",
  "dead-end": "死路",
  success: "成功",
  failure: "失败",
};

const state = {
  graphId: SAMPLE_GRAPHS[0].id,
  variantId: "V5",
  colorLimit: SAMPLE_GRAPHS[0].colorLimit,
  speed: 720,
  nodeCount: 10,
  density: 0.24,
  playing: false,
  timer: null,
  step: 0,
  trace: null,
  customGraph: null,
  treeZoom: 1,
  treeBaseWidth: 1200,
  treeBaseHeight: 720,
  stageDrag: {
    active: false,
    pointerId: null,
    nodeId: null,
  },
  treeDrag: {
    active: false,
    pointerId: null,
    startX: 0,
    startY: 0,
    scrollLeft: 0,
    scrollTop: 0,
  },
};

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function activeGraph() {
  if (state.graphId === "random" && state.customGraph) return state.customGraph;
  return SAMPLE_GRAPHS.find((graph) => graph.id === state.graphId);
}

function activeVariant() {
  return VARIANTS[state.variantId];
}

function activeFrame() {
  return state.trace.events[state.step] ?? state.trace.events.at(-1);
}

function colorById(colorId) {
  return COLOR_PALETTE.find((item) => item.id === colorId)?.hex ?? "#d4d8df";
}

function textColorForFill(fillHex) {
  const hex = fillHex.replace("#", "");
  const full = hex.length === 3 ? hex.split("").map((part) => part + part).join("") : hex;
  const r = Number.parseInt(full.slice(0, 2), 16);
  const g = Number.parseInt(full.slice(2, 4), 16);
  const b = Number.parseInt(full.slice(4, 6), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance < 0.62 ? "#fffdf7" : "#1d2433";
}

function stackPathKey(stack) {
  return stack.map((item) => `${item.node}:${item.color}`).join("|");
}

function colorNameById(colorId) {
  return COLOR_PALETTE.find((item) => item.id === colorId)?.name ?? `颜色${colorId}`;
}

function branchKey(parentId, nodeId, colorId) {
  return `${parentId}|${nodeId}|${colorId}`;
}

function labelFromIndex(index) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  if (index < alphabet.length) return alphabet[index];
  return `${alphabet[index % alphabet.length]}${Math.floor(index / alphabet.length)}`;
}

function randomBetween(min, max) {
  return min + Math.random() * (max - min);
}

function generateRandomGraph(nodeCount, density) {
  const minDistance = Math.max(0.11, 0.22 - nodeCount * 0.004);
  const nodes = [];
  let attempts = 0;
  while (nodes.length < nodeCount && attempts < 5000) {
    attempts += 1;
    const candidate = {
      id: labelFromIndex(nodes.length),
      x: randomBetween(0.14, 0.86),
      y: randomBetween(0.14, 0.86),
    };
    const separated = nodes.every((node) => Math.hypot(node.x - candidate.x, node.y - candidate.y) >= minDistance);
    if (separated) nodes.push(candidate);
  }
  while (nodes.length < nodeCount) {
    nodes.push({
      id: labelFromIndex(nodes.length),
      x: randomBetween(0.14, 0.86),
      y: randomBetween(0.14, 0.86),
    });
  }

  const edges = [];
  const edgeSet = new Set();
  const propensities = nodes.map(() => randomBetween(0.55, 1.75));
  const pushEdge = (a, b) => {
    if (a === b) return;
    const [left, right] = [a, b].sort();
    const key = `${left}-${right}`;
    if (edgeSet.has(key)) return;
    edgeSet.add(key);
    edges.push([left, right]);
  };

  for (let index = 1; index < nodes.length; index += 1) {
    const nearestPrevious = nodes
      .slice(0, index)
      .map((node, previousIndex) => ({
        previousIndex,
        distance: Math.hypot(node.x - nodes[index].x, node.y - nodes[index].y),
      }))
      .sort((left, right) => left.distance - right.distance)
      .slice(0, Math.min(3, index));
    const target = nearestPrevious[Math.floor(Math.random() * nearestPrevious.length)];
    pushEdge(nodes[index].id, nodes[target.previousIndex].id);
  }

  for (let left = 0; left < nodes.length; left += 1) {
    for (let right = left + 1; right < nodes.length; right += 1) {
      const distance = Math.hypot(nodes[left].x - nodes[right].x, nodes[left].y - nodes[right].y);
      const locality = Math.max(0.32, 1.18 - distance * 1.02);
      const bias = ((propensities[left] + propensities[right]) / 2) * locality;
      const probability = Math.max(0.03, Math.min(0.9, density * bias));
      if (Math.random() < probability) pushEdge(nodes[left].id, nodes[right].id);
    }
  }

  const hubIndexes = propensities
    .map((value, index) => ({ value, index }))
    .sort((left, right) => right.value - left.value)
    .slice(0, Math.max(1, Math.floor(nodeCount / 6)));
  hubIndexes.forEach(({ index }) => {
    nodes.forEach((node, candidateIndex) => {
      if (candidateIndex === index) return;
      if (Math.random() < density * 0.35 * propensities[index]) {
        pushEdge(nodes[index].id, node.id);
      }
    });
  });

  return {
    id: "random",
    name: `随机图 (${nodeCount} 节点)`,
    description: `随机生成的 ${nodeCount} 节点图，连边概率约为 ${density.toFixed(2)}。`,
    colorLimit: Math.min(4, COLOR_PALETTE.length),
    nodes,
    edges,
  };
}

function rerun(resetStep = true) {
  stopPlayback();
  if (state.graphId === "random" && !state.customGraph) {
    state.customGraph = generateRandomGraph(state.nodeCount, state.density);
  }
  const graph = activeGraph();
  state.trace = runVariant(graph, state.variantId, state.colorLimit);
  if (resetStep) state.step = 0;
  state.step = Math.min(state.step, state.trace.events.length - 1);
  render();
}

function stopPlayback() {
  if (state.timer) clearInterval(state.timer);
  state.timer = null;
  state.playing = false;
}

function startPlayback() {
  stopPlayback();
  state.playing = true;
  state.timer = window.setInterval(() => {
    if (state.step >= state.trace.events.length - 1) {
      stopPlayback();
      renderControls();
      return;
    }
    state.step += 1;
    render();
  }, state.speed);
}

function togglePlayback() {
  if (state.playing) {
    stopPlayback();
  } else {
    if (state.step >= state.trace.events.length - 1) state.step = 0;
    startPlayback();
  }
  renderControls();
}

function setStep(nextStep) {
  state.step = Math.max(0, Math.min(nextStep, state.trace.events.length - 1));
  render();
}

function renderVariantStrip() {
  els.variantStrip.innerHTML = Object.values(VARIANTS)
    .map(
      (variant) => `
        <button class="variant-card ${variant.id === state.variantId ? "active" : ""}" data-variant="${variant.id}" style="border-top: 5px solid ${variant.color}">
          <b>${variant.id}</b>
          <small>${variant.label}</small>
          <p>${variant.coreLogic}</p>
        </button>
      `,
    )
    .join("");
  els.variantStrip.querySelectorAll("[data-variant]").forEach((button) => {
    button.addEventListener("click", () => {
      state.variantId = button.dataset.variant;
      rerun(true);
    });
  });
}

function renderHeroMetrics() {
  const frame = activeFrame();
  const graph = activeGraph();
  const metrics = state.trace.metrics;
  const heroItems = [
    ["当前算法", state.variantId, activeVariant().label],
    ["图实例", graph.name, `${graph.nodes.length} 个节点 · ${graph.edges.length} 条边`],
    ["搜索节点", String(metrics.searchNodes), `回放事件 ${state.trace.events.length} · 最大深度 ${metrics.maxDepth}`],
    [
      "运行结果",
      state.trace.success ? "成功" : "失败",
      state.trace.success
        ? `${metrics.backtracks} 次回溯 · ${metrics.runtimeMs.toFixed(1)} ms`
        : `颜色上限 ${state.colorLimit} 下未找到可行着色`,
    ],
  ];
  els.heroMetrics.innerHTML = heroItems
    .map(
      ([label, value, note]) => `
        <div class="hero-metric">
          <span>${label}</span>
          <strong>${value}</strong>
          <span>${note}</span>
        </div>
      `,
    )
    .join("");
  els.stageCaption.textContent = `${graph.description} 当前聚焦：${frame.title}`;
}

function renderControls() {
  els.graphSelect.value = state.graphId;
  els.colorLimit.value = String(state.colorLimit);
  els.speedRange.value = String(state.speed);
  els.speedLabel.textContent = `${state.speed} ms`;
  els.nodeCount.value = String(state.nodeCount);
  els.densityRange.value = String(state.density);
  els.densityLabel.textContent = state.density.toFixed(2);
  els.stepLabel.textContent = `步骤 ${state.step + 1} / ${state.trace.events.length} · ${eventLabels[activeFrame().type] ?? activeFrame().title}`;
  els.progressFill.style.width = `${((state.step + 1) / state.trace.events.length) * 100}%`;
  els.playBtn.textContent = state.playing ? "暂停" : "播放";
  els.prevBtn.disabled = state.step === 0;
  els.nextBtn.disabled = state.step >= state.trace.events.length - 1;
}

function renderLegend() {
  const colors = COLOR_PALETTE.slice(0, state.colorLimit);
  els.colorLegend.innerHTML = colors
    .map(
      (color) => `
        <span class="legend-chip">
          <i class="legend-dot" style="background:${color.hex}"></i>
          ${color.id}. ${color.name}
        </span>
      `,
    )
    .join("");
}

function renderStage() {
  const graph = activeGraph();
  const frame = activeFrame();
  const focusSet = new Set(frame.focusNodes ?? []);
  const selected = frame.selectedNode;
  const assignment = frame.assignment;
  const draggedNodeId = state.stageDrag.active ? state.stageDrag.nodeId : null;
  const previewEvents = new Set(["assign-color", "forward-check", "domain-prune", "domain-wipeout", "recurse"]);
  const toX = (x) => 90 + x * 820;
  const toY = (y) => 70 + y * 540;

  const edgeMarkup = graph.edges
    .map(([left, right]) => {
      const a = graph.nodes.find((node) => node.id === left);
      const b = graph.nodes.find((node) => node.id === right);
      const focused = focusSet.has(left) && focusSet.has(right);
      const dragFocused = draggedNodeId && (left === draggedNodeId || right === draggedNodeId);
      return `<line class="edge ${focused ? "focus" : ""} ${dragFocused ? "drag-focus" : ""}" x1="${toX(a.x)}" y1="${toY(a.y)}" x2="${toX(b.x)}" y2="${toY(b.y)}" />`;
    })
    .join("");

  const nodeMarkup = graph.nodes
    .map((node, index) => {
      const colorId = assignment[index];
      const previewColor = !colorId && node.id === selected && frame.color != null && previewEvents.has(frame.type) ? colorById(frame.color) : null;
      const fill = colorId ? colorById(colorId) : previewColor ?? "#fffdf8";
      const labelFill = colorId || previewColor ? textColorForFill(fill) : "#1d2433";
      const ringClass = [
        "node-ring",
        focusSet.has(node.id) || node.id === selected ? "focus" : "",
        colorId ? "assigned" : "",
        previewColor ? "preview" : "",
      ]
        .filter(Boolean)
        .join(" ");
      const dragging = state.stageDrag.active && state.stageDrag.nodeId === node.id;
      return `
        <g class="stage-node ${dragging ? "dragging" : ""}" data-node-id="${node.id}">
          <circle class="${ringClass}" cx="${toX(node.x)}" cy="${toY(node.y)}" r="42" style="fill:${fill}" />
          <text class="node-label ${colorId || previewColor ? "on-color" : ""}" x="${toX(node.x)}" y="${toY(node.y) + 8}" style="fill:${labelFill}">${node.id}</text>
        </g>
      `;
    })
    .join("");

  els.graphStage.innerHTML = `${edgeMarkup}${nodeMarkup}`;
  renderLegend();
}

function stagePointerToGraphPoint(event) {
  const rect = els.graphStage.getBoundingClientRect();
  const viewBox = els.graphStage.viewBox.baseVal;
  const svgX = ((event.clientX - rect.left) / rect.width) * viewBox.width;
  const svgY = ((event.clientY - rect.top) / rect.height) * viewBox.height;
  return {
    x: clamp((svgX - 90) / 820, 0.06, 0.94),
    y: clamp((svgY - 70) / 540, 0.06, 0.94),
  };
}

function updateDraggedStageNode(event) {
  if (!state.stageDrag.active || !state.stageDrag.nodeId) return;
  if (state.stageDrag.pointerId != null && event.pointerId != null && event.pointerId !== state.stageDrag.pointerId) return;
  const graph = activeGraph();
  const node = graph?.nodes?.find((item) => item.id === state.stageDrag.nodeId);
  if (!node) return;
  const point = stagePointerToGraphPoint(event);
  node.x = point.x;
  node.y = point.y;
  renderStage();
}

function renderInfo() {
  const variant = activeVariant();
  const frame = activeFrame();
  els.variantTitle.textContent = `${variant.id} · ${variant.label}`;
  els.variantCore.textContent = variant.coreLogic;
  els.variantVisual.textContent = variant.visualization;
  els.variantTime.textContent = variant.complexity.time;
  els.variantSpace.textContent = variant.complexity.space;
  els.eventTitle.textContent = frame.title;
  els.eventDetail.textContent = frame.detail;

  els.stackView.innerHTML = frame.stack.length
    ? frame.stack.map((item) => `<span class="stack-pill">${item.node} = ${item.color}</span>`).join("")
    : `<span class="meta-pill">根状态</span>`;

  const metaBits = [];
  if (frame.meta?.heuristics?.length) metaBits.push(...frame.meta.heuristics.map((item) => `启发式 · ${item}`));
  if (frame.meta?.candidates?.length) metaBits.push(...frame.meta.candidates.map((item) => `${item.id} · 域 ${item.domainSize} · 度 ${item.degree}`));
  if (frame.meta?.lcvScores?.length) metaBits.push(...frame.meta.lcvScores.map((item) => `${item.colorName} · 影响值 ${item.impact}`));
  if (!metaBits.length) metaBits.push("当前步骤没有额外启发式元数据");
  els.eventMeta.innerHTML = metaBits.map((item) => `<span class="meta-pill">${item}</span>`).join("");
}

function renderDomainMatrix() {
  const frame = activeFrame();
  const palette = COLOR_PALETTE.slice(0, state.colorLimit);
  const graph = activeGraph();
  const header = `
    <div class="domain-row">
      <div></div>
      ${palette.map((color) => `<div class="domain-cell">${color.id}</div>`).join("")}
    </div>
  `;
  const body = graph.nodes
    .map((node, nodeIndex) => {
      const available = new Set(frame.domains[nodeIndex]);
      const assigned = frame.assignment[nodeIndex];
      return `
        <div class="domain-row">
          <div class="domain-node">${node.id}</div>
          ${palette
            .map((color) => {
              const isAvailable = available.has(color.id);
              const isSelected = assigned === color.id;
              const classes = ["domain-cell"];
              if (isAvailable) classes.push("available");
              if (isSelected) classes.push("selected");
              return `<div class="${classes.join(" ")}" style="${isAvailable ? `background:${color.hex};` : ""}">${isAvailable ? color.name : "—"}</div>`;
            })
            .join("")}
        </div>
      `;
    })
    .join("");
  els.domainMatrix.innerHTML = header + body;
}

function renderPseudocode() {
  const frame = activeFrame();
  const hot = new Set(frame.highlight ?? []);
  els.pseudocodeList.innerHTML = activeVariant().pseudocode
    .map((line) => `<li class="${hot.has(line.key) ? "active" : ""}">${line.text}</li>`)
    .join("");
}

function renderTimeline() {
  els.timeline.innerHTML = state.trace.events
    .map(
      (item, index) => `
        <button class="timeline-item ${index === state.step ? "active" : ""}" data-step="${index}" type="button">
          <strong>${String(index + 1).padStart(2, "0")} · ${item.title}</strong>
          <span>${eventLabels[item.type] ?? item.type}</span>
          <p>${item.detail}</p>
        </button>
      `,
    )
    .join("");
  els.timeline.querySelectorAll("[data-step]").forEach((button) => {
    button.addEventListener("click", () => setStep(Number(button.dataset.step)));
  });
}

function buildSearchTree(trace, uptoStep) {
  const nodes = new Map();
  const root = {
    id: "root",
    parentId: null,
    depth: 0,
    kind: "root",
    title: "起点",
    subtitle: "搜索入口",
    color: "#fff7e8",
    border: "#0b4f6c",
    children: [],
    createdAt: -1,
  };
  nodes.set(root.id, root);

  function addNode(node) {
    if (nodes.has(node.id)) return nodes.get(node.id);
    nodes.set(node.id, node);
    const parent = nodes.get(node.parentId);
    if (parent) parent.children.push(node.id);
    return node;
  }

  const activeBranchByPath = new Map([["", "root"]]);

  function pathFromStack(stack) {
    return stackPathKey(stack ?? []);
  }

  for (let step = 0; step <= uptoStep; step += 1) {
    const event = trace.events[step];
    if (!event) continue;
    const parentPath = pathFromStack(event.stack);
    const parentBranchId = activeBranchByPath.get(parentPath) ?? "root";

    if (event.type === "order-colors" && event.selectedNode) {
      const paletteColors = event.meta?.allPaletteColors ?? [];
      const availableColors = new Set(event.meta?.availableColors ?? []);
      const orderedColors = new Set(event.meta?.orderedColors ?? []);
      const parentDepth = nodes.get(parentBranchId)?.depth ?? 0;
      paletteColors.forEach((colorId) => {
        let status = "pruned";
        let subtitle = "不满足约束";
        if (availableColors.has(colorId) && orderedColors.has(colorId)) {
          status = "candidate";
          subtitle = "候选分支";
        } else if (availableColors.has(colorId) && !orderedColors.has(colorId)) {
          status = "symmetry-pruned";
          subtitle = "对称/启发式跳过";
        }
        addNode({
          id: branchKey(parentBranchId, event.selectedNode, colorId),
          parentId: parentBranchId,
          depth: parentDepth + 1,
          kind: "choice",
          title: `${event.selectedNode}`,
          subtitle: `${colorNameById(colorId)} · ${subtitle}`,
          color: colorById(colorId),
          border: colorById(colorId),
          children: [],
          createdAt: step,
          eventType: "choice",
          status,
          nodeId: event.selectedNode,
          colorId,
        });
      });
      continue;
    }

    if (event.type === "try-color" && event.selectedNode && event.color != null) {
      const choiceId = branchKey(parentBranchId, event.selectedNode, event.color);
      const choice = nodes.get(choiceId);
      if (choice) {
        choice.status = "trying";
        choice.subtitle = "正在尝试";
      }
      continue;
    }

    if (event.type === "assign-color" && event.selectedNode && event.color != null) {
      const stackBeforeAssign = (event.stack ?? []).slice(0, -1);
      const beforePath = pathFromStack(stackBeforeAssign);
      const actualParent = activeBranchByPath.get(beforePath) ?? "root";
      const choiceId = branchKey(actualParent, event.selectedNode, event.color);
      const choice = nodes.get(choiceId);
      if (choice) {
        choice.status = "accepted";
        choice.subtitle = "进入下一层";
      }
      activeBranchByPath.set(pathFromStack(event.stack), choiceId);
      continue;
    }

    if (event.type === "backtrack" && event.selectedNode && event.color != null) {
      const choiceId = branchKey(parentBranchId, event.selectedNode, event.color);
      const choice = nodes.get(choiceId);
      if (choice) {
        choice.status = "failed";
        choice.subtitle = "回溯撤销";
      }
      continue;
    }

    const markerMap = {
      "domain-prune": { title: "削域", subtitle: event.meta?.prunedNode ? `邻居 ${event.meta.prunedNode}` : "FC 传播", color: "#c84c09", border: "#8d3608" },
      "domain-wipeout": { title: "剪枝", subtitle: "域被削空", color: "#b42318", border: "#7a1414" },
      "dead-end": { title: "死路", subtitle: "无解回退", color: "#d65a31", border: "#9c3d1c" },
      "clique-prune": { title: "剪枝", subtitle: "团下界", color: "#b42318", border: "#7a1414" },
      success: { title: "成功", subtitle: "找到可行着色", color: "#1c7c54", border: "#12513a" },
      failure: { title: "失败", subtitle: "颜色上限不足", color: "#586074", border: "#394150" },
    };
    const marker = markerMap[event.type];
    if (!marker) continue;
    addNode({
      id: `${parentBranchId}>${event.type}:${step}`,
      parentId: parentBranchId,
      depth: (nodes.get(parentBranchId)?.depth ?? 0) + 1,
      kind: "marker",
      title: marker.title,
      subtitle: marker.subtitle,
      color: marker.color,
      border: marker.border,
      children: [],
      createdAt: step,
      eventType: event.type,
      status: event.type === "success" ? "success" : "pruned",
    });
  }

  return { nodes };
}

function renderSearchTree() {
  const tree = buildSearchTree(state.trace, state.step);
  const frame = activeFrame();
  const currentBranchIds = new Set(["root"]);
  let parentId = "root";
  for (const item of frame.stack ?? []) {
    parentId = branchKey(parentId, item.node, item.color);
    currentBranchIds.add(parentId);
  }
  const successEvent = state.trace.events.find((event) => event.type === "success");
  const solved = Boolean(successEvent) && state.step >= successEvent.step;
  const solutionBranchIds = new Set(["root"]);
  if (solved && successEvent?.stack?.length) {
    let branchParent = "root";
    for (const item of successEvent.stack) {
      branchParent = branchKey(branchParent, item.node, item.color);
      solutionBranchIds.add(branchParent);
    }
  }

  const allNodes = [...tree.nodes.values()];
  const pruneCount = allNodes.filter((node) => ["domain-prune", "domain-wipeout", "dead-end", "clique-prune"].includes(node.eventType) || ["pruned", "symmetry-pruned", "failed"].includes(node.status)).length;
  const successCount = allNodes.filter((node) => node.eventType === "success" || node.status === "success").length;

  els.treeLegend.innerHTML = [
    `<span class="tree-chip"><i class="tree-swatch current"></i>当前搜索路径</span>`,
    `<span class="tree-chip"><i class="tree-swatch explored"></i>已探索分支</span>`,
    `<span class="tree-chip"><i class="tree-swatch candidate"></i>候选颜色</span>`,
    `<span class="tree-chip"><i class="tree-swatch pruned"></i>剪枝/死路 ${pruneCount}</span>`,
    `<span class="tree-chip"><i class="tree-swatch success"></i>成功分支 ${successCount}</span>`,
  ].join("");

  function orderedChildren(node) {
    return (node.children ?? [])
      .map((childId) => tree.nodes.get(childId))
      .filter(Boolean)
      .sort((a, b) => {
        if (a.kind === "choice" && b.kind === "choice") return (a.colorId ?? 0) - (b.colorId ?? 0);
        return (a.createdAt ?? 0) - (b.createdAt ?? 0);
      });
  }

  function measure(nodeId) {
    const node = tree.nodes.get(nodeId);
    if (!node) return 1;
    const children = orderedChildren(node);
    if (!children.length) return 1;
    return Math.max(1, children.reduce((sum, child) => sum + measure(child.id), 0));
  }

  const colGap = 188;
  const rowUnit = 74;
  const topPad = 56;
  const leftPad = 110;
  const totalUnits = measure("root");
  const maxDepth = Math.max(...allNodes.map((node) => node.depth));
  const width = Math.max(1280, (maxDepth + 2) * colGap + 180);
  const height = Math.max(760, totalUnits * rowUnit + 120);
  state.treeBaseWidth = width;
  state.treeBaseHeight = height;
  els.searchTree.setAttribute("viewBox", `0 0 ${width} ${height}`);
  els.searchTree.style.width = `${width * state.treeZoom}px`;
  els.searchTree.style.height = `${height * state.treeZoom}px`;

  const positioned = [];
  const byId = new Map();

  function layout(nodeId, top) {
    const node = tree.nodes.get(nodeId);
    if (!node) return top;
    const children = orderedChildren(node);
    const span = measure(nodeId) * rowUnit;
    const nodeX = leftPad + node.depth * colGap;
    let nodeY = top + span / 2;

    if (!children.length) {
      const positionedNode = { ...node, x: nodeX, y: nodeY };
      positioned.push(positionedNode);
      byId.set(nodeId, positionedNode);
      return nodeY;
    }

    let cursor = top;
    const childYs = [];
    children.forEach((child) => {
      const childSpan = measure(child.id) * rowUnit;
      childYs.push(layout(child.id, cursor));
      cursor += childSpan;
    });
    nodeY = (childYs[0] + childYs.at(-1)) / 2;
    const positionedNode = { ...node, x: nodeX, y: nodeY };
    positioned.push(positionedNode);
    byId.set(nodeId, positionedNode);
    return nodeY;
  }

  layout("root", topPad);

  const edges = positioned
    .filter((node) => node.parentId)
    .map((node) => {
      const parent = byId.get(node.parentId);
      const current = currentBranchIds.has(node.id);
      const candidate = node.kind === "choice" && ["candidate", "trying"].includes(node.status);
      const masked = solved && !solutionBranchIds.has(node.id) && !solutionBranchIds.has(node.parentId);
      return `
        <path
          class="tree-edge ${current ? "current" : node.kind === "marker" ? "marker" : candidate ? "candidate" : ""} ${masked ? "masked" : ""}"
          d="M ${parent.x + 60} ${parent.y} C ${parent.x + 110} ${parent.y}, ${node.x - 80} ${node.y}, ${node.x - 18} ${node.y}"
        />
      `;
    })
    .join("");

  const nodeMarkup = positioned
    .map((node) => {
      if (node.kind === "root") {
        return `
          <g>
            <rect class="tree-node root ${solved ? "solution-root" : ""}" x="${node.x - 52}" y="${node.y - 24}" width="120" height="48" rx="20" />
            <text class="tree-title root" x="${node.x + 8}" y="${node.y + 2}">${node.title}</text>
          </g>
        `;
      }

      if (node.kind === "marker") {
        const pruneLike = ["domain-prune", "domain-wipeout", "dead-end", "clique-prune"].includes(node.eventType);
        const masked = solved && !solutionBranchIds.has(node.parentId);
        return `
          <g class="${masked ? "tree-mask" : ""}">
            <rect class="tree-node marker ${pruneLike ? "pruned" : "success"}" x="${node.x - 60}" y="${node.y - 24}" width="136" height="48" rx="16" style="fill:${node.color}; stroke:${node.border}" />
            <text class="tree-title marker" x="${node.x + 8}" y="${node.y - 4}">${node.title}</text>
            <text class="tree-subtitle marker" x="${node.x + 8}" y="${node.y + 12}">${node.subtitle}</text>
            ${pruneLike ? `<text class="tree-prune-mark" x="${node.x + 56}" y="${node.y - 5}">✕</text>` : ""}
          </g>
        `;
      }

      const active = currentBranchIds.has(node.id);
      const onSolution = solutionBranchIds.has(node.id);
      const masked = solved && !onSolution;
      if (node.kind === "choice") {
        const statusClass =
          node.status === "accepted"
            ? "success"
            : node.status === "candidate" || node.status === "trying"
              ? "candidate"
              : node.status === "symmetry-pruned" || node.status === "pruned" || node.status === "failed"
                ? "pruned"
                : "";
        const stroke = statusClass === "pruned" ? "#b42318" : active ? "#0b4f6c" : node.border;
        return `
          <g class="${masked ? "tree-mask" : ""}">
            <rect class="tree-node choice ${active ? "current" : ""} ${statusClass} ${onSolution ? "solution" : ""}" x="${node.x - 64}" y="${node.y - 26}" width="148" height="52" rx="18" style="fill:${node.color}; stroke:${stroke}" />
            <text class="tree-title choice" x="${node.x + 10}" y="${node.y - 5}">${node.title}</text>
            <text class="tree-subtitle choice" x="${node.x + 10}" y="${node.y + 12}">${node.subtitle}</text>
            ${statusClass === "pruned" ? `<text class="tree-prune-mark" x="${node.x + 64}" y="${node.y - 6}">✕</text>` : ""}
          </g>
        `;
      }

      return `
        <g>
          <rect class="tree-node assign ${active ? "current" : ""}" x="${node.x - 56}" y="${node.y - 26}" width="136" height="52" rx="18" style="fill:${node.color}; stroke:${active ? "#0b4f6c" : node.border}" />
          <text class="tree-title assign" x="${node.x + 12}" y="${node.y - 5}">${node.title}</text>
          <text class="tree-subtitle assign" x="${node.x + 12}" y="${node.y + 13}">${node.subtitle}</text>
        </g>
      `;
    })
    .join("");

  els.searchTree.innerHTML = `${edges}${nodeMarkup}`;
}

function generateNewRandomGraph() {
  state.customGraph = generateRandomGraph(state.nodeCount, state.density);
  state.graphId = "random";
  rerun(true);
}

function render() {
  renderVariantStrip();
  renderHeroMetrics();
  renderControls();
  renderStage();
  renderInfo();
  renderDomainMatrix();
  renderPseudocode();
  renderTimeline();
  renderSearchTree();
}

function seedControls() {
  els.graphSelect.innerHTML = [
    ...SAMPLE_GRAPHS.map((graph) => `<option value="${graph.id}">${graph.name}</option>`),
    `<option value="random">随机图</option>`,
  ].join("");
  els.graphSelect.addEventListener("change", () => {
    state.graphId = els.graphSelect.value;
    if (state.graphId === "random") {
      if (!state.customGraph) state.customGraph = generateRandomGraph(state.nodeCount, state.density);
    } else {
      state.colorLimit = activeGraph().colorLimit;
    }
    rerun(true);
  });
  els.colorLimit.addEventListener("change", () => {
    state.colorLimit = Math.max(2, Math.min(6, Number(els.colorLimit.value) || activeGraph().colorLimit));
    rerun(true);
  });
  els.nodeCount.addEventListener("change", () => {
    state.nodeCount = Math.max(4, Math.min(16, Number(els.nodeCount.value) || 10));
  });
  els.densityRange.addEventListener("input", () => {
    state.density = Number(els.densityRange.value);
    els.densityLabel.textContent = state.density.toFixed(2);
  });
  els.randomBtn.addEventListener("click", generateNewRandomGraph);
  els.speedRange.addEventListener("input", () => {
    state.speed = Number(els.speedRange.value);
    els.speedLabel.textContent = `${state.speed} ms`;
    if (state.playing) startPlayback();
  });
  els.restartBtn.addEventListener("click", () => rerun(true));
  els.prevBtn.addEventListener("click", () => setStep(state.step - 1));
  els.nextBtn.addEventListener("click", () => setStep(state.step + 1));
  els.playBtn.addEventListener("click", togglePlayback);

  function beginStageDrag(event) {
    const target = event.target.closest?.("[data-node-id]");
    if (!target || event.button !== 0) return;
    stopPlayback();
    state.stageDrag.active = true;
    state.stageDrag.pointerId = event.pointerId ?? null;
    state.stageDrag.nodeId = target.dataset.nodeId;
    els.graphStage.classList.add("is-dragging");
    if (event.pointerId != null) {
      els.graphStage.setPointerCapture?.(event.pointerId);
    }
    updateDraggedStageNode(event);
    event.preventDefault();
    renderControls();
  }

  function moveStageDrag(event) {
    if (!state.stageDrag.active) return;
    updateDraggedStageNode(event);
    event.preventDefault();
  }

  function stopStageDrag(event) {
    if (!state.stageDrag.active) return;
    if (event?.pointerId != null && state.stageDrag.pointerId != null && event.pointerId !== state.stageDrag.pointerId) return;
    if (state.stageDrag.pointerId != null) {
      els.graphStage.releasePointerCapture?.(state.stageDrag.pointerId);
    }
    state.stageDrag.active = false;
    state.stageDrag.pointerId = null;
    state.stageDrag.nodeId = null;
    els.graphStage.classList.remove("is-dragging");
    renderStage();
  }

  els.graphStage.addEventListener("pointerdown", beginStageDrag);
  window.addEventListener("pointermove", moveStageDrag);
  window.addEventListener("pointerup", stopStageDrag);
  els.graphStage.addEventListener("pointercancel", stopStageDrag);
  els.graphStage.addEventListener("lostpointercapture", stopStageDrag);

  function beginTreeDrag(event) {
    if (event.button !== 0) return;
    if ("isPrimary" in event && !event.isPrimary) return;
    state.treeDrag.active = true;
    state.treeDrag.pointerId = "pointerId" in event ? event.pointerId : null;
    state.treeDrag.startX = event.clientX;
    state.treeDrag.startY = event.clientY;
    state.treeDrag.scrollLeft = els.treeStageWrap.scrollLeft;
    state.treeDrag.scrollTop = els.treeStageWrap.scrollTop;
    if ("pointerId" in event) {
      els.treeStageWrap.setPointerCapture?.(event.pointerId);
    }
    els.treeStageWrap.classList.add("is-panning");
    event.preventDefault();
  }

  function moveTreeDrag(event) {
    if (!state.treeDrag.active) return;
    if ("pointerId" in event && state.treeDrag.pointerId != null && event.pointerId !== state.treeDrag.pointerId) return;
    const dx = event.clientX - state.treeDrag.startX;
    const dy = event.clientY - state.treeDrag.startY;
    els.treeStageWrap.scrollLeft = state.treeDrag.scrollLeft - dx;
    els.treeStageWrap.scrollTop = state.treeDrag.scrollTop - dy;
    event.preventDefault();
  }

  function stopTreeDrag(event) {
    if (!state.treeDrag.active) return;
    if (event?.pointerId != null && state.treeDrag.pointerId != null && event.pointerId !== state.treeDrag.pointerId) return;
    state.treeDrag.active = false;
    if (state.treeDrag.pointerId != null) {
      els.treeStageWrap.releasePointerCapture?.(state.treeDrag.pointerId);
    }
    state.treeDrag.pointerId = null;
    els.treeStageWrap.classList.remove("is-panning");
  }

  [els.treeStageWrap, els.searchTree].forEach((element) => {
    element.addEventListener("mousedown", beginTreeDrag);
    element.addEventListener("pointerdown", beginTreeDrag);
  });
  window.addEventListener("mousemove", moveTreeDrag);
  window.addEventListener("pointermove", moveTreeDrag);
  window.addEventListener("mouseup", stopTreeDrag);
  els.treeStageWrap.addEventListener("pointerup", stopTreeDrag);
  els.treeStageWrap.addEventListener("pointercancel", stopTreeDrag);
  els.treeStageWrap.addEventListener("lostpointercapture", stopTreeDrag);
  els.treeStageWrap.addEventListener("wheel", (event) => {
    event.preventDefault();
    const oldZoom = state.treeZoom;
    const delta = event.deltaY < 0 ? 1.12 : 0.9;
    state.treeZoom = Math.max(0.55, Math.min(2.8, state.treeZoom * delta));
    const rect = els.treeStageWrap.getBoundingClientRect();
    const anchorX = (els.treeStageWrap.scrollLeft + event.clientX - rect.left) / oldZoom;
    const anchorY = (els.treeStageWrap.scrollTop + event.clientY - rect.top) / oldZoom;
    renderSearchTree();
    els.treeStageWrap.scrollLeft = anchorX * state.treeZoom - (event.clientX - rect.left);
    els.treeStageWrap.scrollTop = anchorY * state.treeZoom - (event.clientY - rect.top);
  }, { passive: false });
}

seedControls();
rerun(true);
