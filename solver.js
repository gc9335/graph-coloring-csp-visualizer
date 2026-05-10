const BASE_LINES = [
  ["init-order", "order <- vertices sorted by descending degree"],
];

function pseudocodeFor(flags) {
  const lines = [...BASE_LINES];
  if (flags.cliqueBound) {
    lines.push(["clique-bound", "if cliqueLowerBound(G) > M then return FAIL"]);
  }
  if (flags.componentDecomposition) {
    lines.push(["decompose", "split graph into connected components when beneficial"]);
  }
  if (flags.mrv) {
    lines.push([
      "select-node",
      flags.degreeTieBreak
        ? "v <- MRV node, break ties by highest degree"
        : "v <- uncolored vertex with minimum remaining values",
    ]);
  } else {
    lines.push(["select-node", "v <- next uncolored vertex in order"]);
  }
  lines.push([
    "order-colors",
    flags.lcv
      ? "colors <- order by least constraining value"
      : flags.symmetryBreaking
        ? "colors <- usedColorsFirst(v) + oneNewColorBySymmetry(v)"
        : "colors <- all feasible colors in numeric order",
  ]);
  lines.push(["try-color", "for c in colors do"]);
  lines.push(["assign-color", "  if safe(v, c) then assign v <- c"]);
  if (flags.forwardChecking) {
    lines.push(["forward-check", "  delete c from every uncolored neighbor domain"]);
    lines.push(["wipeout", "  if some neighbor domain becomes empty then undo and continue"]);
  }
  lines.push(["recurse", "  if search(next state) then return SUCCESS"]);
  lines.push(["backtrack", "  undo assignment and restore state"]);
  lines.push(["fail", "return FAIL"]);
  return lines.map(([key, text]) => ({ key, text }));
}

function makeVariant(id, name, label, color, flags, texts) {
  return {
    id,
    name,
    label,
    color,
    ...flags,
    coreLogic: texts.core,
    visualization: texts.visual,
    complexity: { time: texts.time, space: texts.space },
    pseudocode: pseudocodeFor(flags),
  };
}

export const COLOR_PALETTE = [
  { id: 1, name: "朱砂红", hex: "#d95c4f" },
  { id: 2, name: "琥珀黄", hex: "#e8b33d" },
  { id: 3, name: "孔雀蓝", hex: "#2f6f9f" },
  { id: 4, name: "松石青", hex: "#67b8b1" },
  { id: 5, name: "石榴紫", hex: "#8d6fd1" },
  { id: 6, name: "珊瑚粉", hex: "#f08a9d" },
];

