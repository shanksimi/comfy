import { app } from "../../scripts/app.js";

const videoNodes = new Set(["VHS_LoadVideoFFmpeg", "VHS_VideoCombine", "VHS_BatchManager"]);
const canSave = widget => widget.type !== "button" && widget.serialize !== false
  && widget.options?.serialize !== false;

app.registerExtension({
  name: "Shank.VideoHelper",
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (!videoNodes.has(nodeData.name)) return;
    const formats = nodeData.input?.required?.format?.[1]?.formats;
    const previousCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function (...args) {
      const result = previousCreated?.apply(this, args);
      const node = this;
      const widgets = node.widgets ?? [];
      const format = widgets.find(widget => widget.name === "format");
      const video = widgets.find(widget => widget.name === "video");
      const formatWidgets = new Set();

      function syncFormat(value) {
        for (const widget of formatWidgets) {
          const index = widgets.indexOf(widget);
          if (index !== -1) widgets.splice(index, 1);
          widget.onRemove?.();
        }
        formatWidgets.clear();
        for (const [name, type, options] of formats?.[value] ?? []) {
          const factory = app.widgets[Array.isArray(type) ? "COMBO" : type];
          const widget = factory(node, name, options ? [type, options] : [type], app).widget;
          formatWidgets.add(widget);
        }
        const size = node.computeSize();
        node.setSize([Math.max(node.size[0], size[0]), Math.max(node.size[1], size[1])]);
        node.setDirtyCanvas(true, true);
      }

      if (formats && format) {
        const previousFormat = format.callback;
        format.callback = function (value, ...params) {
          previousFormat?.call(this, value, ...params);
          syncFormat(value);
        };
        syncFormat(format.value);
      }

      const previousConfigure = node.onConfigure;
      node.onConfigure = function (info) {
        previousConfigure?.call(this, info);
        const values = info.widgets_values;
        if (!values || Array.isArray(values) || typeof values !== "object") return;
        if (formats && format && typeof values.format === "string") syncFormat(values.format);
        for (const widget of widgets) {
          if (!canSave(widget) || !Object.hasOwn(values, widget.name)) continue;
          widget.value = values[widget.name];
        }
        if (video?.value && Array.isArray(video.options?.values) && !video.options.values.includes(video.value)) {
          video.options.values = [...video.options.values, video.value];
        }
        if (values.videopreview?.params?.type === "output") {
          node.shankVideoSubfolder = values.videopreview.params.subfolder;
        }
      };

      const previousSerialize = node.onSerialize;
      node.onSerialize = function (info) {
        previousSerialize?.call(this, info);
        info.widgets_values = Object.fromEntries(widgets.filter(canSave).map(widget => [widget.name, widget.value]));
      };

      if (formats) {
        const previousExecuted = node.onExecuted;
        node.onExecuted = function (message, ...params) {
          previousExecuted?.call(this, message, ...params);
          const output = message?.gifs?.[0];
          if (output?.type === "output") node.shankVideoSubfolder = output.subfolder;
        };
      }
      return result;
    };
  },
});
