import { app } from "../../scripts/app.js";

const rowName = /^text_[1-9][0-9]*$/;

function addRowsWidget(node, name, [, options]) {
  const panel = document.createElement("div");
  panel.style.cssText = "display:grid;gap:4px;width:100%;color:var(--input-text,#ddd);font:12px sans-serif";
  let rows = [];
  let editors = new Map();

  function refreshConnections() {
    for (const input of node.inputs) {
      const editor = editors.get(input.name);
      if (!editor) continue;
      editor.disabled = input.link != null;
      editor.placeholder = editor.disabled ? "Đang dùng cổng STRING" : "Nhập văn bản";
    }
  }

  function syncInputs() {
    const names = new Set(rows.map(([key]) => key));
    for (let index = node.inputs.length - 1; index >= 0; index--) {
      const { name: key } = node.inputs[index];
      if (rowName.test(key) && !names.has(key)) node.removeInput(index);
    }
    rows.forEach(([key], index) => {
      const label = `Text ${index + 1}`;
      const input = node.inputs.find(slot => slot.name === key);
      if (input) input.label = label;
      else node.addInput(key, "STRING", { label });
    });
  }

  function button(label, title, onClick) {
    const item = document.createElement("button");
    item.type = "button";
    item.textContent = label;
    item.title = title;
    item.setAttribute("aria-label", title);
    item.style.cssText = "background:var(--comfy-input-bg,#222);color:inherit;border:1px solid var(--border-color,#555);border-radius:8px;cursor:pointer";
    item.onclick = onClick;
    return item;
  }

  function editRows(change) {
    node.graph?.beforeChange?.(node);
    change();
    syncInputs();
    render();
    const [width, height] = node.computeSize();
    node.setSize([Math.max(node.size[0], width), height]);
    node.graph?.afterChange?.(node);
    node.setDirtyCanvas(true, true);
  }

  function render() {
    panel.replaceChildren();
    editors = new Map();
    rows.forEach((row, index) => {
      const [key, value] = row;
      const label = `Text ${index + 1}`;
      const line = document.createElement("div");
      line.style.cssText = "display:grid;grid-template-columns:48px minmax(0,1fr) 26px;gap:4px;align-items:center;height:44px";
      const caption = document.createElement("span");
      caption.textContent = label;
      const editor = document.createElement("textarea");
      editor.style.cssText = "box-sizing:border-box;width:100%;height:100%;resize:none;padding:4px;background:var(--comfy-input-bg,#222);color:inherit;border:1px solid var(--border-color,#555);border-radius:6px";
      editor.value = value;
      editor.setAttribute("aria-label", label);
      editor.oninput = () => {
        row[1] = editor.value;
        node.setDirtyCanvas(true, true);
      };
      editor.onchange = () => node.graph?.afterChange?.(node);
      editors.set(key, editor);
      line.append(caption, editor, button("×", `Xoá ${label}`, () => editRows(() => rows.splice(index, 1))));
      panel.append(line);
    });
    const add = button("+ Thêm dòng", "Thêm dòng văn bản", () => editRows(() => {
      const next = 1 + rows.reduce((max, [key]) => Math.max(max, Number(key.slice(5))), 0);
      rows.push([`text_${next}`, ""]);
    }));
    add.style.height = "24px";
    panel.append(add);
    refreshConnections();
  }

  function restore(value) {
    let saved;
    try {
      saved = JSON.parse(value);
    } catch {
      return;
    }
    if (!Array.isArray(saved) || !saved.every(row => Array.isArray(row) && row.length === 2
      && typeof row[0] === "string" && rowName.test(row[0]) && typeof row[1] === "string")
      || new Set(saved.map(([key]) => key)).size !== saved.length) return;
    rows = saved;
    render();
  }

  const height = () => rows.length * 48 + 24;
  const widget = node.addDOMWidget(name, "custom", panel, {
    socketless: true,
    getValue: () => JSON.stringify(rows),
    setValue: restore,
    getMinHeight: height,
    getMaxHeight: height,
  });
  widget.computeSize = width => [width, height()];

  const onConfigure = node.onConfigure;
  node.onConfigure = function (...args) {
    onConfigure?.apply(this, args);
    syncInputs();
    refreshConnections();
  };
  const onConnectionsChange = node.onConnectionsChange;
  node.onConnectionsChange = function (...args) {
    onConnectionsChange?.apply(this, args);
    refreshConnections();
  };

  restore(options.default);
  syncInputs();
  return { widget, minWidth: 300 };
}

app.registerExtension({
  name: "shanksimi.ConcatenateText",
  getCustomWidgets() {
    return { SHANK_CONCATENATE_ROWS: addRowsWidget };
  },
});