export const VARIANTS = {
  V0: makeVariant(
    "V0",
    "Base Backtracking",
    "基础回溯搜索",
    "#2f6690",
    { forwardChecking: false, mrv: false, degreeTieBreak: false, lcv: false, symmetryBreaking: false, cliqueBound: false, componentDecomposition: false },
    {
      core: "从当前节点开始逐色试探，遇到冲突就回溯，不额外做前向检查、变量排序或取值排序。",
      visual: "适合作为基线版本观察搜索树如何迅速膨胀，以及回溯是怎样逐层展开的。",
      time: "最坏情况下仍是指数级搜索；因为没有额外启发式，单步开销最低，但总搜索量通常最大。",
      space: "主要消耗在递归栈与邻接结构本身，不需要维护额外域状态。",
    },
  ),
  V1: makeVariant(
    "V1",
    "Backtracking + Forward Checking",
    "在 B0 基础上加入前向检查",
    "#cc5a71",
    { forwardChecking: true, mrv: false, degreeTieBreak: false, lcv: false, symmetryBreaking: false, cliqueBound: false, componentDecomposition: false },
    {
      core: "每次着色后主动删除所有未着色邻居域中的该颜色，若有邻居域被削空则立即回溯。",
      visual: "让邻居域矩阵实时收缩，被删掉的颜色单元闪烁，清晰展示 FC 的约束传播。",
      time: "最坏仍指数级，但每次赋值多付出 O(d) 传播代价，通常能显著缩小搜索树。",
      space: "需要维护 O(NM) 的域状态，并记录每层传播日志以恢复现场。",
    },
  ),
  V2: makeVariant(
    "V2",
    "B1 + MRV",
    "在 B1 基础上加入最小剩余值变量选择",
    "#f28f3b",
    { forwardChecking: true, mrv: true, degreeTieBreak: false, lcv: false, symmetryBreaking: false, cliqueBound: false, componentDecomposition: false },
    {
      core: "遵循 Fail-First，动态选择当前可用颜色最少的节点，让冲突更早暴露。",
      visual: "每次选点前展示所有未着色节点的域大小，最终选中的“最紧节点”会被强调。",
      time: "在 FC 基础上增加每步 O(N) 的选点扫描，实践中往往能换来更少的回溯。",
      space: "与 FC 相同，另加少量 MRV 候选统计。",
    },
  ),
  V3: makeVariant(
    "V3",
    "B2 + Degree Tie-Break",
    "在 B2 基础上加入 Degree 作为平局选择策略",
    "#7a306c",
    { forwardChecking: true, mrv: true, degreeTieBreak: true, lcv: false, symmetryBreaking: false, cliqueBound: false, componentDecomposition: false },
    {
      core: "当多个节点的剩余可选颜色数相同，优先选择静态度数更高的节点，让约束传播尽快覆盖更多邻居。",
      visual: "MRV 候选会先并排出现，再由 Degree 标记打破平局，突出“同域大小下谁更关键”。",
      time: "相比 V2 只多出很小的平局比较开销，但在稠密图上通常能进一步减少无效回溯。",
      space: "与 V2 基本一致，只额外保留少量度数元数据。",
    },
  ),
  V4: makeVariant(
    "V4",
    "B3 + LCV",
    "在 B3 基础上加入最小约束值排序",
    "#1c7c54",
    { forwardChecking: true, mrv: true, degreeTieBreak: true, lcv: true, symmetryBreaking: false, cliqueBound: false, componentDecomposition: false },
    {
      core: "在 MRV 和 Degree 选定节点后，再让对邻居约束最小的颜色优先尝试，尽量把成功分支提到前面。",
      visual: "每个候选颜色都会展示影响分数，能够直接看出 LCV 如何改变试色顺序。",
      time: "相比 V3 多出颜色影响评估成本，但常能显著压缩搜索树深处的回溯次数。",
      space: "与 V3 相同，另外需要暂存颜色评分结果。",
    },
  ),
  V5: makeVariant(
    "V5",
    "B4 + Structured Pruning",
    "在 B4 基础上加入结构化剪枝",
    "#0b4f6c",
    { forwardChecking: true, mrv: true, degreeTieBreak: true, lcv: true, symmetryBreaking: true, cliqueBound: true, componentDecomposition: true },
    {
      core: "保留 B4 的启发式栈，并进一步加入颜色对称性剪枝、团下界剪枝和连通分量分解，集中消除结构性冗余。",
      visual: "除了 MRV、Degree、LCV 外，还会额外强调“开局下界剪枝”和“等价颜色分支合并”等结构化优化来源。",
      time: "单步分析开销最高，但通常能最有效地缩短整体搜索路径，尤其适合大规模困难实例。",
      space: "除域矩阵与评分信息外，还需要保存结构化剪枝相关的中间状态。",
    },
  ),
};

