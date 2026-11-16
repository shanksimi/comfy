import { app } from "../../scripts/app.js";
import { showModelInfo } from "./model_info_dialog.js";
import { openModelPicker } from "./searchable_model_picker.js";

const loaderInfo = {
  ShankUNETLoader: ["unet_name", "unet-info"],
  UNETLoader: ["unet_name", "unet-info"],
  CheckpointLoaderSimple: ["ckpt_name", "checkpoint-info"],
  ShankCheckpointLoader: ["ckpt_name", "checkpoint-info"],
  CheckpointLoader: ["ckpt_name", "checkpoint-info"],
};

app.registerExtension({
  name: "shanksimi.UNETLoaderInfo",
  nodeCreated(node) {
    const settings = loaderInfo[node.comfyClass];
    if (!settings) return;
    const [filenameWidget, route] = settings;

    const findModel = node.addWidget("button", "Tìm model…", null, () => {
      const widget = node.widgets?.find(item => item.name === filenameWidget);
      if (!widget) return;
      const values = widget.options?.values;
      const choices = typeof values === "function" ? values.call(widget) : values;
      openModelPicker({
        title: route === "checkpoint-info" ? "Chọn checkpoint" : "Chọn model",
        choices: Array.isArray(choices) ? choices : [],
        current: widget.value,
        onSelect(name) {
          widget.value = name;
          widget.callback?.(name, app.canvas, node);
          node.setDirtyCanvas(true, true);
        },
      });
    }, { serialize: false });
    findModel.serialize = false;

    let dialog;
    const info = node.addWidget("button", "ⓘ Thông tin Civitai", null, async () => {
      if (dialog?.open) return;
      const name = node.widgets?.find(widget => widget.name === filenameWidget)?.value;
      await showModelInfo(name, route, opened => { dialog = opened; });
    }, { serialize: false });
    info.serialize = false;
  },
});
