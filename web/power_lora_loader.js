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
    panel.style.cssText = "display:flex;flex-direction:column;gap:4px;box-sizing:border-box;width:100%";
    const strengthMode = "Show Strengths";
    const splitMode = "Separate Model & Clip";
    let choices = [];
    let rows = [];

    function update() {
      config.value = JSON.stringify(rows);
    }

    const panelHeight = () => (rows.length + 1) * 30 + 4;

    function render() {
      panel.replaceChildren();
      const emptyRow = { enabled: true, name: "", model: 1, clip: 1 };
      [...rows, emptyRow].forEach((row, index) => {
        const isEmpty = row === emptyRow;
        const separate = node.properties?.[strengthMode] === splitMode || row.model !== row.clip;
        const line = document.createElement("div");
        const columns = separate ? "54px 54px" : "64px";
        line.style.cssText = `display:grid;grid-template-columns:30px minmax(0,1fr) ${columns} 24px;gap:4px;align-items:center;height:26px;flex-shrink:0`;
        const toggle = document.createElement("button");
        toggle.type = "button";
        toggle.setAttribute("role", "switch");
        toggle.setAttribute("aria-label", "Bật/tắt LoRA");
        toggle.title = "Bật/tắt LoRA";
        toggle.disabled = isEmpty;
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
        select.disabled = isEmpty && choices.length === 0;
        select.add(new Option(isEmpty ? "+ Thêm LoRA" : "Chọn LoRA", ""));
        for (const name of new Set([...choices, row.name].filter(Boolean))) {
          select.add(new Option(name, name));
        }
        select.value = row.name;
        select.onchange = () => {
          const name = select.value;
          if (isEmpty && !name) return;
          if (isEmpty) {
            rows.push({ ...row, name });
          } else if (name) {
            row.name = name;
          } else {
            rows.splice(index, 1);
          }
          update();
          render();
          panel.children[Math.min(index, rows.length)]?.querySelector("select")?.focus();
        };
        const strength = (key, label) => {
          const input = document.createElement("input");
          input.type = "number";
          input.step = "0.05";
          input.value = Number(row[key]).toFixed(2);
          input.title = label;
          input.setAttribute("aria-label", label);
          input.disabled = isEmpty;
          input.style.cssText = "width:100%;min-width:0;box-sizing:border-box";
          input.onchange = () => {
            if (Number.isFinite(input.valueAsNumber)) {
              row[key] = input.valueAsNumber;
              if (!separate) row.clip = row.model;
            }
            input.value = Number(row[key]).toFixed(2);
            update();
          };
          return input;
        };
        const remove = document.createElement("button");
        remove.type = "button";
        remove.textContent = "×";
        remove.title = "Xóa dòng LoRA";
        remove.onclick = () => { rows.splice(index, 1); update(); render(); };
        remove.disabled = isEmpty;
        remove.style.visibility = isEmpty ? "hidden" : "";
        line.append(toggle, select, strength("model", separate ? "MODEL strength" : "LoRA strength"));
        if (separate) line.append(strength("clip", "CLIP strength"));
        line.append(remove);
        panel.append(line);
      });
      const minimum = node.computeSize();
      if (node.size[1] < minimum[1]) node.setSize([node.size[0], minimum[1]]);
      node.setDirtyCanvas(true, true);
    }

    const getExtraMenuOptions = node.getExtraMenuOptions;
    node.getExtraMenuOptions = function (canvas, options) {
      const result = getExtraMenuOptions?.call(this, canvas, options);
      const menu = result ?? options;
      const separate = this.properties?.[strengthMode] === splitMode;
      menu.push({
        content: separate ? "Dùng chung strength" : "Chỉnh riêng MODEL và CLIP",
        callback: () => {
          (this.properties ??= {})[strengthMode] = separate ? "Single Strength" : splitMode;
          render();
        },
      });
      return result;
    };

    const restore = savedWidgets => {
      const migrated = savedWidgets?.filter(value =>
        value && typeof value === "object" && typeof value.lora === "string");
      if (migrated?.length) {
        rows = migrated.map(value => ({
          enabled: Boolean(value.on), name: value.lora, model: value.strength ?? 1,
          clip: value.strengthTwo ?? value.strength ?? 1,
        }));
        update();
        render();
        return;
      }
      try {
        const saved = JSON.parse(config.value);
        rows = Array.isArray(saved) ? saved.filter(row => row?.name) : [];
      } catch {
        rows = [];
      }
      render();
    };
    const configure = node.onConfigure;
    node.onConfigure = function (...args) {
      configure?.apply(this, args);
      restore(args[0]?.widgets_values);
    };
    const controls = node.addDOMWidget("power_lora_controls", "custom", panel, {
      serialize: false,
      getMinHeight: panelHeight,
      getMaxHeight: panelHeight,
    });
    controls.computeSize = width => [width, panelHeight()];
    node.setSize([Math.max(node.size[0], 290), node.size[1]]);
    restore();
    api.fetchApi("/shanksimi/wildcard-options")
      .then(response => {
        if (!response.ok) throw new Error(response.statusText);
        return response.json();
      })
      .then(options => {
        choices = options.loras;
        render();
      })
      .catch(error => { panel.title = "Không tải được danh sách LoRA"; console.warn(error); });
  },
});
