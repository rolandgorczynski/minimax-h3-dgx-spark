# Deutsche Oberfläche

Diese kleine Ergänzung verbindet das lokale Community-Paket
[ComfyUI-Global-Translation](https://github.com/a63976659/ComfyUI-Global-Translation)
mit Frontend 1.47.11. Die Installation aktiviert Deutsch und bewahrt die
vorherigen Benutzereinstellungen in `comfy.settings.json.before-german` auf.

Nach der Installation **Strg+F5** drücken. In den Einstellungen nach
**Übersetzungssprache** suchen; dort stehen **Deutsch** und **English** zur Wahl.
Ein Sprachwechsel lädt die Oberfläche neu. Der Schalter **Übersetzung An/Aus**
oben kann das Community-Paket deaktivieren.

Deutsch fehlt in der nativen Sprachauswahl dieser Frontend-Version. Die separate
Übersetzungssprache verhindert deshalb, dass ComfyUI die Auswahl wieder auf
Englisch zurücksetzt. Das Paket erhält dafür zwei kleine, reproduzierbare
Anpassungen in `js/utils.js`; sie sind unter `text_edits` in
`config/extensions.json` festgehalten. Der Installer akzeptiert ausschließlich
den Originalcode oder genau diese Anpassungen und überschreibt keine anderen
lokalen Codeänderungen. `config.json` ist die veränderbare Laufzeitkonfiguration
des Pakets und wird entsprechend behandelt.

Die Ergänzung vervollständigt häufig verwendete Beschriftungen des neueren
Frontends. Viele Node-Titel und Hilfetexte stammen aus den deutschen Wörterbüchern
des Community-Pakets. Nicht alle Erweiterungen und Beschriftungen sind übersetzt;
einzelne Texte können Englisch bleiben oder sprachlich ungenau sein.

Technische Auswahlwerte, Modell-Dateinamen und Sampler werden nicht übersetzt
(`translate_options=false`). Workflow-IDs und API-Parameter bleiben unverändert.
Die Übersetzung läuft lokal ohne externe Übersetzungsdienste oder API-Gebühren.
