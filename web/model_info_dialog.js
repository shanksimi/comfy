import { api } from "../../scripts/api.js";

export async function showModelInfo(name, route, onOpen) {
  const dialog = document.createElement("dialog");
  dialog.style.cssText = "max-width:min(560px,90vw);background:var(--comfy-menu-bg,#222);color:var(--input-text,#eee);padding:20px;border-radius:8px";
  const heading = document.createElement("h3");
  heading.textContent = name || "Thông tin Civitai";
  const body = document.createElement("div");
  body.textContent = name ? "Đang kiểm tra thông tin đã lưu…" : "Hãy chọn model trước.";
  const close = document.createElement("button");
  close.textContent = "Đóng";
  close.onclick = () => dialog.close();
  dialog.addEventListener("close", () => dialog.remove(), { once: true });
  onOpen(dialog);
  dialog.append(heading, body, close);
  document.body.append(dialog);
  dialog.showModal();
  close.focus();
  if (!name) return;

  try {
    const query = new URLSearchParams({ name });
    let data;
    while (dialog.open) {
      const response = await api.fetchApi(`/shanksimi/${route}?${query}`, { cache: "no-store" });
      data = await response.json();
      if (!response.ok) throw new Error(data.error || response.statusText);
      if (response.status !== 202) break;
      body.textContent = "Đang tra Civitai trong nền. Bạn có thể đóng cửa sổ này và mở lại sau.";
      query.set("poll", "1");
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
    if (!dialog.open) return;
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
    if (!dialog.open) return;
    body.textContent = error.message || "Không tải được thông tin.";
  }
}
