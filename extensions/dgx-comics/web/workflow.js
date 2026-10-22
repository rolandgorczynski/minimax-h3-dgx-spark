import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { renderSpeechEditor } from "./speech.js";
import { renderLibrary, refreshLibrary, selectedCharacters, matchedCharacters } from "./characters.js";

app.registerExtension({
    name: "DGX.ComicWorkflow",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (!["DGXComicWorkflow", "DGXComicStudio"].includes(nodeData.name)) return;
        const created = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function (...args) {
            const result = created?.apply(this, args);
            const widget = name => this.widgets.find(w => w.name === name);
            for (const name of ["artikel", "bearbeiteter_plan", "kachel_revisionen", "aktion", "figuren"]) {
                const w = widget(name);
                if (!w) continue;
                w.hidden = true;
                w.computeSize = () => [0, -4];
                if (w.inputEl) w.inputEl.style.display = "none";
            }
            const root = document.createElement("div");
            root.style.cssText = "width:100%;overflow:auto;padding:10px;box-sizing:border-box;background:#222;color:#eee;font:14px sans-serif";
            const dom = this.addDOMWidget("comic_workflow", "div", root, { serialize: false });
            const article = widget("artikel");

            this._comicBusy = false;
            const validateArticle = () => {
                const value=String(article.value ?? "");
                if(!value.trim() || value.length>16000){
                    status.textContent=!value.trim()?"Bitte zuerst oben den Originalartikel oder deine Geschichte einfügen. Figurenbeschreibungen ersetzen die Geschichte nicht.":"Die Geschichte darf maximal 16000 Zeichen enthalten.";
                    root.querySelector('[data-comic-article]')?.focus();
                    return false;
                }
                return true;
            };
            const execute = async action => {
                if(!validateArticle())return;
                if (this._comicBusy) return;
                this._comicBusy = true;
                root.querySelectorAll("button, textarea, input, select").forEach(b => { b.disabled = true; });
                root.querySelectorAll("svg").forEach(el => { el.style.pointerEvents="none"; });
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
                for (const editor of Object.values(this._speechEditors ?? {})) editor.dispose();
                this._speechEditors = {};
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
                const articleLabel=document.createElement("label");
                articleLabel.textContent="1 · Originalartikel / Gesamtgeschichte";
                articleLabel.style.cssText="display:block;font-weight:bold;margin:8px 0";
                const articleField=document.createElement("textarea");
                articleField.dataset.comicArticle="true";
                articleField.setAttribute("aria-label","Originalartikel / Gesamtgeschichte");
                articleField.placeholder="Hier deine vollständige Geschichte einfügen. Figurenbeschreibungen stehen separat in der Figurenbibliothek.";
                articleField.value=String(article.value ?? "");
                articleField.maxLength=16000;
                articleField.style.cssText="display:block;width:100%;height:200px;box-sizing:border-box;background:#151515;color:#fff;padding:10px;margin-top:8px;font:14px sans-serif";
                const counter=document.createElement("small");
                counter.textContent=`${articleField.value.length} / 16000 Zeichen`;
                articleField.oninput=()=>{
                    article.value=articleField.value;
                    counter.textContent=`${articleField.value.length} / 16000 Zeichen`;
                    widget("bearbeiteter_plan").value="";
                    widget("kachel_revisionen").value="{}";
                    widget("aktion").value="Szenen planen";
                    this.properties.comic_panel_previews=[];
                    for(const editor of Object.values(this._speechEditors ?? {}))editor.dispose();
                    this._speechEditors={};
                    root.querySelectorAll('[data-scene-editor]').forEach(el=>el.remove());
                    const next=root.querySelector('[data-comic-generate]');if(next)next.disabled=true;
                    status.textContent=article.value.trim()?"Geschichte eingegeben. Jetzt Szenen planen anklicken.":"Bitte zuerst deinen Originalartikel oder deine Geschichte einfügen.";
                    app.graph?.setDirtyCanvas(true,true);
                };
                articleLabel.append(articleField,counter);root.append(articleLabel);
                const intro = document.createElement("p");
                intro.textContent = "Artikel hier einfügen, Comic-Art und Kachelanzahl oben wählen. 2. Szenen planen und korrigieren. 3. Comic generieren. Danach einzelne Kacheln ändern oder neu zeichnen.";
                root.append(intro);
                renderLibrary(this, root, () => this._renderComicWorkflow());
                button("1 · Szenen planen", () => {
                    if(!validateArticle())return;
                    widget("bearbeiteter_plan").value = "";
                    widget("kachel_revisionen").value = "{}";
                    this.properties.comic_panel_previews = [];
                    execute("Szenen planen");
                });
                let plan;
                try { plan = JSON.parse(widget("bearbeiteter_plan").value); } catch { plan = null; }
                const generate = button("2 · Weiter: Comic generieren", () => execute("Comic generieren"));
                generate.dataset.comicGenerate="true";
                generate.disabled = !plan?.scenes?.length;
                root.append(status);
                if (!plan?.scenes?.length) {
                    status.textContent = article.value?.trim()?"Noch kein Szenenplan. Jetzt Szenen planen anklicken.":"Bitte zuerst deinen Originalartikel oder deine Geschichte in das große Feld oben einfügen.";
                } else {
                    plan.scenes.forEach((scene, i) => {
                        const section = document.createElement("section");
                        section.dataset.sceneEditor="true";
                        section.style.cssText = "padding:10px;margin:10px 0;border:1px solid #666;border-radius:6px";
                        const heading = document.createElement("strong");
                        heading.textContent = `Kachel ${i + 1}`;
                        section.append(heading);
                        const cast = selectedCharacters(this);
                        if (cast.length) {
                            const assignments = document.createElement("div");
                            assignments.textContent = "Figuren in dieser Kachel: ";
                            for (const character of cast) {
                                const label = document.createElement("label");
                                const check = document.createElement("input");check.type="checkbox";
                                check.checked=matchedCharacters(scene,cast).includes(character.id);
                                check.disabled=(scene.bubbles ?? []).some(b=>[character.id,character.name,...(character.aliases ?? [])].some(name=>name.toLocaleLowerCase()===b.speaker.toLocaleLowerCase()));
                                if(check.disabled)check.title="Diese Figur spricht in dieser Kachel.";
                                check.setAttribute("aria-label",`Kachel ${i+1}: Figur ${character.name}`);
                                check.onchange=()=>{
                                    const ids=new Set(matchedCharacters(scene,cast));
                                    if(check.checked)ids.add(character.id);else ids.delete(character.id);
                                    scene.characters=[...ids];
                                    widget("bearbeiteter_plan").value=JSON.stringify(plan);
                                    app.graph?.setDirtyCanvas(true,true);
                                };
                                label.append(check,document.createTextNode(character.name+" "));assignments.append(label);
                            }
                            section.append(assignments);
                        }
                        const preview = this.properties?.comic_panel_previews?.[i];
                        for (const [key, label, height] of [["story", "Szene / Untergeschichte", 100], ["dialog", scene.bubbles ? "Erzählerkasten (optional)" : "Erzählertext / Sprechblase", 70]]) {
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
                                this._speechEditors?.[i]?.refresh();
                                widget("bearbeiteter_plan").value = JSON.stringify(plan);
                                status.textContent = "Änderungen gespeichert. Weiter übernimmt geänderte Szenen; unveränderte Bilder bleiben erhalten.";
                                app.graph?.setDirtyCanvas(true, true);
                            };
                            wrapper.append(field);
                            section.append(wrapper);
                        }
                        this._speechEditors[i] = renderSpeechEditor(this, section, scene, i, cast, preview, () => {
                            widget("bearbeiteter_plan").value = JSON.stringify(plan);
                            app.graph?.setDirtyCanvas(true, true);
                        }, () => this._renderComicWorkflow());
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
                const height = plan?.scenes?.length || this.properties.character_library_open ? 850 : 450;
                root.style.height = `${height}px`;
                dom.computeSize = () => [this.size[0], height];
                this.setSize([this.size[0], this.computeSize()[1]]);
                this.setDirtyCanvas(true, true);
            };
            for (const name of ["artikel", "anzahl_kacheln", "seed"]) {
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
            const styleWidget = widget("comic_art");
            const styleCallback = styleWidget.callback;
            styleWidget.callback = (...values) => {
                styleCallback?.apply(styleWidget, values);
                // Preserve the reviewed plan, revisions and existing previews.
                this._renderComicWorkflow();
                status.textContent = "Bildstil geändert. Szenen und Texte bleiben erhalten. Weiter generiert die Bilder im gewählten Stil.";
                app.graph?.setDirtyCanvas(true, true);
            };
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
            refreshLibrary(this).then(() => this._renderComicWorkflow()).catch(error => {
                status.textContent = `Figurenbibliothek: ${error.message}`;
            });
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
