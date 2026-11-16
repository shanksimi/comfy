export function openModelPicker({ title, choices, current, onSelect }) {
  const dialog = document.createElement("dialog");
  dialog.style.cssText = "width:min(570px,90vw);box-sizing:border-box;padding:16px;max-height:85vh;border:1px solid var(--border-color,#555);border-radius:10px;color:var(--input-text,#eee);background:var(--comfy-menu-bg,#222)";
  const heading = document.createElement("h3");
  heading.textContent = title;
  heading.style.margin = "0 0 12px";
  const search = document.createElement("input");
  search.type = "search";
  search.placeholder = "Lọc theo tên hoặc thư mục…";
  search.setAttribute("aria-label", search.placeholder);
  const list = document.createElement("select");
  list.size = 9;
  list.setAttribute("aria-label", "Kết quả tìm kiếm");
  for (const control of [search, list]) {
    control.style.cssText = "display:block;width:100%;box-sizing:border-box;margin-bottom:8px;padding:6px;color:inherit;background:var(--comfy-input-bg,#333);border:1px solid var(--border-color,#555);border-radius:4px";
  }
  const status = document.createElement("output");
  status.setAttribute("aria-live", "polite");
  const choose = document.createElement("button");
  choose.type = "button";
  choose.textContent = "Chọn";
  const cancel = document.createElement("button");
  cancel.type = "button";
  cancel.textContent = "Hủy";
  const actions = document.createElement("div");
  actions.style.cssText = "display:flex;justify-content:flex-end;gap:8px;margin-top:10px";
  actions.append(cancel, choose);
  const files = [...new Set([...choices, current].filter(name => typeof name === "string" && name))];
  function render() {
    const tokens = search.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    const filtered = files.filter(name => tokens.every(token => name.toLowerCase().includes(token)));
    const previous = list.value || current;
    list.replaceChildren(...filtered.map(name => new Option(name, name)));
    list.value = filtered.includes(previous) ? previous : filtered[0] ?? "";
    choose.disabled = !list.value;
    status.textContent = filtered.length ? `${filtered.length} model` : "Không tìm thấy file phù hợp.";
  }
  function select() {
    if (!list.value) return;
    const name = list.value;
    dialog.close();
    onSelect(name);
  }
  search.oninput = render;
  search.onkeydown = event => {
    if (event.key === "ArrowDown" && list.value) {
      event.preventDefault();
      list.focus();
    }
  };
  dialog.onkeydown = event => {
    if (event.key === "Enter" && (event.target === search || event.target === list)) {
      event.preventDefault();
      select();
    }
  };
  list.ondblclick = select;
  choose.onclick = select;
  cancel.onclick = () => dialog.close();
  dialog.addEventListener("close", () => dialog.remove(), { once: true });
  dialog.append(heading, search, list, status, actions);
  document.body.append(dialog);
  render();
  dialog.showModal();
  search.focus();
}
