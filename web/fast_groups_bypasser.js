import { app } from "../../scripts/app.js";

app.registerExtension({
  name: "shanksimi.FastGroupsBypasser",
  registerCustomNodes() {
    class ShankFastGroupsBypasser extends globalThis.LGraphNode {
      static title = "Fast Groups Bypasser (shanksimi)";
      static desc = "Bật hoặc bypass các node trong từng nhóm của graph hiện tại.";
      isVirtualNode = true;

      constructor() {
        super();
        this.size = [290, 100];
      }

      onDrawForeground() {
        const groups = this.graph?._groups ?? [];
        if (this.widgets?.length === groups.length &&
            groups.every((group, index) => this.widgets[index].group === group)) {
          for (const widget of this.widgets) {
            widget.name = widget.group.title;
            widget.value = this.members(widget.group).some(node => node.mode === LiteGraph.ALWAYS);
          }
          return;
        }

        this.widgets = [];
        for (const group of groups) {
          const widget = this.addWidget("toggle", group.title, false, enabled => {
            for (const node of this.members(group)) {
              node.mode = enabled ? LiteGraph.ALWAYS : (LiteGraph.BYPASS ?? 4);
            }
            this.graph?.change();
            this.setDirtyCanvas(true, true);
          }, { serialize: false });
          widget.group = group;
          widget.serialize = false;
          widget.value = this.members(group).some(node => node.mode === LiteGraph.ALWAYS);
        }
        this.setSize([this.size[0], Math.max(100, this.computeSize()[1])]);
      }

      members(group) {
        group.recomputeInsideNodes();
        return Array.from(group.nodes ?? group._nodes ?? []).filter(node => node !== this);
      }
    }

    LiteGraph.registerNodeType("ShankFastGroupsBypasser", ShankFastGroupsBypasser);
    ShankFastGroupsBypasser.category = "utils";
  },
});
