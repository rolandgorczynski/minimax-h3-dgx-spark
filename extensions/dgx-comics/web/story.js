import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "DGX.ComicStory",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "DGXComicStory") return;
        const created = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function (...args) {
            const result = created?.apply(this, args);
            const saved = this.widgets.find(w => w.name === "bearbeiteter_plan");
            saved.hidden = true;
            saved.computeSize = () => [0, -4];
            if (saved.inputEl) saved.inputEl.style.display = "none";
            const container = document.createElement("div");
            container.style.cssText = "width:100%;height:100px;overflow:auto;background:#252525;color:#eee;padding:8px;box-sizing:border-box;font:14px sans-serif;";
            const editor = this.addDOMWidget("geplanter_comic", "div", container, { serialize: false });
            this._renderPlan = () => {
                container.replaceChildren();
                let plan;
                try { plan = JSON.parse(saved.value); } catch { plan = null; }
                if (!plan?.scenes?.length) {
                    container.textContent = "Nach dem Planen erscheinen hier die bearbeitbaren Szenen und Sprechblasen.";
                    container.style.height = "100px";
                    editor.computeSize = () => [this.size[0], 100];
                    return;
                }
                plan.scenes.forEach((scene, i) => {
                    const section = document.createElement("section");
                    section.style.cssText = "padding:8px;margin-bottom:10px;border:1px solid #666;border-radius:6px;";
                    const heading = document.createElement("strong");
                    heading.textContent = `Geplante Kachel ${i+1}`;
                    section.append(heading);
                    for (const [key, label] of [["story", "Szene"], ["dialog", "Erzählertext / Sprechblase"]]) {
                        const wrapper = document.createElement("label");
                        wrapper.textContent = label;
                        wrapper.style.display = "block";
                        const input = document.createElement("textarea");
                        input.value = scene[key] ?? "";
                        input.setAttribute("aria-label", `Geplante Kachel ${i+1}: ${label}`);
                        input.style.cssText = `width:100%;height:${key==='story'?85:55}px;background:#171717;color:white;box-sizing:border-box;padding:6px;`;
                        input.addEventListener("input", () => {
                            scene[key] = input.value;
                            saved.value = JSON.stringify(plan);
                            app.graph?.setDirtyCanvas(true, true);
                        });
                        wrapper.append(input);
                        section.append(wrapper);
                    }
                    container.append(section);
                });
                for (const id of this.outputs?.[0]?.links ?? []) {
                    const link = app.graph.links?.get?.(id) ?? app.graph.links?.[id];
                    const target = link && app.graph.getNodeById(link.target_id);
                    const count = target?.widgets?.find(w => w.name === "anzahl_kacheln");
                    if (count) { count.value = plan.scenes.length; target._renderScenes?.(); }
                }
                const height = Math.min(850, plan.scenes.length*235);
                container.style.height = `${height}px`;
                editor.computeSize = () => [this.size[0], height];
                this.setSize([this.size[0], this.computeSize()[1]]);
                this.setDirtyCanvas(true, true);
            };
            for (const name of ["gesamtgeschichte", "anzahl_kacheln", "seed"]) {
                const widget = this.widgets.find(w => w.name === name);
                if (!widget) continue;
                const callback = widget.callback;
                widget.callback = (...args) => {
                    callback?.apply(widget, args);
                    saved.value = "";
                    this._renderPlan();
                };
            }
            this.addWidget("button", "Szenen neu planen", null, () => {
                saved.value = "";
                this._renderPlan();
            }, { serialize: false });
            this._renderPlan();
            return result;
        };
        const configured = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (...args) {
            const result = configured?.apply(this, args);
            this._renderPlan?.();
            return result;
        };
        const executed = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            executed?.call(this, message);
            if (message.comic_plan?.[0]) {
                this.widgets.find(w => w.name === "bearbeiteter_plan").value = message.comic_plan[0];
                this._renderPlan?.();
            }
        };
    },
});
