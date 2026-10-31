# Aufteilung der Repositories

Seit dem 31. Oktober 2026 ist die technische MiniMax-H3-/ComfyUI-Basis von den persönlichen Anwendungen getrennt.

| Repository | Inhalt | Workflow-Dateien |
|---|---|---|
| minimax-h3-dgx-spark, öffentlich | ComfyUI, H3, allgemeine Video-Beispiele, Einladungen | `examples/workflows/`, `examples/api/`, `examples/invitations/` |
| comic-studio, privat | Comic-Anwendung, Quellen, Skripte und Comic-Nodes | `examples/comics/workflows/` |
| bitzi-studio, privat | Figuren, Referenzen und Videoproduktion | `examples/api/bitzi_*.json` |
| spark-betrieb, privat | Offline-Backup und Rechnerverwaltung | keine ComfyUI-Workflows |

Die privaten Repositories liegen im selben GitHub-Konto und sind nur mit entsprechender Berechtigung zugänglich. Sie werden unabhängig versioniert. Es werden keine Git-Submodule oder privaten Abhängigkeiten für den öffentlichen Basis-Build benötigt.

Die laufende ComfyUI-Installation und ihre bereits gespeicherten Workflows bleiben erhalten. Der öffentliche Installer installiert weiterhin allgemeine H3-Workflows sowie die vorhandenen Einladungen. Comic-Erweiterungen haben einen eigenen Installer im Comic-Repository. Bitzi-Dateien sind API-Aufträge und keine normalen Canvas-Vorlagen.

Alte lokale Pfade können beim bisherigen Betreiber über ignorierte Symlinks weiter erreichbar sein. Diese gehören nicht zum öffentlichen Checkout und werden für dessen Installation nicht benötigt.

Bereits veröffentlichte ältere Commits wurden nicht umgeschrieben. Der Umzug trennt die aktuelle Entwicklung; er macht früher veröffentlichte Inhalte nicht rückwirkend privat.

Die früheren polnischen Plakat-Vorlagen und ihre Erweiterung wurden anschließend entfernt. Modelle und erzeugte Ausgaben bleiben erhalten.
