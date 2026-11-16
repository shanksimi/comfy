import { api } from "../../scripts/api.js";

const styles = `
.shank-model-info { width:min(760px,90vw); max-height:88vh; box-sizing:border-box; padding:0; border:1px solid var(--border-color,#494949); border-radius:14px; background:var(--comfy-menu-bg,#202020); color:var(--input-text,#eee); }
.shank-model-info::backdrop { background:#0009; }
.shank-model-info header { display:flex; justify-content:space-between; align-items:flex-start; gap:14px; padding:16px 20px; border-bottom:1px solid var(--border-color,#494949); }
.shank-model-info h3, .shank-model-info h4, .shank-model-info dl { margin:0; }
.shank-model-info header small { display:block; margin-top:4px; overflow-wrap:anywhere; opacity:.72; }
.shank-model-info section { padding:18px 20px; }
.shank-model-info .info-grid { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1.2fr); gap:20px; }
.shank-model-info .info-grid.no-preview { grid-template-columns:1fr; }
.shank-model-info img { width:100%; max-height:460px; object-fit:contain; display:block; background:#111; border-radius:8px; }
.shank-model-info figure { margin:0; min-width:0; }
.shank-model-info nav, .shank-model-info .keyword-list { display:flex; flex-wrap:wrap; align-items:center; gap:6px; margin-top:8px; }
.shank-model-info table { border-collapse:collapse; width:100%; table-layout:fixed; }
.shank-model-info th, .shank-model-info td { padding:8px 9px; border-bottom:1px solid var(--border-color,#444); text-align:left; vertical-align:top; overflow-wrap:anywhere; }
.shank-model-info th { width:28%; font-size:12px; font-weight:600; color:var(--descrip-text,#bbb); }
.shank-model-info td { white-space:pre-wrap; }
.shank-model-info td .keywords { margin-top:0; }
.shank-model-info td .keyword-list { margin-top:0; }
.shank-model-info td a { margin-top:0; }
.shank-model-info .long-text { max-height:210px; overflow:auto; }
.shank-model-info .keywords { margin-top:18px; }
.shank-model-info label { display:inline-flex; gap:5px; align-items:center; overflow-wrap:anywhere; padding:4px 8px; border:1px solid var(--border-color,#555); border-radius:14px; cursor:pointer; }
.shank-model-info label:has(input:checked) { border-color:#76a9ff; background:#28436f; color:#fff; }
.shank-model-info button { border:1px solid var(--border-color,#555); border-radius:6px; padding:5px 9px; cursor:pointer; color:inherit; background:var(--comfy-input-bg,#333); }
.shank-model-info a { display:inline-block; margin-top:12px; color:#8db9ff; }
.shank-model-info output { font-size:12px; }
@media (max-width:560px) { .shank-model-info .info-grid { grid-template-columns:1fr; } }
`;

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function button(text, action) {
  const node = element("button", text);
  node.type = "button";
  node.onclick = action;
  return node;
}

function renderKeywords(words) {
  const block = element("div", undefined, "keywords");
  const list = element("div", undefined, "keyword-list");
  const checks = words.map(word => {
    const label = element("label");
    const input = element("input");
    input.type = "checkbox";
    label.append(input, element("span", word));
    list.append(label);
    return input;
  });
  const actions = element("nav");
  const status = element("output");
  status.setAttribute("aria-live", "polite");
  async function copy(values) {
    try {
      await navigator.clipboard.writeText(values.join(", "));
      status.textContent = "Đã sao chép";
    } catch {
      status.textContent = "Trình duyệt không cho sao chép. Bạn có thể chọn và copy bên dưới.";
      const manual = element("textarea");
      manual.value = values.join(", ");
      manual.readOnly = true;
      block.querySelector("textarea")?.remove();
      block.append(manual);
      manual.select();
    }
  }
  const copySelected = button("Copy đã chọn", () => copy(words.filter((_, index) => checks[index].checked)));
  copySelected.disabled = true;
  list.onchange = () => {
    copySelected.disabled = !checks.some(check => check.checked);
    status.textContent = "";
  };
  actions.append(copySelected, button("Copy tất cả", () => copy(words)), status);
  block.append(list, actions);
  return block;
}