export const SAMPLE_GRAPHS = [
  {
    id: "course-map",
    name: "课程示例图",
    description: "9 个区域的近似地图图，适合展示基础回溯与颜色复用。",
    colorLimit: 4,
    nodes: [{ id: "A", x: 0.16, y: 0.18 }, { id: "B", x: 0.42, y: 0.12 }, { id: "C", x: 0.74, y: 0.16 }, { id: "D", x: 0.14, y: 0.48 }, { id: "E", x: 0.42, y: 0.42 }, { id: "F", x: 0.74, y: 0.44 }, { id: "G", x: 0.22, y: 0.78 }, { id: "H", x: 0.50, y: 0.78 }, { id: "I", x: 0.82, y: 0.74 }],
    edges: [["A", "B"], ["A", "D"], ["B", "C"], ["B", "E"], ["C", "E"], ["C", "F"], ["D", "E"], ["D", "G"], ["E", "F"], ["E", "G"], ["E", "H"], ["F", "H"], ["F", "I"], ["G", "H"], ["H", "I"]],
  },
  {
    id: "fc-lab",
    name: "FC 传播图",
    description: "10 个节点的中高约束图，前向检查与 MRV 的收益更明显。",
    colorLimit: 4,
    nodes: [{ id: "A", x: 0.10, y: 0.24 }, { id: "B", x: 0.32, y: 0.10 }, { id: "C", x: 0.58, y: 0.14 }, { id: "D", x: 0.82, y: 0.26 }, { id: "E", x: 0.16, y: 0.52 }, { id: "F", x: 0.42, y: 0.44 }, { id: "G", x: 0.68, y: 0.46 }, { id: "H", x: 0.90, y: 0.56 }, { id: "I", x: 0.34, y: 0.80 }, { id: "J", x: 0.72, y: 0.78 }],
    edges: [["A", "B"], ["A", "E"], ["A", "F"], ["B", "C"], ["B", "F"], ["B", "G"], ["C", "D"], ["C", "F"], ["C", "G"], ["D", "G"], ["D", "H"], ["E", "F"], ["E", "G"], ["E", "I"], ["F", "G"], ["F", "I"], ["F", "J"], ["G", "H"], ["G", "J"], ["H", "J"], ["I", "J"]],
  },
  {
    id: "mrv-tie",
    name: "MRV / Degree 平局图",
    description: "专门构造的平局场景，用于观察 Degree tie-break 与 LCV。",
    colorLimit: 4,
    nodes: [{ id: "A", x: 0.16, y: 0.18 }, { id: "B", x: 0.40, y: 0.12 }, { id: "C", x: 0.66, y: 0.14 }, { id: "D", x: 0.86, y: 0.28 }, { id: "E", x: 0.14, y: 0.52 }, { id: "F", x: 0.40, y: 0.46 }, { id: "G", x: 0.66, y: 0.50 }, { id: "H", x: 0.88, y: 0.58 }, { id: "I", x: 0.30, y: 0.82 }, { id: "J", x: 0.58, y: 0.82 }],
    edges: [["A", "B"], ["A", "E"], ["A", "F"], ["B", "C"], ["B", "F"], ["B", "G"], ["C", "D"], ["C", "F"], ["C", "G"], ["D", "G"], ["D", "H"], ["E", "F"], ["E", "G"], ["E", "I"], ["F", "G"], ["F", "I"], ["F", "J"], ["G", "H"], ["G", "J"], ["H", "J"], ["I", "J"]],
  },
  {
    id: "k4-prune",
    name: "K4 团下界演示",
    description: "当颜色数小于最大团大小时，搜索会在入口处直接结束。",
    colorLimit: 3,
    nodes: [{ id: "A", x: 0.24, y: 0.24 }, { id: "B", x: 0.76, y: 0.24 }, { id: "C", x: 0.24, y: 0.76 }, { id: "D", x: 0.76, y: 0.76 }],
    edges: [["A", "B"], ["A", "C"], ["A", "D"], ["B", "C"], ["B", "D"], ["C", "D"]],
  },
];

