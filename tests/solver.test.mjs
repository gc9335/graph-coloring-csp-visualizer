import assert from "node:assert/strict";
import { runVariant, VARIANTS, validateColoring } from "../solver.js";

const triangleGraph = {
  id: "triangle",
  name: "Triangle",
  colorLimit: 3,
  nodes: [
    { id: "A", x: 0.2, y: 0.2 },
    { id: "B", x: 0.8, y: 0.2 },
    { id: "C", x: 0.5, y: 0.8 },
  ],
  edges: [
    ["A", "B"],
    ["B", "C"],
    ["A", "C"],
  ],
};

const impossibleClique = {
  id: "k4",
  name: "K4",
  colorLimit: 3,
  nodes: [
    { id: "A", x: 0.2, y: 0.2 },
    { id: "B", x: 0.8, y: 0.2 },
    { id: "C", x: 0.2, y: 0.8 },
    { id: "D", x: 0.8, y: 0.8 },
  ],
  edges: [
    ["A", "B"],
    ["A", "C"],
    ["A", "D"],
    ["B", "C"],
    ["B", "D"],
    ["C", "D"],
  ],
};

function eventTypes(trace) {
  return new Set(trace.events.map((event) => event.type));
}

function expectSolvedTrace(variantId) {
  const trace = runVariant(triangleGraph, variantId, 3);
  assert.equal(trace.variant.id, variantId, `${variantId} should report its variant id`);
  assert.equal(trace.success, true, `${variantId} should solve the triangle graph`);
  assert.ok(validateColoring(triangleGraph, trace.assignment), `${variantId} should return a valid coloring`);
  assert.ok(trace.events.length > 0, `${variantId} should produce a non-empty event trace`);
  assert.ok(eventTypes(trace).has("select-node"), `${variantId} should expose node selection events`);
  assert.ok(eventTypes(trace).has("assign-color"), `${variantId} should expose assignment events`);
  return trace;
}

assert.equal(Object.keys(VARIANTS).length, 6, "There should be six visualization variants");

for (const variantId of Object.keys(VARIANTS)) {
  expectSolvedTrace(variantId);
}

for (const variantId of ["V1", "V2", "V3", "V4", "V5"]) {
  const trace = expectSolvedTrace(variantId);
  assert.ok(eventTypes(trace).has("domain-prune"), `${variantId} should surface FC domain pruning`);
}

for (const variantId of ["V2", "V4", "V5"]) {
  const trace = expectSolvedTrace(variantId);
  assert.ok(
    trace.events.some(
      (event) => event.type === "select-node" && event.meta?.heuristics?.includes("MRV"),
    ),
    `${variantId} should annotate MRV-based node choices`,
  );
}

for (const variantId of ["V3", "V5"]) {
  const trace = expectSolvedTrace(variantId);
  assert.ok(
    trace.events.some(
      (event) => event.type === "order-colors" && Array.isArray(event.meta?.lcvScores),
    ),
    `${variantId} should expose LCV scores for value ordering`,
  );
}

for (const variantId of Object.keys(VARIANTS)) {
  const trace = runVariant(impossibleClique, variantId, 3);
  assert.equal(trace.success, false, `${variantId} should reject K4 under 3 colors`);
  assert.ok(eventTypes(trace).has("clique-prune"), `${variantId} should report the clique lower-bound prune`);
}

console.log("solver.test.mjs passed");
