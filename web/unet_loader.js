import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
  name: "shanksimi.UNETLoaderInfo",
  nodeCreated(node) {
    if (node.comfyClass !== "ShankUNETLoader") return;

    let dialog;
    const info = node.addWidget("button", "ⓘ Thông tin Civitai", null, async () => {
      if (dialog?.open) return;
      const name = node.widgets?.find(widget => widget.name === "unet_name")?.value;
      dialog = document.createElement("dialog");
      dialog.style.cssText = "max-width:min(560px,90vw);background:var(--comfy-menu-bg,#222);color:var(--input-text,#eee);padding:20px;border-radius:8px";
      const heading = document.createElement("h3");
      heading.textContent = name || "Thông tin Civitai";
      const body = document.createElement("div");
      body.textContent = name ? "Đang kiểm tra thông tin đã lưu…" : "Hãy chọn model trước.";
      const close = document.createElement("button");
      close.textContent = "Đóng";
      close.onclick = () => dialog.close();
      const currentDialog = dialog;
      dialog.addEventListener("close", () => currentDialog.remove(), { once: true });
      dialog.append(heading, body, close);
      document.body.append(dialog);
      dialog.showModal();
      close.focus();
      if (!name) return;

      try {
        const query = new URLSearchParams({ name });
        let data;
        while (currentDialog.open) {
          const response = await api.fetchApi("/shanksimi/unet-info?" + query, { cache: "no-store" });
          data = await response.json();
          if (!response.ok) throw new Error(data.error || response.statusText);
          if (response.status !== 202) break;
          body.textContent = "Đang tra Civitai trong nền. Bạn có thể đóng cửa sổ này và mở lại sau.";
          query.set("poll", "1");
          await new Promise(resolve => setTimeout(resolve, 2000));
        }
        if (!currentDialog.open) return;
        body.replaceChildren();
        for (const [label, value] of [
          ["Model", data.model], ["Phiên bản", data.version], ["Model nền", data.base_model],
          ["Trigger words", data.trained_words?.join(", ")],
        ]) {
          if (!value) continue;
          const row = document.createElement("p");
          row.textContent = label + ": " + value;
          body.append(row);
        }
        if (data.url) {
          const link = document.createElement("a");
          link.href = data.url;
          link.target = "_blank";
          link.rel = "noopener noreferrer";
          link.textContent = "Mở trên Civitai";
          body.append(link);
        }
      } catch (error) {
        body.textContent = error.message || "Không tải được thông tin.";
      }
    }, { serialize: false });
    info.serialize = false;
  },
});
