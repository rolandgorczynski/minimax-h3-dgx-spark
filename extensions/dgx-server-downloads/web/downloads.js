import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const models = new Map();
let dialog;
let list;
let notice;
let poll;
let lastCompleted = "";

function remember(value) {
    if (!value || typeof value !== "object") return;
    if (value.properties?.models) {
        for (const model of value.properties.models) {
            if (model.name && model.url && model.directory) {
                const directory = ({ unet: "diffusion_models", clip: "text_encoders" })[model.directory] ?? model.directory;
                const copy = { name: model.name, url: model.url, directory };
                models.set(`${copy.directory}/${copy.name}`, copy);
            }
        }
    }
    for (const child of Object.values(value)) {
        if (child && typeof child === "object") remember(child);
    }
}

function currentModels() {
    // Include metadata inside subgraph definitions as well as ordinary nodes.
    const graph = app.rootGraph ?? app.graph;
    if (graph) remember(graph.serialize());
    return [...models.values()];
}

async function request(path, body) {
    const response = await api.fetchApi(`/dgx-downloads/${path}`, body === undefined ? {} : {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-DGX-Download": "1" },
        body: JSON.stringify(body),
    });
    if (!response.ok) {
        let message = `HTTP ${response.status}`;
        try { message = (await response.json()).error ?? message; } catch { /* Non-JSON server error. */ }
        throw new Error(message);
    }
    return response.json();
}

function size(bytes) {
    return bytes == null ? "Größe unbekannt" : `${(bytes / 1024 ** 3).toFixed(2)} GiB`;
}

async function refresh() {
    try {
        const jobs = await request("jobs");
        list.replaceChildren();
        if (!jobs.length) list.textContent = "Noch keine Server-Downloads gestartet.";
        const labels = { queued: "Wartet", downloading: "Lädt", complete: "Fertig", present: "Bereits vorhanden", error: "Fehler" };
        for (const job of jobs) {
            const row = document.createElement("div");
            row.style.cssText = "padding:12px 0;border-bottom:1px solid #555;overflow-wrap:anywhere";
            const title = document.createElement("strong");
            title.textContent = `${job.directory}/${job.name}`;
            const status = document.createElement("div");
            status.textContent = `${labels[job.status] ?? job.status} · ${size(job.downloaded)} / ${size(job.total)}`;
            row.append(title, status);
            if (job.status === "queued" || job.status === "downloading") {
                const progress = document.createElement("progress");
                progress.style.width = "100%";
                progress.setAttribute("aria-label", job.name);
                if (job.total) { progress.max = job.total; progress.value = job.downloaded; }
                row.append(progress);
            }
            if (job.error) {
                const error = document.createElement("div");
                error.textContent = job.error;
                error.style.color = "#ffb6a8";
                row.append(error);
                const model = models.get(job.id);
                if (model) {
                    const retry = document.createElement("button");
                    retry.textContent = "Erneut versuchen / fortsetzen";
                    retry.onclick = () => enqueue([model]);
                    row.append(retry);
                }
            }
            list.append(row);
        }
        const completed = jobs.filter(j => ["complete", "present"].includes(j.status)).map(j => j.id).join("|");
        if (completed && completed !== lastCompleted) {
            lastCompleted = completed;
            await app.refreshComboInNodes?.();
        }
    } catch (error) {
        notice.textContent = `Download-Status nicht erreichbar: ${error.message}`;
    }
}

function show() {
    if (!dialog) {
        dialog = document.createElement("dialog");
        dialog.style.cssText = "width:min(760px,90vw);max-height:80vh;background:#252525;color:#eee;border:1px solid #777;border-radius:10px;padding:20px;z-index:100000";
        const header = document.createElement("h2");
        header.textContent = "Modelle auf dem DGX herunterladen";
        notice = document.createElement("p");
        notice.textContent = "Die Dateien landen auf dem DGX im Modellordner. Downloads laufen weiter, wenn du dieses Fenster schließt. Nach einem Server-Neustart erneut starten, um Teildownloads fortzusetzen.";
        const all = document.createElement("button");
        all.textContent = "Alle Workflow-Modelle auf den DGX laden";
        all.onclick = () => {
            const selected = currentModels();
            if (!selected.length) { notice.textContent = "Dieser Workflow enthält keine Modell-Downloadlinks. Lade zuerst einen Workflow mit Modellangaben."; return; }
            enqueue(selected);
        };
        list = document.createElement("div");
        list.style.cssText = "max-height:48vh;overflow:auto;margin:12px 0";
        list.setAttribute("aria-live", "polite");
        const close = document.createElement("button");
        close.textContent = "Schließen";
        close.onclick = () => dialog.close();
        dialog.append(header, notice, all, list, close);
        dialog.addEventListener("close", () => { clearInterval(poll); poll = undefined; });
        document.body.append(dialog);
    }
    if (!dialog.open) dialog.showModal();
    if (!poll) poll = setInterval(refresh, 1500);
    void refresh();
}

async function enqueue(selected) {
    show();
    try {
        // The backend queues downloads sequentially and skips existing files.
        await request("jobs", selected);
        notice.textContent = "Downloads auf dem DGX gestartet. Vorhandene Dateien werden nicht überschrieben.";
        await refresh();
    } catch (error) {
        notice.textContent = `Download konnte nicht gestartet werden: ${error.message}`;
    }
}

app.registerExtension({
    name: "DGX.ServerDownloads",
    async setup() {
        const originalLoad = app.loadGraphData;
        app.loadGraphData = async function (graph, ...args) {
            models.clear();
            remember(graph);
            return originalLoad.call(this, graph, ...args);
        };
        const originalClick = HTMLAnchorElement.prototype.click;
        HTMLAnchorElement.prototype.click = function (...args) {
            // ComfyUI 1.47's single/all-model download actions create an anchor
            // with the download filename. Leave ordinary links/exports alone.
            const host = new URL(this.href, location.href).hostname;
            if (["huggingface.co", "hf.co", "github.com", "civitai.com", "civitai.red"].includes(host) &&
                this.download && /\.(safetensors|sft|ckpt|pth|pt|bin|gguf|onnx)$/i.test(this.download)) {
                const selected = currentModels().find(model => model.name === this.download && new URL(model.url, location.href).href === this.href);
                if (selected) { void enqueue([selected]); return; }
                show();
                notice.textContent = "Modellordner nicht bekannt. Der Download wurde nicht an den Browser weitergegeben. Lade einen Workflow mit Modell-Downloadangaben.";
                return;
            }
            return originalClick.apply(this, args);
        };
        const button = document.createElement("button");
        button.textContent = "DGX Downloads";
        button.title = "Modelle auf dem Server herunterladen und Fortschritt ansehen";
        button.style.cssText = "position:fixed;right:16px;bottom:16px;z-index:1000;padding:9px 14px;background:#244e63;color:white;border:1px solid #70b3d2;border-radius:7px;cursor:pointer";
        button.onclick = show;
        document.body.append(button);
    },
});
