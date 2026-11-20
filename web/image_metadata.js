import { app } from "../../scripts/app.js";

app.registerExtension({
  name: "shanksimi.Metadata",
  nodeCreated(node) {
    if (node.comfyClass !== "ShankMetadata") return;
    const reportInputs = node.inputs?.filter(input => ["loras", "lllite_report"].includes(input.name)) ?? [];
    const configure = node.onConfigure;
    node.onConfigure = function (...args) {
      configure?.apply(this, args);
      for (const input of reportInputs) {
        if (!this.inputs?.some(existing => existing.name === input.name)) {
          this.addInput(input.name, input.type);
        }
      }
      for (const widget of this.widgets ?? []) {
        if ((widget.name === "positive" || widget.name === "negative") && widget.value === "unknown") {
          widget.value = "";
        }
      }
    };
  },
});
