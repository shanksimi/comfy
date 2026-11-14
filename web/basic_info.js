import { app } from "../../scripts/app.js";

app.registerExtension({
  name: "shanksimi.BasicInfo",
  nodeCreated(node) {
    if (node.comfyClass !== "ShankBasicInfo") return;
    const ratio = node.widgets?.find(widget => widget.name === "aspect_ratio");
    if (!ratio) return;

    const dimensions = node.widgets.filter(widget => ["width", "height"].includes(widget.name));
    const sync = () => {
      const locked = Boolean(ratio.value && ratio.value !== "Custom");
      for (const widget of dimensions) widget.disabled = locked;
      node.setDirtyCanvas(true, true);
    };

    const changeRatio = ratio.callback;
    ratio.callback = function (...args) {
      const result = changeRatio?.apply(this, args);
      sync();
      return result;
    };

    const configure = node.onConfigure;
    node.onConfigure = function (...args) {
      const result = configure?.apply(this, args);
      sync();
      return result;
    };

    sync();
  },
});
