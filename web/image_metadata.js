import { app } from "../../scripts/app.js";

app.registerExtension({
  name: "shanksimi.Metadata",
  nodeCreated(node) {
    if (node.comfyClass !== "ShankMetadata") return;
    const configure = node.onConfigure;
    node.onConfigure = function (...args) {
      configure?.apply(this, args);
      for (const widget of this.widgets ?? []) {
        if ((widget.name === "positive" || widget.name === "negative") && widget.value === "unknown") {
          widget.value = "";
        }
      }
    };
  },
});
