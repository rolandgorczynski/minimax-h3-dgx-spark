import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "DGX.ComicWorkflow",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "DGXComicWorkflow") return;
        const created = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function (...args) {
            const result = created?.apply(this, args);
            const widget = name => this.widgets.find(w => w.name === name);
            for (const name of ["bearbeiteter_plan", "kachel_revisionen", "aktion"]) {
                const w = widget(name);
                w.hidden = true;
                w.computeSize = () => [0, -4];
                if (w.inputEl) w.inputEl.style.display = "none";
            }
            const root = document.createElement("div");
            root.style.cssText = "width:100%;overflow:auto;padding:10px;box-sizing:border-box;background:#222;color:#eee;font:14px sans-serif";
            const dom = this.addDOMWidget("comic_workflow", "div", root, { serialize: false });
            const article = widget("artikel");
            article.computeSize = () => [this.size[0], 260];
            this._comicBusy = false;
            const execute = async action => {
                if (this._comicBusy) return;
                this._comicBusy = true;
                root.querySelectorAll("button, textarea").forEach(b => { b.disabled = true; });
                widget("aktion").value = action;
                status.textContent = action === "Szenen planen" ? "Szenen werden geplant …" : "Comic wird erstellt; unveränderte Bilder werden wiederverwendet …";
                try { await app.queuePrompt(0, 1); }
                catch (error) {
                    this._comicBusy = false;
                    this._renderComicWorkflow();
                    status.textContent = `Fehler: ${error.message ?? error}`;
                }
            };
            const status = document.createElement("p");
            this._renderComicWorkflow = () => {
                root.replaceChildren();
                status.textContent = "Szenen prüfen und bearbeiten; anschließend Weiter anklicken.";
                const button = (label, callback, parent = root) => {
                    const b = document.createElement("button");
                    b.textContent = label;
                    b.style.cssText = "padding:9px;margin:4px;cursor:pointer";
                    b.onclick = callback;
                    parent.append(b);
                    return b;
                };
                const intro = document.createElement("p");
                intro.textContent = "1. Artikel, Comic-Art und Anzahl oben wählen. 2. Szenen planen und korrigieren. 3. Comic generieren. Danach einzelne Kacheln ändern oder neu zeichnen.";
                root.append(intro);
                button("1 · Szenen planen", () => {
                    widget("bearbeiteter_plan").value = "";
                    widget("kachel_revisionen").value = "{}";
                    this.properties.comic_panel_previews = [];
                    execute("Szenen planen");
                });
                let plan;
                try { plan = JSON.parse(widget("bearbeiteter_plan").value); } catch { plan = null; }
                const generate = button("2 · Weiter: Comic generieren", () => execute("Comic generieren"));
                generate.disabled = !plan?.scenes?.length;
                root.append(status);
                if (!plan?.scenes?.length) {
                    status.textContent = "Noch kein Szenenplan. Zuerst Szenen planen anklicken.";
                } else {
                    plan.scenes.forEach((scene, i) => {
                        const section = document.createElement("section");
                        section.style.cssText = "padding:10px;margin:10px 0;border:1px solid #666;border-radius:6px";
                        const heading = document.createElement("strong");
                        heading.textContent = `Kachel ${i + 1}`;
                        section.append(heading);
                        const preview = this.properties?.comic_panel_previews?.[i];
                        if (preview) {
                            const img = document.createElement("img");
                            img.src = api.apiURL(`/view?${new URLSearchParams(preview)}`);
                            img.style.cssText = "display:block;max-width:100%;max-height:280px;margin:8px auto";
                            img.alt = `Vorschau Kachel ${i + 1}`;
                            section.append(img);
                        }
                        for (const [key, label, height] of [["story", "Szene / Untergeschichte", 100], ["dialog", "Erzählertext / Sprechblase", 70]]) {
                            const wrapper = document.createElement("label");
                            wrapper.textContent = label;
                            wrapper.style.display = "block";
                            const field = document.createElement("textarea");
                            field.value = scene[key] ?? "";
                            field.maxLength = key === "story" ? 4000 : 400;
                            field.setAttribute("aria-label", `Kachel ${i+1}: ${label}`);
                            field.style.cssText = `display:block;width:100%;height:${height}px;box-sizing:border-box;background:#151515;color:#fff;padding:8px`;
                            field.oninput = () => {
                                scene[key] = field.value;
                                widget("bearbeiteter_plan").value = JSON.stringify(plan);
                                status.textContent = "Änderungen gespeichert. Weiter übernimmt geänderte Szenen; unveränderte Bilder bleiben erhalten.";
                                app.graph?.setDirtyCanvas(true, true);
                            };
                            wrapper.append(field);
                            section.append(wrapper);
                        }
                        button(`Kachel ${i+1} neu zeichnen`, () => {
                            let revisions;
                            try { revisions = JSON.parse(widget("kachel_revisionen").value); } catch { revisions = {}; }
                            revisions[String(i)] = (revisions[String(i)] ?? 0) + 1;
                            widget("kachel_revisionen").value = JSON.stringify(revisions);
                            execute("Comic generieren");
                        }, section);
                        root.append(section);
                    });
                }
                const height = plan?.scenes?.length ? 850 : 200;
                root.style.height = `${height}px`;
                dom.computeSize = () => [this.size[0], height];
                this.setSize([this.size[0], this.computeSize()[1]]);
                this.setDirtyCanvas(true, true);
            };
            for (const name of ["artikel", "comic_art", "anzahl_kacheln", "seed"]) {
                const w = widget(name);
                const previous = w.callback;
                w.callback = (...values) => {
                    previous?.apply(w, values);
                    widget("bearbeiteter_plan").value = "";
                    widget("kachel_revisionen").value = "{}";
                    widget("aktion").value = "Szenen planen";
                    this.properties.comic_panel_previews = [];
                    this._renderComicWorkflow();
                };
            }
            api.addEventListener("execution_error", event => {
                if (String(event.detail.node_id) !== String(this.id)) return;
                this._comicBusy = false;
                this._renderComicWorkflow();
                status.textContent = `Fehler: ${event.detail.exception_message ?? "Ausführung fehlgeschlagen"}`;
            });
            api.addEventListener("execution_interrupted", () => {
                this._comicBusy = false;
                this._renderComicWorkflow();
                status.textContent = "Ausführung abgebrochen. Bereits fertige Bilder bleiben erhalten.";
            });
            this._renderComicWorkflow();
            return result;
        };
        const configured = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (...args) {
            const result = configured?.apply(this, args);
            this._renderComicWorkflow?.();
            return result;
        };
        const executed = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            executed?.call(this, message);
            this._comicBusy = false;
            if (message.comic_plan?.[0]) {
                this.widgets.find(w => w.name === "bearbeiteter_plan").value = message.comic_plan[0];
            }
            if (message.comic_panels) {
                this.properties.comic_panel_previews = message.comic_panels;
            }
            this._renderComicWorkflow?.();
        };
    },
});
