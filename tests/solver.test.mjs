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

const preferredVariantIds = ["B0", "B1", "B2", "B3", "B4", "B5"].filter((variantId) => variantId in VARIANTS);
const legacyVariantIds = ["V0", "V1", "V2", "V3", "V4", "V5"].filter((variantId) => variantId in VARIANTS);
const variantIds = preferredVariantIds.length === 6 ? preferredVariantIds : legacyVariantIds;

assert.equal(variantIds.length, 6, "There should be six visualization variants");

for (const variantId of variantIds) {
  expectSolvedTrace(variantId);
}

for (const variantId of variantIds.slice(1)) {
  const trace = expectSolvedTrace(variantId);
  assert.ok(eventTypes(trace).has("domain-prune"), `${variantId} should surface FC domain pruning`);
}

for (const variantId of [variantIds[2], variantIds[4], variantIds[5]]) {
  const trace = expectSolvedTrace(variantId);
  assert.ok(
    trace.events.some(
      (event) => event.type === "select-node" && event.meta?.heuristics?.includes("MRV"),
    ),
    `${variantId} should annotate MRV-based node choices`,
  );
}

for (const variantId of [variantIds[3], variantIds[5]]) {
  const trace = expectSolvedTrace(variantId);
  assert.ok(
    trace.events.some(
      (event) => event.type === "order-colors" && Array.isArray(event.meta?.lcvScores),
    ),
    `${variantId} should expose LCV scores for value ordering`,
  );
}

for (const variantId of variantIds) {
  const trace = runVariant(impossibleClique, variantId, 3);
  assert.equal(trace.success, false, `${variantId} should reject K4 under 3 colors`);
  assert.ok(eventTypes(trace).has("clique-prune"), `${variantId} should report the clique lower-bound prune`);
}

console.log("solver.test.mjs passed");
