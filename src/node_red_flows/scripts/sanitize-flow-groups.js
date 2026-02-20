#!/usr/bin/env node
/**
 * Sanitize flow JSON: strip `g` (group) refs where parent is designer_node_existing.
 * Prevents Node-RED Flow editor addChild crash when loading flows.
 *
 * Usage: node scripts/sanitize-flow-groups.js [flowFile]
 * Default: flows_chat.json in same directory as script's parent
 */
const fs = require("fs");
const path = require("path");

const defaultFlowFile = path.join(__dirname, "..", "flows_chat.json");
const flowPath = process.argv[2] || defaultFlowFile;

function sanitize(flows) {
  if (!Array.isArray(flows)) return flows;
  if (flows.some((n) => n && typeof n === "object" && "nodes" in n)) return flows;

  const invalidGroupIds = new Set();
  for (const n of flows) {
    if (n && typeof n === "object" && n.type === "designer_node_existing" && typeof n.id === "string") {
      invalidGroupIds.add(n.id);
    }
  }

  let count = 0;
  for (const n of flows) {
    if (!n || typeof n !== "object") continue;
    const g = n.g;
    if (typeof g === "string" && invalidGroupIds.has(g)) {
      delete n.g;
      count++;
    }
  }
  return count;
}

try {
  const data = JSON.parse(fs.readFileSync(flowPath, "utf8"));
  const flows = Array.isArray(data) ? data : data.flows || [];
  const count = sanitize(flows);
  if (count > 0) {
    fs.writeFileSync(flowPath, JSON.stringify(flows, null, 2));
    console.log(`Sanitized ${count} group ref(s) in ${flowPath}`);
  } else {
    console.log(`No invalid group refs in ${flowPath}`);
  }
} catch (err) {
  console.error(err.message);
  process.exit(1);
}
