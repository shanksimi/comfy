import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
  name: "shanksimi.PowerLoraLoader",
  setup() {
    const graph = globalThis.LiteGraph;
    const Original = graph?.registered_node_types?.["Power Lora Loader (rgthree)"];
    if (!Original) return;

    class ShankPowerLoraLoader extends Original {
      static comfyClass = "ShankPowerLoraLoader";

      configure(info) {
        const oldConfig = info.widgets_values?.find(value =>
          typeof value === "string" && value.startsWith("["));
        if (oldConfig) {
          try {
            const rows = JSON.parse(oldConfig);
            if (Array.isArray(rows)) {
              info = {
                ...info,
                properties: { ...info.properties, "Show Strengths": "Separate Model & Clip" },
                widgets_values: rows.filter(row => row?.name).map(row => ({
                  on: Boolean(row.enabled), lora: row.name,
                  strength: row.model, strengthTwo: row.clip,
                })),
              };
            }
          } catch (error) {
            console.warn("Không thể khôi phục danh sách LoRA cũ", error);
          }
        }
        return super.configure(info);
      }
    }
    ShankPowerLoraLoader.title = "Power Lora Loader (shanksimi)";
    graph.registerNodeType("ShankPowerLoraLoader", ShankPowerLoraLoader);
    ShankPowerLoraLoader.category = "loaders";
  },
  nodeCreated(node) {
    if (node.comfyClass !== "ShankPowerLoraLoader") return;
    const config = node.widgets?.find(widget => widget.name === "loras");
    if (!config) return;
    // Preserve the regular widget for workflow and API serialization.
    config.type = "hidden";
    config.computeSize = () => [0, -4];
    const panel = document.createElement("div");
    panel.style.cssText = "display:flex;flex-direction:column;gap:6px;box-sizing:border-box;width:100%;height:100%;min-height:0;overflow:hidden";
    const rowsElement = document.createElement("div");
    rowsElement.style.cssText = "display:flex;flex-direction:column;gap:4px;min-height:0;overflow:auto";
    const add = document.createElement("button");
    add.type = "button";
    add.style.flexShrink = "0";
    add.textContent = "+ Thêm LoRA";
    add.disabled = true;
    panel.append(rowsElement, add);
    let choices = [];
    let rows = [];

    function update() {
      config.value = JSON.stringify(rows);
    }

    const panelHeight = () => Math.min(rows.length, 8) * 36 + 36;

    function render() {
      rowsElement.replaceChildren();
      rows.forEach((row, index) => {
        const line = document.createElement("div");
        line.style.cssText = "display:grid;grid-template-columns:34px minmax(0,1fr) 56px 56px 26px;gap:4px;align-items:center;min-height:32px;flex-shrink:0";
        const toggle = document.createElement("button");
        toggle.type = "button";
        toggle.setAttribute("role", "switch");
        toggle.setAttribute("aria-label", "Bật/tắt LoRA");
        toggle.title = "Bật/tắt LoRA";
        toggle.style.cssText = "position:relative;width:34px;height:20px;padding:0;border:0;border-radius:10px;cursor:pointer";
        const thumb = document.createElement("span");
        thumb.style.cssText = "position:absolute;top:3px;width:14px;height:14px;border-radius:50%;background:white;pointer-events:none";
        toggle.append(thumb);
        const showEnabled = () => {
          toggle.setAttribute("aria-checked", String(Boolean(row.enabled)));
          toggle.style.background = row.enabled ? "#27834c" : "#666";
          thumb.style.left = row.enabled ? "17px" : "3px";
        };
        toggle.onclick = () => {
          row.enabled = !row.enabled;
          showEnabled();
          update();
        };
        showEnabled();
        const select = document.createElement("select");
        select.style.cssText = "flex:1;min-width:0";
        select.title = "Chọn file LoRA";
        select.add(new Option("Chọn LoRA", ""));
        for (const name of new Set([...choices, row.name].filter(Boolean))) {
          select.add(new Option(name, name));
        }
        select.value = row.name;
        select.onchange = () => { row.name = select.value; update(); };
        const strength = (key, label) => {
          const input = document.createElement("input");
          input.type = "number";
          input.step = "0.05";
          input.value = row[key];
          input.title = "Độ mạnh " + label;
          input.style.cssText = "width:100%;min-width:0;box-sizing:border-box";
          input.onchange = () => {
            if (Number.isFinite(input.valueAsNumber)) row[key] = input.valueAsNumber;
            input.value = row[key];
            update();
          };
          return input;
        };
        const remove = document.createElement("button");
        remove.type = "button";
        remove.textContent = "×";
        remove.title = "Xóa dòng LoRA";
        remove.onclick = () => { rows.splice(index, 1); update(); render(); };
        line.append(toggle, select, strength("model", "MODEL"), strength("clip", "CLIP"), remove);
        rowsElement.append(line);
      });
      const minimum = node.computeSize();
      if (node.size[1] < minimum[1]) node.setSize([node.size[0], minimum[1]]);
      node.setDirtyCanvas(true, true);
    }

    add.onclick = event => {
      new globalThis.LiteGraph.ContextMenu(choices, {
        event,
        title: "Chọn LoRA",
        callback: name => {
          rows.push({ enabled: true, name, model: 1, clip: 1 });
          update();
          render();
        },
      });
    };
    const restore = () => {
      try {
        const saved = JSON.parse(config.value);
        rows = Array.isArray(saved) ? saved : [];
      } catch {
        rows = [];
      }
      render();
    };
    const configure = node.onConfigure;
    node.onConfigure = function (...args) {
      configure?.apply(this, args);
      restore();
    };
    const controls = node.addDOMWidget("power_lora_controls", "custom", panel, {
      serialize: false,
      getMinHeight: panelHeight,
      getMaxHeight: panelHeight,
    });
    controls.computeSize = width => [width, panelHeight()];
    node.setSize([Math.max(node.size[0], 380), Math.max(node.size[1], 240)]);
    restore();
    api.fetchApi("/shanksimi/wildcard-options")
      .then(response => {
        if (!response.ok) throw new Error(response.statusText);
        return response.json();
      })
      .then(options => {
        choices = options.loras;
        add.disabled = choices.length === 0;
        add.title = choices.length ? "Chọn LoRA để thêm" : "Chưa có file LoRA";
        render();
      })
      .catch(error => { add.title = "Không tải được danh sách LoRA"; console.warn(error); });
  },
});
