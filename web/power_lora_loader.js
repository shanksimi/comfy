import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { showModelInfo } from "./model_info_dialog.js";
import { openModelPicker } from "./searchable_model_picker.js";

app.registerExtension({
  name: "shanksimi.PowerLoraLoader",
  nodeCreated(node) {
    if (node.comfyClass !== "ShankPowerLoraLoader") return;
    const configIndex = node.widgets?.findIndex(widget => widget.name === "loras") ?? -1;
    if (configIndex < 0) return;
    const original = node.widgets[configIndex];
    // The STRING control may be a registered DOM widget. Replacing it keeps its
    // serialized slot and API name without leaving a rendered input on the canvas.
    const config = {
      name: original.name,
      value: original.value,
      type: "shank_lora_state",
      options: { ...original.options, serialize: true },
      computeSize: () => [0, 0],
      draw() {},
    };
    original.onRemove?.();
    original.element?.remove();
    node.widgets[configIndex] = config;
    const panel = document.createElement("div");
    panel.style.cssText = "display:flex;flex-direction:column;gap:4px;box-sizing:border-box;width:100%";
    const strengthMode = "Show Strengths";
    const splitMode = "Separate Model & Clip";
    let choices = [];
    let rows = [];
    let infoDialog;

    function update() {
      config.value = JSON.stringify(rows);
    }

    const panelHeight = () => (rows.length + 1) * 25 + 4;

    function render() {
      panel.replaceChildren();
      const emptyRow = { enabled: true, name: "", model: 1, clip: 1 };
      [...rows, emptyRow].forEach((row, index) => {
        const isEmpty = row === emptyRow;
        const separate = node.properties?.[strengthMode] === splitMode || row.model !== row.clip;
        const line = document.createElement("div");
        const strengthColumns = separate ? "44px 44px" : "52px";
        const columns = isEmpty ? "minmax(0,1fr)" : `17px minmax(0,1fr) 18px ${strengthColumns} 16px`;
        line.style.cssText = `display:grid;grid-template-columns:${columns};gap:4px;align-items:center;height:21px;flex-shrink:0;padding:0 6px;border-radius:11px;background:var(--comfy-input-bg,#202020);color:var(--input-text,#ddd);font:12px sans-serif`;
        const select = document.createElement("button");
        select.type = "button";
        select.style.cssText = "width:100%;min-width:0;border:0;background:transparent;color:inherit;font:inherit;text-overflow:ellipsis;white-space:nowrap;overflow:hidden;cursor:pointer;text-align:left;padding:0";
        select.textContent = isEmpty ? "+ Thêm LoRA" : row.name.split(/[\\/]/).pop();
        select.title = row.name || "Chọn file LoRA";
        select.disabled = isEmpty && choices.length === 0;
        select.onclick = () => openModelPicker({
          title: isEmpty ? "Thêm LoRA" : "Đổi LoRA",
          choices,
          current: row.name,
          onSelect(name) {
            if (isEmpty) rows.push({ ...row, name });
            else row.name = name;
            update();
            render();
          },
        });
        if (isEmpty) {
          line.append(select);
          panel.append(line);
          return;
        }
        const chromelessButton = "border:0;background:transparent;color:inherit;padding:0;cursor:pointer;font:inherit";
        const toggle = document.createElement("button");
        toggle.type = "button";
        toggle.setAttribute("role", "switch");
        toggle.setAttribute("aria-label", "Bật/tắt LoRA");
        toggle.title = "Bật/tắt LoRA";
        toggle.style.cssText = chromelessButton;
        const showEnabled = () => {
          toggle.setAttribute("aria-checked", String(Boolean(row.enabled)));
          toggle.textContent = row.enabled ? "●" : "○";
          toggle.style.color = row.enabled ? "#a7db74" : "var(--descrip-text,#888)";
        };
        toggle.onclick = () => {
          row.enabled = !row.enabled;
          showEnabled();
          update();
        };
        showEnabled();
        const strength = (key, label) => {
          const input = document.createElement("input");
          input.type = "number";
          input.step = "0.05";
          input.value = Number(row[key]).toFixed(2);
          input.title = label;
          input.setAttribute("aria-label", label);
          input.style.cssText = "width:100%;min-width:0;box-sizing:border-box;border:0;background:transparent;color:inherit;text-align:right;font:inherit;font-variant-numeric:tabular-nums";
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
        const info = document.createElement("button");
        info.type = "button";
        info.textContent = "ⓘ";
        info.title = "Thông tin LoRA trên Civitai";
        info.setAttribute("aria-label", info.title);
        info.style.cssText = chromelessButton;
        info.onclick = () => {
          if (!infoDialog?.open) {
            void showModelInfo(row.name, "lora-info", dialog => { infoDialog = dialog; });
          }
        };
        const remove = document.createElement("button");
        remove.type = "button";
        remove.textContent = "×";
        remove.title = "Xóa dòng LoRA";
        remove.style.cssText = chromelessButton;
        remove.onclick = () => { rows.splice(index, 1); update(); render(); };
        line.append(toggle, select, info, strength("model", separate ? "MODEL strength" : "LoRA strength"));
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
