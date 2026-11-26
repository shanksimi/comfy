import { app } from "../../scripts/app.js";

app.registerExtension({
  name: "shanksimi.Metadata",
  nodeCreated(node) {
    if (node.comfyClass !== "ShankMetadata") return;
    const reportInputs = node.inputs?.filter(input => ["loras", "lllite_report"].includes(input.name)) ?? [];
    const denoiseWidget = node.widgets?.find(widget => widget.name === "denoise");
    function showDenoiseInput() {
      if (!denoiseWidget) return;

      const input = node.inputs?.find(slot => slot.name === "denoise");
      if (!input) {
        node.addInput("denoise", "FLOAT");
        return;
      }
      if (input.widget) {
        // Widget sockets can be hidden by the frontend. Keep the numeric
        // widget as a fallback and expose the existing socket in the input list.
        input.widget = undefined;
        input._widget = undefined;
        input.pos = undefined;
      }
    }

    const configure = node.onConfigure;
    node.onConfigure = function (...args) {
      configure?.apply(this, args);
      for (const input of reportInputs) {
        if (!this.inputs?.some(existing => existing.name === input.name)) {
          this.addInput(input.name, input.type);
        }
      }
      showDenoiseInput();
      for (const widget of this.widgets ?? []) {
        if ((widget.name === "positive" || widget.name === "negative") && widget.value === "unknown") {
          widget.value = "";
        }
      }
    };
    showDenoiseInput();
  },
});
