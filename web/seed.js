import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const nodeType = "ShankSeed";
const limit = 2 ** 50;
const modes = new Set([-1, -2, -3]);
const controls = new WeakMap();

function randomSeed() {
  return Math.floor(Math.random() * (limit + 1));
}

function resolveSeed(value, previous) {
  if (!modes.has(value)) return value;
  if (value === -1 || previous === undefined) return randomSeed();
  const next = previous + (value === -2 ? 1 : -1);
  return next < -limit || next > limit || modes.has(next) ? randomSeed() : next;
}

app.registerExtension({
  name: "shanksimi.SeedControl",
  setup() {
    const queuePrompt = api.queuePrompt;
    api.queuePrompt = async function (index, prompt, ...args) {
      const workflowNodes = new Map((prompt.workflow?.nodes || []).map(node => [String(node.id), node]));
      for (const [id, entry] of Object.entries(prompt.output || {})) {
        if (entry.class_type !== nodeType || !Number.isInteger(entry.inputs?.seed)) continue;
        const state = controls.get(app.graph.getNodeById(id));
        const configured = entry.inputs.seed;
        const actual = resolveSeed(configured, state?.lastSeed);
        entry.inputs.seed = actual;
        const values = workflowNodes.get(id)?.widgets_values;
        if (values?.length) values[0] = actual;
        if (state) {
          state.lastSeed = actual;
          state.lastButton.name = "♻ Use Last Seed (" + actual + ")";
          state.node.setDirtyCanvas(true, true);
        }
      }
      return queuePrompt.call(this, index, prompt, ...args);
    };
  },
  nodeCreated(node) {
    if (node.comfyClass !== nodeType) return;
    const seed = node.widgets?.find(widget => widget.name === "seed");
    if (!seed) return;
    const controlIndex = node.widgets.findIndex(widget => widget.name === "control_after_generate");
    if (controlIndex !== -1) node.widgets.splice(controlIndex, 1);
    const state = { node, lastSeed: undefined };
    const button = (label, callback) => {
      const widget = node.addWidget("button", label, null, callback, { serialize: false });
      widget.serialize = false;
      return widget;
    };
    const setSeed = value => {
      seed.value = value;
      node.setDirtyCanvas(true, true);
    };
    button("🎲 Randomize Each Time", () => setSeed(-1));
    button("🎲 New Fixed Random", () => setSeed(randomSeed()));
    state.lastButton = button("♻ Use Last Seed", () => {
      if (state.lastSeed !== undefined) setSeed(state.lastSeed);
    });
    controls.set(node, state);
  },
});
