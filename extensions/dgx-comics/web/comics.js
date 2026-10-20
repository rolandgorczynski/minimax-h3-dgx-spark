import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "DGX.SysopComics",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "DGXSysopComic") return;
        const created = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function (...args) {
            const result = created?.apply(this, args);
            const serialized = this.widgets.find(w => w.name === "szenen");
            const count = this.widgets.find(w => w.name === "anzahl_kacheln");
            // Keep data in a normal serialized widget, including panels temporarily hidden by a smaller count.
            serialized.hidden = true;
            serialized.computeSize = () => [0, -4];
            if (serialized.inputEl) serialized.inputEl.style.display = "none";
            const container = document.createElement("div");
            container.style.cssText = "width:100%;overflow-y:auto;box-sizing:border-box;padding:8px;background:#252525;color:#eee;font:14px sans-serif;";
            const editor = this.addDOMWidget("kachel_editor", "div", container, { serialize: false });
            this._renderScenes = () => {
                if (this.inputs?.some(input => input.name === "szenenplan" && input.link != null)) {
                    count.disabled = true;
                    container.textContent = "Kachelanzahl, Szenen und Sprechblasen werden im Gesamtgeschichte-Knoten bearbeitet.";
                    container.style.height = "70px";
                    editor.computeSize = () => [this.size[0], 70];
                    return;
                }
                count.disabled = false;
                let scenes;
                try { scenes = JSON.parse(serialized.value); } catch { scenes = []; }
                if (!Array.isArray(scenes)) scenes = [];
                const total = Math.min(12, Math.max(1, Number(count.value) || 1));
                while (scenes.length < total) scenes.push({ story: "", dialog: "" });
                serialized.value = JSON.stringify(scenes);
                container.replaceChildren();
                for (let i = 0; i < total; i++) {
                    const section = document.createElement("section");
                    section.style.cssText = "padding:8px;margin-bottom:10px;border:1px solid #666;border-radius:6px;";
                    const heading = document.createElement("strong");
                    heading.textContent = `Kachel ${i + 1}`;
                    section.append(heading);
                    for (const [key, label, height] of [["story", "Szene / Handlung", 85], ["dialog", "Sprechblase (optional)", 55]]) {
                        const wrapper = document.createElement("label");
                        wrapper.textContent = label;
                        wrapper.style.cssText = "display:block;margin-top:7px;";
                        const input = document.createElement("textarea");
                        input.value = scenes[i]?.[key] ?? "";
                        input.setAttribute("aria-label", `Kachel ${i + 1}: ${label}`);
                        input.style.cssText = `width:100%;height:${height}px;box-sizing:border-box;resize:vertical;background:#171717;color:#fff;padding:6px;border:1px solid #777;`;
                        input.addEventListener("input", () => {
                            scenes[i] ??= { story: "", dialog: "" };
                            scenes[i][key] = input.value;
                            serialized.value = JSON.stringify(scenes);
                            app.graph?.setDirtyCanvas(true, true);
                        });
                        wrapper.append(input);
                        section.append(wrapper);
                    }
                    container.append(section);
                }
                const height = Math.min(850, total * 245);
                container.style.height = `${height}px`;
                editor.computeSize = () => [this.size[0], height];
                this.setSize([this.size[0], this.computeSize()[1]]);
                this.setDirtyCanvas(true, true);
            };
            const callback = count.callback;
            count.callback = (...args) => { callback?.apply(count, args); this._renderScenes(); };
            this._renderScenes();
            return result;
        };
        const configured = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (...args) {
            const result = configured?.apply(this, args);
            this._renderScenes?.();
            return result;
        };
    },
});
