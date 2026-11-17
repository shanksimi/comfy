import { app } from "../../scripts/app.js";

app.registerExtension({
  name: "shanksimi.Metadata",
  nodeCreated(node) {
    if (node.comfyClass !== "ShankMetadata") return;
    const lorasInput = node.inputs?.find(input => input.name === "loras");
    const configure = node.onConfigure;
    node.onConfigure = function (...args) {
      configure?.apply(this, args);
      if (lorasInput && !this.inputs?.some(input => input.name === lorasInput.name)) {
        this.addInput(lorasInput.name, lorasInput.type);
      }
      for (const widget of this.widgets ?? []) {
        if ((widget.name === "positive" || widget.name === "negative") && widget.value === "unknown") {
          widget.value = "";
        }
      }
    };
  },
});
