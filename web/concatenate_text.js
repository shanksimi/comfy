import { app } from "../../scripts/app.js";

const rowName = /^text_[1-9][0-9]*$/;
const rowHeight = 24;

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

function addRowsWidget(node, name, [, options]) {
  let rows = [];
  const editors = new Map();

  function refreshConnections() {
    node.inputs.forEach((input, index) => {
      const entry = editors.get(input.name);
      if (!entry) return;
      const { editor, row } = entry;
      const linked = input.link != null;
      const source = linked && node.graph ? node.getInputNode(index) : null;
      const sourceTitle = linked ? (source?.getTitle?.() || source?.title || "Đang dùng cổng STRING") : "";
      const value = linked ? sourceTitle : row[1];
      if (editor.value !== value) editor.value = value;
      editor.disabled = linked;
      editor.title = sourceTitle;
    });
  }

  function editRows(change) {
    node.graph?.beforeChange?.(node);
    change();
    syncRows();
    const [width, height] = node.computeSize();
    node.setSize([Math.max(node.size[0], width), height]);
    node.graph?.afterChange?.(node);
    node.setDirtyCanvas(true, true);
  }

  function createEditor(key) {
    const line = document.createElement("div");
    line.className = "shank-concatenate-row";
    line.style.cssText = `display:grid;grid-template-columns:minmax(0,1fr) 26px;gap:4px;height:${rowHeight}px;padding:0 5px 0 20px;box-sizing:border-box;pointer-events:none;color:var(--input-text,#ddd);font:12px sans-serif`;
    const editor = document.createElement("textarea");
    editor.rows = 1;
    editor.wrap = "off";
    editor.placeholder = "Nhập văn bản";
    editor.style.cssText = "box-sizing:border-box;width:100%;height:100%;resize:none;scrollbar-width:none;padding:2px 5px;font:inherit;line-height:16px;background:var(--comfy-input-bg,#222);color:inherit;border:1px solid var(--border-color,#555);border-radius:6px";
    const remove = button("×", "Xoá dòng", () => editRows(() => {
      rows = rows.filter(([name]) => name !== key);
    }));
    line.append(editor, remove);
    const widget = node.addDOMWidget(key, "custom", line, {
      serialize: false,
      margin: 0,
      getValue: () => editors.get(key)?.row[1] ?? "",
      getMinHeight: () => rowHeight,
      getMaxHeight: () => rowHeight,
    });
    widget.serialize = false;
    widget.computeSize = width => [width, rowHeight];

    // ComfyUI hides connected widget controls by default. Keep the row visible
    // so it can display the source title and the remove button beside the socket.
    Object.defineProperties(widget, {
      computedDisabled: { get: () => false, set() {} },
      connectionSuppressed: { get: () => false, set() {} },
    });

    editor.oninput = () => {
      if (editor.disabled) return;
      editors.get(key).row[1] = editor.value;
      node.setDirtyCanvas(true, true);
    };
    editor.onchange = () => node.graph?.afterChange?.(node);
    return { editor, remove, widget };
  }

  function syncRows() {
    const names = new Set(rows.map(([key]) => key));
    for (let index = node.inputs.length - 1; index >= 0; index--) {
      const { name: key } = node.inputs[index];
      if (rowName.test(key) && !names.has(key)) node.removeInput(index);
    }
    for (const [key, { widget }] of editors) {
      if (names.has(key)) continue;
      if (node.removeWidget) node.removeWidget(widget);
      else {
        widget.onRemove?.();
        node.widgets.splice(node.widgets.indexOf(widget), 1);
      }
      editors.delete(key);
    }
    rows.forEach((row, index) => {
      const [key] = row;
      let entry = editors.get(key);
      if (!entry) {
        entry = createEditor(key);
        editors.set(key, entry);
      }
      entry.row = row;
      const label = `Dòng ${index + 1}`;
      entry.editor.setAttribute("aria-label", label);
      entry.remove.title = `Xoá ${label.toLowerCase()}`;
      entry.remove.setAttribute("aria-label", entry.remove.title);

      const socket = { widget: { name: key }, alwaysVisible: true, label: " " };
      const input = node.inputs.find(slot => slot.name === key);
      if (input) Object.assign(input, socket);
      else node.addInput(key, "STRING", socket);
    });
    let nextWidget = addWidget;
    for (let index = rows.length - 1; index >= 0; index--) {
      const widget = editors.get(rows[index][0]).widget;
      const current = node.widgets.indexOf(widget);
      if (node.widgets[current + 1] !== nextWidget) {
        node.widgets.splice(current, 1);
        node.widgets.splice(node.widgets.indexOf(nextWidget), 0, widget);
      }
      nextWidget = widget;
    }
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
    syncRows();
  }

  const add = button("+ Thêm dòng", "Thêm dòng văn bản", () => editRows(() => {
    const next = 1 + rows.reduce((max, [key]) => Math.max(max, Number(key.slice(5))), 0);
    rows.push([`text_${next}`, ""]);
  }));
  add.style.cssText += ";width:100%;height:24px";
  const addWidget = node.addDOMWidget(name, "custom", add, {
    socketless: true,
    margin: 2,
    getValue: () => JSON.stringify(rows),
    setValue: restore,
    onDraw: refreshConnections,
    getMinHeight: () => rowHeight,
    getMaxHeight: () => rowHeight,
  });
  addWidget.computeSize = width => [width, rowHeight];

  const onConfigure = node.onConfigure;
  node.onConfigure = function (...args) {
    onConfigure?.apply(this, args);
    syncRows();
  };
  const onConnectionsChange = node.onConnectionsChange;
  node.onConnectionsChange = function (...args) {
    onConnectionsChange?.apply(this, args);
    refreshConnections();
  };

  restore(options.default);
  return { widget: addWidget, minWidth: 300 };
}

app.registerExtension({
  name: "shanksimi.ConcatenateText",
  init() {
    const style = document.createElement("style");
    style.textContent = `
      .shank-concatenate-row > * { pointer-events: auto; }
      .lg-node-widgets .shank-concatenate-row { padding: 0; }
      [data-widget-name]:has(.shank-concatenate-row) > :first-child { opacity: 1; }
    `;
    document.head.append(style);
  },
  getCustomWidgets() {
    return { SHANK_CONCATENATE_ROWS: addRowsWidget };
  },
});
