import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
  name: "shanksimi.PowerLoraLoader",
  nodeCreated(node) {
    if (node.comfyClass !== "ShankPowerLoraLoader") return;
    const config = node.widgets?.find(widget => widget.name === "loras");
    if (!config) return;
    // Preserve the regular widget for workflow and API serialization.
    config.type = "hidden";
    config.computeSize = () => [0, -4];
    const panel = document.createElement("div");
    panel.style.cssText = "display:flex;flex-direction:column;gap:4px;overflow:auto";
    const rowsElement = document.createElement("div");
    const add = document.createElement("button");
    add.textContent = "Thêm LoRA";
    panel.append(rowsElement, add);
    let choices = [];
    let rows = [];

    function update() {
      config.value = JSON.stringify(rows);
    }

    function render() {
      rowsElement.replaceChildren();
      rows.forEach((row, index) => {
        const line = document.createElement("div");
        line.style.cssText = "display:flex;gap:4px;align-items:center;margin-bottom:4px";
        const toggle = document.createElement("input");
        toggle.type = "checkbox";
        toggle.checked = row.enabled;
        toggle.title = "Bật/tắt LoRA";
        toggle.onchange = () => { row.enabled = toggle.checked; update(); };
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
          input.style.width = "52px";
          input.onchange = () => {
            if (Number.isFinite(input.valueAsNumber)) row[key] = input.valueAsNumber;
            input.value = row[key];
            update();
          };
          return input;
        };
        const remove = document.createElement("button");
        remove.textContent = "×";
        remove.title = "Xóa dòng LoRA";
        remove.onclick = () => { rows.splice(index, 1); update(); render(); };
        line.append(toggle, select, strength("model", "MODEL"), strength("clip", "CLIP"), remove);
        rowsElement.append(line);
      });
    }

    add.onclick = () => {
      rows.push({ enabled: true, name: "", model: 1, clip: 1 });
      update();
      render();
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
    node.addDOMWidget("power_lora_controls", "custom", panel, { serialize: false });
    node.setSize([Math.max(node.size[0], 380), Math.max(node.size[1], 240)]);
    restore();
    api.fetchApi("/shanksimi/wildcard-options")
      .then(response => {
        if (!response.ok) throw new Error(response.statusText);
        return response.json();
      })
      .then(options => { choices = options.loras; render(); })
      .catch(error => { add.title = "Không tải được danh sách LoRA"; console.warn(error); });
  },
});
