import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
  name: "shanksimi.ImageComparer",
  nodeCreated(node) {
    if (node.comfyClass !== "ShankImageComparer") return;

    const panel = document.createElement("div");
    panel.style.cssText = "display:flex;flex-direction:column;gap:4px;width:100%;height:100%";
    const controls = document.createElement("div");
    controls.style.cssText = "display:flex;gap:4px;flex-wrap:wrap";
    const mode = document.createElement("select");
    mode.add(new Option("Trượt", "slide"));
    mode.add(new Option("Bấm để đổi ảnh", "click"));
    const selectors = ["A", "B"].map(label => {
      const select = document.createElement("select");
      select.setAttribute("aria-label", "Chọn ảnh " + label);
      return select;
    });
    controls.append(mode, ...selectors);

    const stage = document.createElement("div");
    stage.style.cssText = "position:relative;flex:1;min-height:100px;overflow:hidden;background:#171717";
    const images = selectors.map(() => {
      const img = document.createElement("img");
      img.style.cssText = "position:absolute;inset:0;width:100%;height:100%;object-fit:contain;pointer-events:none";
      stage.append(img);
      return img;
    });
    const slider = document.createElement("input");
    slider.type = "range";
    slider.setAttribute("aria-label", "Vị trí đường chia ảnh");
    slider.value = "50";
    slider.style.width = "100%";
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.textContent = "Đổi ảnh A/B";

    let showB = false;
    const draw = () => {
      const both = selectors.every(select => select.value);
      const slide = mode.value === "slide";
      slider.hidden = !both || !slide;
      toggle.hidden = !both || slide;
      images[0].hidden = !selectors[0].value || (both && !slide && showB);
      images[1].hidden = !selectors[1].value || (both && !slide && !showB);
      images[1].style.clipPath = both && slide ? "inset(0 0 0 " + slider.value + "%)" : "";
    };
    selectors.forEach((select, index) => {
      select.onchange = () => {
        if (select.value) images[index].src = select.value;
        else images[index].removeAttribute("src");
        draw();
      };
    });
    mode.onchange = slider.oninput = draw;
    toggle.onclick = () => { showB = !showB; draw(); };
    panel.append(controls, stage, slider, toggle);
    node.addDOMWidget("comparison", "custom", panel, { serialize: false });
    node.setSize([Math.max(node.size[0], 320), Math.max(node.size[1], 340)]);
    draw();

    const onExecuted = node.onExecuted;
    node.onExecuted = function (message) {
      onExecuted?.call(this, message);
      showB = false;
      for (const [index, key] of ["a_images", "b_images"].entries()) {
        const select = selectors[index];
        select.replaceChildren();
        for (const [i, data] of (message?.[key] || []).entries()) {
          const query = new URLSearchParams({
            filename: data.filename, type: data.type, subfolder: data.subfolder || "",
          });
          select.add(new Option((index === 0 ? "A" : "B") + (i + 1), api.apiURL("/view?" + query)));
        }
        select.disabled = select.options.length < 2;
        select.onchange();
      }
    };
  },
});