function normalizeGraph(graph) {
  const nodes = graph.nodes.map((node, index) => ({ ...node, index }));
  const byId = new Map(nodes.map((node) => [node.id, node.index]));
  const edges = graph.edges.map(([a, b]) => [byId.get(a), byId.get(b)]);
  const adjacency = Array.from({ length: nodes.length }, () => new Set());
  for (const [a, b] of edges) adjacency[a].add(b), adjacency[b].add(a);
  const degree = adjacency.map((set) => set.size);
  const staticOrder = nodes.map((node) => node.index).sort((a, b) => degree[b] - degree[a] || nodes[a].id.localeCompare(nodes[b].id));
  const orderRank = new Map(staticOrder.map((nodeIndex, rank) => [nodeIndex, rank]));
  return { ...graph, nodes, edges, adjacency, degree, staticOrder, orderRank };
}

function resolveGraph(graphOrId) {
  if (typeof graphOrId !== "string") return graphOrId;
  const graph = SAMPLE_GRAPHS.find((item) => item.id === graphOrId);
  if (!graph) throw new Error(`Unknown graph: ${graphOrId}`);
  return graph;
}

function exactCliqueSize(model) {
  const all = new Set(model.nodes.map((node) => node.index));
  let best = 0;
  const inter = (set, neighbors) => new Set([...set].filter((value) => neighbors.has(value)));
  function bk(r, p, x) {
    if (!p.size && !x.size) return void (best = Math.max(best, r.size));
    if (r.size + p.size <= best) return;
    const pivot = [...new Set([...p, ...x])][0];
    const avoid = pivot === undefined ? new Set() : model.adjacency[pivot];
    for (const value of [...p].filter((item) => !avoid.has(item))) {
      bk(new Set([...r, value]), inter(p, model.adjacency[value]), inter(x, model.adjacency[value]));
      p.delete(value);
      x.add(value);
    }
  }
  bk(new Set(), all, new Set());
  return best;
}

function usedColorsOf(assignment) {
  return new Set(assignment.filter((color) => color !== null));
}

function colorName(color) {
  return COLOR_PALETTE.find((item) => item.id === color)?.name ?? `颜色 ${color}`;
}

function consistent(model, assignment, nodeIndex, color) {
  for (const neighbor of model.adjacency[nodeIndex]) if (assignment[neighbor] === color) return false;
  return true;
}

function availableColors(model, assignment, domains, nodeIndex, palette) {
  return palette.filter((color) => domains[nodeIndex].has(color) && consistent(model, assignment, nodeIndex, color));
}

function impact(model, assignment, domains, nodeIndex, color) {
  let total = 0;
  for (const neighbor of model.adjacency[nodeIndex]) if (assignment[neighbor] === null && domains[neighbor].has(color)) total += 1;
  return total;
}

function snapshotDomains(domains, assignment) {
  return domains.map((domain, index) => (assignment[index] !== null ? [assignment[index]] : [...domain].sort((a, b) => a - b)));
}

function assignmentMap(model, assignment) {
  return Object.fromEntries(model.nodes.map((node) => [node.id, assignment[node.index]]));
}

export function validateColoring(graphOrModel, assignment) {
  const model = graphOrModel.nodes?.[0]?.index !== undefined ? graphOrModel : normalizeGraph(graphOrModel);
  const values = Array.isArray(assignment) ? assignment : model.nodes.map((node) => assignment[node.id] ?? null);
  if (values.some((color) => color === null || color === undefined)) return false;
  for (const [a, b] of model.edges) if (values[a] === values[b]) return false;
  return true;
}