function renderPreview(sources, name) {
  const figure = element("figure");
  const image = element("img");
  image.alt = "Ảnh mẫu cho " + name;
  image.referrerPolicy = "no-referrer";
  const nav = element("nav");
  const count = element("span");
  let index = 0;
  function show(offset = 0) {
    index = (index + offset + sources.length) % sources.length;
    image.src = sources[index];
    count.textContent = `${index + 1} / ${sources.length}`;
  }
  nav.append(button("‹", () => show(-1)), count, button("›", () => show(1)));
  figure.append(image);
  if (sources.length > 1) figure.append(nav);
  show();
  return figure;
}

function renderInfo(body, heading, data, name, route) {
  if (data.model) heading.textContent = data.model;
  const sources = Array.isArray(data.images) ? [...data.images] : [];
  if (data.has_local_preview) {
    const category = { "lora-info": "loras", "checkpoint-info": "checkpoints", "unet-info": "diffusion_models" }[route];
    const query = new URLSearchParams({ category, name });
    sources.unshift(api.apiURL("/shanksimi/model-preview?" + query));
  }
  const grid = element("div", undefined, sources.length ? "info-grid" : "info-grid no-preview");
  if (sources.length) grid.append(renderPreview(sources, name));
  const table = element("table");
  table.setAttribute("aria-label", "Thông tin model");
  const rows = element("tbody");
  function addRow(label, value) {
    if (!value) return;
    const row = element("tr");
    const nameCell = element("th", label);
    nameCell.scope = "row";
    const valueCell = element("td");
    if (typeof value === "string") valueCell.textContent = value;
    else valueCell.append(value);
    row.append(nameCell, valueCell);
    rows.append(row);
  }
  function longText(value) {
    if (typeof value !== "string" || !value.trim()) return null;
    const markup = element("template");
    // Sidecar descriptions may contain HTML. Read only its text; never mount this fragment.
    markup.innerHTML = value.replace(/<\/?(?:p|div|li|br|h[1-6])\b[^>]*>/gi, "\n");
    markup.content.querySelectorAll("script,style").forEach(node => node.remove());
    return element("div", markup.content.textContent.trim(), "long-text");
  }

  addRow("Tên", data.model || name);
  addRow("Loại model", data.model_type || {
    "checkpoint-info": "Checkpoint", "lora-info": "LoRA", "unet-info": "Diffusion model",
  }[route]);
  addRow("Phiên bản", data.version);
  addRow("Base model", data.base_model);
  addRow("Strength gợi ý", data.preferred_weight);
  addRow("Mô tả", longText(data.description));
  addRow("Ghi chú / hướng dẫn", longText(data.notes));
  if (Array.isArray(data.trained_words) && data.trained_words.length) {
    addRow(route === "lora-info" ? "Trigger words" : "Keywords", renderKeywords(data.trained_words));
  }
  if (typeof data.url === "string" && data.url.startsWith("https://civitai.com/models/")) {
    const link = element("a", "Mở trên Civitai");
    link.href = data.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    addRow("Civitai", link);
  }
  table.append(rows);
  grid.append(table);
  body.replaceChildren(grid);
}

export async function showModelInfo(name, route, onOpen) {
  const dialog = element("dialog", undefined, "shank-model-info");
  const style = element("style", styles);
  const heading = element("h3", "Thông tin model");
  const title = element("div");
  title.append(heading, element("small", name));
  const header = element("header");
  const close = button("Đóng", () => dialog.close());
  header.append(title, close);
  const body = element("section", name ? "Đang đọc thông tin đã lưu…" : "Hãy chọn model trước.");
  dialog.addEventListener("close", () => dialog.remove(), { once: true });
  onOpen(dialog);
  dialog.append(style, header, body);
  document.body.append(dialog);
  dialog.showModal();
  close.focus();
  if (!name) return;

  try {
    const query = new URLSearchParams({ name });
    while (dialog.open) {
      const response = await api.fetchApi(`/shanksimi/${route}?${query}`, { cache: "no-store" });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(data?.error || `Không tải được thông tin model (HTTP ${response.status}).`);
      }
      if (!data || typeof data !== "object" || Array.isArray(data)) {
        throw new Error("Máy chủ ComfyUI trả dữ liệu thông tin model không hợp lệ.");
      }
      if (!dialog.open) return;
      if (response.status !== 202) {
        renderInfo(body, heading, data, name, route);
        return;
      }
      body.textContent = "Đang tra Civitai trong nền. Bạn có thể đóng cửa sổ này và mở lại sau.";
      query.set("poll", "1");
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  } catch (error) {
    if (dialog.open) body.textContent = error.message || "Không tải được thông tin.";
  }
}
