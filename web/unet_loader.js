import { app } from "../../scripts/app.js";
import { showModelInfo } from "./model_info_dialog.js";

app.registerExtension({
  name: "shanksimi.UNETLoaderInfo",
  nodeCreated(node) {
    if (node.comfyClass !== "ShankUNETLoader") return;

    let dialog;
    const info = node.addWidget("button", "ⓘ Thông tin Civitai", null, async () => {
      if (dialog?.open) return;
      const name = node.widgets?.find(widget => widget.name === "unet_name")?.value;
      await showModelInfo(name, "unet-info", opened => { dialog = opened; });
    }, { serialize: false });
    info.serialize = false;
  },
});