export function runVariant(graphOrId, variantId, requestedColorLimit) {
  const now = () => (globalThis.performance?.now ? globalThis.performance.now() : Date.now());
  const startedAt = now();
  const graph = resolveGraph(graphOrId);
  const model = normalizeGraph(graph);
  const variant = VARIANTS[variantId];
  if (!variant) throw new Error(`Unknown variant: ${variantId}`);
  const colorLimit = requestedColorLimit ?? graph.colorLimit ?? 4;
  const palette = COLOR_PALETTE.slice(0, colorLimit).map((item) => item.id);
  const assignment = Array(model.nodes.length).fill(null);
  const domains = Array.from({ length: model.nodes.length }, () => new Set(palette));
  const metrics = {
    steps: 0,
    assignments: 0,
    backtracks: 0,
    prunes: 0,
    deadEnds: 0,
    selections: 0,
    maxDepth: 0,
    searchNodes: 0,
    colorTrials: 0,
    prunedBranches: 0,
    overheadOps: 0,
    runtimeMs: 0,
  };
  const stack = [];
  const events = [];
  const cliqueSize = exactCliqueSize(model);

  function event(type, payload = {}) {
    const used = [...usedColorsOf(assignment)].sort((a, b) => a - b);
    events.push({
      step: metrics.steps++,
      type,
      title: payload.title ?? "",
      detail: payload.detail ?? "",
      color: payload.color ?? null,
      selectedNode: payload.selectedNode == null ? null : model.nodes[payload.selectedNode].id,
      focusNodes: (payload.focusNodes ?? []).map((index) => model.nodes[index].id),
      highlight: payload.highlight ?? [],
      metrics: { ...metrics, usedColors: used.length },
      usedColors: used,
      stack: stack.map((item) => ({ node: model.nodes[item.nodeIndex].id, color: item.color })),
      assignment: assignment.slice(),
      domains: snapshotDomains(domains, assignment),
      meta: payload.meta ?? {},
    });
  }

  event("start-search", {
    title: "开始搜索",
    detail: `${variant.id} 启动，颜色上限为 ${colorLimit}。静态顺序为 ${model.staticOrder.map((index) => model.nodes[index].id).join(" -> ")}。`,
    highlight: ["init-order"],
    meta: { staticOrder: model.staticOrder.map((index) => model.nodes[index].id), cliqueSize },
  });

  if (variant.cliqueBound && cliqueSize > colorLimit) {
    metrics.prunedBranches += 1;
    metrics.runtimeMs = now() - startedAt;
    event("clique-prune", {
      title: "团下界剪枝",
      detail: `最大团为 ${cliqueSize}，已超过颜色上限 ${colorLimit}，因此无需进入搜索。`,
      highlight: ["clique-bound", "fail"],
      meta: { cliqueSize, colorLimit },
    });
    return { graph: model, variant, colorLimit, success: false, assignment: assignmentMap(model, assignment), palette, events, metrics, cliqueSize };
  }

  function chooseNode() {
    const remaining = model.staticOrder.filter((index) => assignment[index] === null);
    if (!remaining.length) return null;
    if (!variant.mrv) {
      metrics.selections += 1;
      return { nodeIndex: remaining[0], heuristics: ["DegreeOrder"], candidates: remaining.map((index) => ({ id: model.nodes[index].id, degree: model.degree[index], domainSize: availableColors(model, assignment, domains, index, palette).length })) };
    }
    metrics.overheadOps += remaining.length;
    const candidates = remaining.map((index) => ({ nodeIndex: index, degree: model.degree[index], domainSize: availableColors(model, assignment, domains, index, palette).length, rank: model.orderRank.get(index) }));
    const minDomain = Math.min(...candidates.map((item) => item.domainSize));
    let finalists = candidates.filter((item) => item.domainSize === minDomain);
    const heuristics = ["MRV"];
    if (variant.degreeTieBreak && finalists.length > 1) {
      metrics.overheadOps += finalists.length;
      const maxDegree = Math.max(...finalists.map((item) => item.degree));
      finalists = finalists.filter((item) => item.degree === maxDegree);
      heuristics.push("Degree");
    }
    finalists.sort((a, b) => a.rank - b.rank);
    metrics.selections += 1;
    return { nodeIndex: finalists[0].nodeIndex, heuristics, candidates: candidates.map((item) => ({ id: model.nodes[item.nodeIndex].id, degree: item.degree, domainSize: item.domainSize })), tieCandidates: finalists.map((item) => model.nodes[item.nodeIndex].id) };
  }

  function colorOrder(nodeIndex) {
    const avail = availableColors(model, assignment, domains, nodeIndex, palette);
    let ordered = [...avail].sort((a, b) => a - b);
    if (variant.symmetryBreaking) {
      const used = usedColorsOf(assignment);
      const oldColors = ordered.filter((color) => used.has(color));
      const fresh = ordered.filter((color) => !used.has(color));
      ordered = [...oldColors];
      if (fresh.length) ordered.push(fresh[0]);
    }
    if (!variant.lcv) {
      metrics.prunedBranches += Math.max(0, palette.length - ordered.length);
      return {
        colors: ordered,
        lcvScores: null,
        availableColors: avail,
        allPaletteColors: [...palette],
        skippedColors: palette.filter((color) => !ordered.includes(color)),
      };
    }
    metrics.overheadOps += ordered.length * model.adjacency[nodeIndex].size;
    const scores = ordered.map((color) => ({ color, impact: impact(model, assignment, domains, nodeIndex, color), colorName: colorName(color) }));
    scores.sort((a, b) => a.impact - b.impact || a.color - b.color);
    const lcvOrdered = scores.map((item) => item.color);
    metrics.prunedBranches += Math.max(0, palette.length - lcvOrdered.length);
    return {
      colors: lcvOrdered,
      lcvScores: scores,
      availableColors: avail,
      allPaletteColors: [...palette],
      skippedColors: palette.filter((color) => !lcvOrdered.includes(color)),
    };
  }

  function restore(changes) {
    for (let i = changes.length - 1; i >= 0; i -= 1) domains[changes[i].nodeIndex].add(changes[i].color);
  }

  function propagate(nodeIndex, color) {
    const changes = [];
    event("forward-check", {
      title: "触发前向检查",
      detail: `节点 ${model.nodes[nodeIndex].id} 着为 ${colorName(color)} 后，开始收缩所有未着色邻居的颜色域。`,
      selectedNode: nodeIndex,
      color,
      focusNodes: [nodeIndex, ...model.adjacency[nodeIndex]],
      highlight: ["forward-check"],
    });
    metrics.overheadOps += model.adjacency[nodeIndex].size;
    for (const neighbor of model.adjacency[nodeIndex]) {
      if (assignment[neighbor] !== null || !domains[neighbor].has(color)) continue;
      domains[neighbor].delete(color);
      changes.push({ nodeIndex: neighbor, color });
      metrics.prunes += 1;
      event("domain-prune", {
        title: "邻居域削减",
        detail: `删除邻居 ${model.nodes[neighbor].id} 域中的 ${colorName(color)}，其剩余域大小为 ${domains[neighbor].size}。`,
        selectedNode: nodeIndex,
        color,
        focusNodes: [nodeIndex, neighbor],
        highlight: ["forward-check"],
      });
      if (!domains[neighbor].size) {
        metrics.deadEnds += 1;
        metrics.prunedBranches += 1;
        event("domain-wipeout", {
          title: "域被削空",
          detail: `邻居 ${model.nodes[neighbor].id} 已无可用颜色，当前分支直接失败。`,
          selectedNode: nodeIndex,
          color,
          focusNodes: [nodeIndex, neighbor],
          highlight: ["wipeout", "backtrack"],
        });
        return { ok: false, changes };
      }
    }
    return { ok: true, changes };
  }

  function search(depth) {
    metrics.searchNodes += 1;
    metrics.maxDepth = Math.max(metrics.maxDepth, depth);
    const choice = chooseNode();
    if (!choice) {
      event("success", { title: "找到完整着色", detail: `所有节点均已着色，${variant.id} 成功结束。`, highlight: ["recurse"] });
      return true;
    }
    const nodeIndex = choice.nodeIndex;
    const nodeId = model.nodes[nodeIndex].id;
    event("select-node", {
      title: "选择下一个节点",
      detail: variant.mrv ? `${choice.heuristics.join(" + ")} 选择节点 ${nodeId}。` : `沿静态度数顺序选择节点 ${nodeId}。`,
      selectedNode: nodeIndex,
      focusNodes: [nodeIndex],
      highlight: ["select-node"],
      meta: { heuristics: choice.heuristics, candidates: choice.candidates, tieCandidates: choice.tieCandidates ?? [] },
    });
    const ordered = colorOrder(nodeIndex);
    event("order-colors", {
      title: "生成颜色候选顺序",
      detail: ordered.colors.length ? `节点 ${nodeId} 的尝试顺序为 ${ordered.colors.map((color) => colorName(color)).join(" -> ")}。` : `节点 ${nodeId} 当前无合法颜色。`,
      selectedNode: nodeIndex,
      focusNodes: [nodeIndex],
      highlight: ["order-colors"],
      meta: {
        lcvScores: ordered.lcvScores,
        orderedColors: ordered.colors,
        availableColors: ordered.availableColors,
        allPaletteColors: ordered.allPaletteColors,
        skippedColors: ordered.skippedColors,
      },
    });
    if (!ordered.colors.length) {
      metrics.deadEnds += 1;
      metrics.prunedBranches += 1;
      event("dead-end", { title: "无可用颜色", detail: `节点 ${nodeId} 没有合法颜色可试。`, selectedNode: nodeIndex, focusNodes: [nodeIndex], highlight: ["fail"] });
      return false;
    }
    for (const color of ordered.colors) {
      metrics.colorTrials += 1;
      event("try-color", { title: "尝试颜色", detail: `尝试将节点 ${nodeId} 着为 ${colorName(color)}。`, selectedNode: nodeIndex, color, focusNodes: [nodeIndex], highlight: ["try-color"] });
      if (!consistent(model, assignment, nodeIndex, color)) {
        metrics.prunedBranches += 1;
        continue;
      }
      assignment[nodeIndex] = color;
      stack.push({ nodeIndex, color });
      metrics.assignments += 1;
      event("assign-color", { title: "确认着色", detail: `节点 ${nodeId} 当前着为 ${colorName(color)}，已使用颜色数为 ${usedColorsOf(assignment).size}。`, selectedNode: nodeIndex, color, focusNodes: [nodeIndex], highlight: ["assign-color"] });
      let changes = [];
      let ok = true;
      if (variant.forwardChecking) ({ ok, changes } = propagate(nodeIndex, color));
      if (ok) {
        event("recurse", { title: "深入下一层", detail: `以 ${nodeId} = ${colorName(color)} 为前提继续搜索。`, selectedNode: nodeIndex, color, focusNodes: [nodeIndex], highlight: ["recurse"] });
        if (search(depth + 1)) return true;
      }
      if (variant.forwardChecking) restore(changes);
      assignment[nodeIndex] = null;
      stack.pop();
      metrics.backtracks += 1;
      metrics.prunedBranches += 1;
      event("backtrack", { title: "执行回溯", detail: `撤销节点 ${nodeId} = ${colorName(color)}，恢复现场并尝试下一个分支。`, selectedNode: nodeIndex, color, focusNodes: [nodeIndex], highlight: ["backtrack"] });
    }
    metrics.deadEnds += 1;
    metrics.prunedBranches += 1;
    event("dead-end", { title: "当前节点全部尝试失败", detail: `节点 ${nodeId} 的全部候选颜色都已失败。`, selectedNode: nodeIndex, focusNodes: [nodeIndex], highlight: ["fail"] });
    return false;
  }

  const success = search(0);
  if (!success) event("failure", { title: "搜索结束", detail: `在颜色上限 ${colorLimit} 下，${variant.id} 未找到可行着色。`, highlight: ["fail"] });
  metrics.runtimeMs = now() - startedAt;
  return { graph: model, variant, colorLimit, success, assignment: assignmentMap(model, assignment), palette, events, metrics, cliqueSize };
}

export function runAllVariants(graphOrId, colorLimit) {
  return Object.keys(VARIANTS).map((variantId) => runVariant(graphOrId, variantId, colorLimit));
}
