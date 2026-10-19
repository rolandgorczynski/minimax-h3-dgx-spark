import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "DGX.PosterVision",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "DGXDescribeImage") return;
        const created = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function (...args) {
            const result = created?.apply(this, args);
            const output = document.createElement("textarea");
            output.readOnly = true;
            output.placeholder = "Tutaj pojawi się opis obrazu. Aby go zmienić, skopiuj do pola poprawiony_opis.";
            output.style.cssText = "width:100%;height:150px;box-sizing:border-box;resize:vertical;color:#eee;background:#222;padding:8px;";
            this._captionOutput = output;
            const widget = this.addDOMWidget("wynik_vision", "div", output, { serialize: false });
            widget.computeSize = () => [this.size[0], 160];
            return result;
        };
        const executed = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            executed?.call(this, message);
            if (this._captionOutput && message.text) this._captionOutput.value = message.text.join("\n");
        };
    },
});
