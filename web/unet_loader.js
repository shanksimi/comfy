import { app } from "../../scripts/app.js";
import { showModelInfo } from "./model_info_dialog.js";

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

    let dialog;
    const info = node.addWidget("button", "ⓘ Thông tin Civitai", null, async () => {
      if (dialog?.open) return;
      const name = node.widgets?.find(widget => widget.name === filenameWidget)?.value;
      await showModelInfo(name, route, opened => { dialog = opened; });
    }, { serialize: false });
    info.serialize = false;
  },
});
