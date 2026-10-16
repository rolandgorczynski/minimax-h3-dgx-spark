import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "DGX.Invitations",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "DGXInvitation") return;
        const created = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function (...args) {
            const result = created?.apply(this, args);
            const labels = {
                veranstaltung: "Veranstaltung / Überschrift", veranstalter: "Veranstalter",
                einladungstext: "Einladungstext", datum: "Datum", uhrzeit: "Uhrzeit",
                ort: "Veranstaltungsort", rueckmeldung: "Rückmeldung / Kontakt",
                stil: "Gestaltung", format: "Druckformat", akzentfarbe: "Akzentfarbe (optional)",
                hintergrundfarbe: "Hintergrundfarbe (optional)", hintergrund_staerke: "Eigenes Hintergrundbild: Stärke",
                dateiname: "Ausgabe-Dateiname",
            };
            for (const widget of this.widgets ?? []) if (labels[widget.name]) widget.label = labels[widget.name];
            const container = document.createElement("div");
            container.style.cssText = "display:flex;flex-wrap:wrap;gap:8px;padding:8px;box-sizing:border-box;align-content:center";
            container.textContent = "Nach „Ausführen“ erscheinen hier deine Dateien.";
            this._invitationLinks = container;
            const widget = this.addDOMWidget("invitation_downloads", "div", container, { serialize: false });
            widget.computeSize = () => [this.size[0], 100];
            return result;
        };
        const executed = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            executed?.call(this, message);
            if (!this._invitationLinks || !message.invitation_files) return;
            this._invitationLinks.replaceChildren();
            for (const file of message.invitation_files) {
                const link = document.createElement("a");
                link.textContent = file.label;
                link.href = api.apiURL(`/view?${new URLSearchParams({ filename: file.filename, subfolder: file.subfolder, type: file.type })}`);
                link.target = "_blank";
                link.rel = "noopener";
                link.download = file.filename;
                link.style.cssText = "background:#244e63;color:#fff;padding:7px 10px;border-radius:5px;text-decoration:none;font:13px sans-serif";
                this._invitationLinks.append(link);
            }
        };
    },
});
