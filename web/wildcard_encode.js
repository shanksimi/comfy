import { api } from "../../scripts/api.js";
import { app } from "../../scripts/app.js";

app.registerExtension({
  name: "shanksimi.WildcardEncode",
  nodeCreated(node) {
    if (node.comfyClass !== "ShankWildcardEncode") return;
    const widget = name => node.widgets?.find(item => item.name === name);
    const mode = widget("mode");
    const populated = widget("populated_text");
    const addPicker = (label, format, tooltip) => {
      const choices = [label];
      const picker = node.addWidget("combo", label, label, value => {
        if (value !== label) {
          const target = widget(mode?.value === "populate" ? "wildcard_text" : "populated_text");
          if (target) {
            target.value = [target.value, format(value)].filter(Boolean).join(" ");
            target.callback?.(target.value);
          }
        }
        picker.value = label;
        node.setDirtyCanvas(true, true);
      }, { values: choices, serialize: false, tooltip });
      picker.serialize = false;
      return choices;
    };
    const loras = addPicker("Chèn LoRA", name => "<lora:" + name + ":1.0>", "Chèn thẻ LoRA vào ô prompt đang dùng.");
    const wildcards = addPicker("Chèn wildcard", name => "__" + name + "__", "Chèn tham chiếu wildcard vào ô prompt đang dùng.");
    api.fetchApi("/shanksimi/wildcard-options")
      .then(response => {
        if (!response.ok) throw new Error(response.statusText);
        return response.json();
      })
      .then(options => {
        loras.push(...options.loras);
        wildcards.push(...options.wildcards);
      })
      .catch(error => console.warn("ShankWildcardEncode options:", error));
    const input = populated?.inputEl || populated?.element;
    const originalBackground = input?.style?.backgroundColor ?? "";
    const sync = () => {
      if (!input || !("readOnly" in input)) return;
      const displayOnly = mode?.value === "populate";
      input.readOnly = displayOnly;
      input.style.backgroundColor = displayOnly ? "transparent" : originalBackground;
    };
    const modeChanged = mode?.callback;
    if (mode) mode.callback = function (...args) {
      modeChanged?.apply(this, args);
      sync();
    };
    const executed = node.onExecuted;
    node.onExecuted = function (message) {
      executed?.call(this, message);
      if (populated && message?.mode?.[0] !== "fixed" && typeof message?.text?.[0] === "string") {
        populated.value = message.text[0];
      }
      if (mode?.value === "reproduce" && message?.mode?.[0] === "reproduce") mode.value = "populate";
      sync();
      node.setDirtyCanvas(true, true);
    };
    const configure = node.onConfigure;
    node.onConfigure = function (...args) {
      configure?.apply(this, args);
      sync();
    };
    sync();
  },
});
