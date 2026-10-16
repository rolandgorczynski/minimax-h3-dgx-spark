import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "DGX.GermanLocale",
    init() {
        // The native frontend normalizes unsupported locales to English.
        // Keep the community pack's choice separate from that native setting.
        app.ui.settings.addSetting({
            id: "DGX.Translation.Locale",
            name: "Übersetzungssprache",
            category: ["Comfy", "Übersetzung"],
            type: "combo",
            options: [
                { value: "de", text: "Deutsch" },
                { value: "en", text: "English" },
            ],
            defaultValue: "de",
            tooltip: "Sprache des lokalen Übersetzungspakets. Nach einer Änderung lädt die Oberfläche neu.",
        });
    },
    async setup() {
        const { TUtils } = await import("../ComfyUI-Global-Translation/main.js");
        const { currentConfig, translatedValueSet } = await import("../ComfyUI-Global-Translation/utils.js");
        if (!currentConfig.translation_enabled || !currentConfig.locale.startsWith("de")) return;
        // Fill gaps for the newer frontend using the pack's existing translator.
        const labels = {
            "Run": "Ausführen", "Graph": "Arbeitsfläche", "Nodes": "Knoten",
            "Workflow Overview": "Workflow-Übersicht", "Parameters": "Parameter",
            "Global Settings": "Allgemeine Einstellungen", "Errors": "Fehler",
            "NO FAVORITED INPUTS": "KEINE FAVORISIERTEN EINGABEN",
            "Inputs you favorite will show up here": "Als Favoriten markierte Eingaben erscheinen hier",
            "In the Parameters tab, click": "Im Reiter „Parameter“ klicke auf",
            "on any input to add it here": "neben einer Eingabe, um sie hier hinzuzufügen",
            "Expand job queue": "Warteschlange öffnen", "View details": "Details anzeigen",
            "Error detected": "Fehler erkannt", "Missing Models": "Fehlende Modelle",
            "Resolve before running the workflow": "Vor dem Ausführen beheben",
            "Download a model, or open the node to replace it.": "Lade das Modell herunter oder wähle im Knoten ein anderes aus.",
            "Download": "Herunterladen", "Download all": "Alle herunterladen",
            "Settings": "Einstellungen", "Search Settings...": "Einstellungen suchen …",
            "Search": "Suchen", "Filter": "Filtern", "Templates": "Vorlagen",
            "Workflows": "Workflows", "Models": "Modelle", "Queue": "Warteschlange",
            "Save": "Speichern", "Save As": "Speichern unter", "Cancel": "Abbrechen",
            "Close": "Schließen", "Open": "Öffnen", "Refresh": "Aktualisieren",
            "Clear": "Leeren", "Import": "Importieren", "Export": "Exportieren",
            "Help": "Hilfe", "Browse Templates": "Vorlagen durchsuchen",
            "Extensions": "Erweiterungen", "Language": "Standardsprache",
        };
        for (let count = 0; count <= 100; count++) labels[`${count} active`] = `${count} aktiv`;
        Object.assign(TUtils.T.Menu, labels);
        for (const text of Object.values(labels)) translatedValueSet.add(text);
        TUtils.applyMenuTranslation(app);
    },
});
