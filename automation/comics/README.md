# Selbstständiger Comic-Automat

Eigenständiger Docker-Compose-Dienst mit HTTP-Trigger. Er benutzt die vorhandene
ComfyUI-Installation und die neue Vorlage **04_Comic_Automat_9B**, die auf
**03_Comic_Studio_9B** basiert. Keine eigene GPU- oder Modellinstallation im Dienst.

## Installation und Start

Aus dem Repository-Verzeichnis:

```bash
./scripts/install_comic_automation.sh
docker compose -p comic-automation -f docker-compose.comic-automation.yml up -d --build
curl -fsS http://192.168.1.224:8090/ready
```

Der Installer prüft zuerst die ComfyUI-Warteschlange. Bei laufenden oder wartenden
Aufträgen beendet er sich ohne Neustart. Er installiert zusätzliche Funktionen
und legt die neue Vorlage 04 an. Bestehende gespeicherte Workflows werden weder
überschrieben noch umbenannt; ihre Prüfsummen werden dabei verglichen.

Der separate Compose-Projektname ist **comic-automation**. Netzwerkstandard ist
`minimax-h3-dgx-spark_default`; bei anderem Namen `COMIC_AUTOMATION_NETWORK` setzen.
Der Dienst besitzt keinen Docker-Socket, keine GPU und keinen direkten Zugriff
auf ComfyUIs Datenverzeichnisse. Das einzige eingebundene Repository-Dokument ist
seine schreibgeschützte Workflow-Vorlage. Aufträge und Ergebnisse liegen im eigenen
Volume `comic-automation_comic-automation-data`.

Benötigte vorhandene Modelle in ComfyUI:

- `flux-2-klein-9b-bf16.safetensors` und `flux2-vae.safetensors`
- `qwen_3_8b.safetensors` als Bild-Textencoder des Studio-Renderers

Standardmäßig kommt die Sprache jetzt aus **Ollama auf dem Host außerhalb dieses
Compose-Projekts**: `gemma3:27b` schreibt, `qwen3.6:35b-a3b` übernimmt Kritik,
Bildprüfung und Selbstreflexion. Der Dienst erreicht Ollama über
`host.docker.internal:11434`. Die vorhandene Ollama-Installation wird nicht verändert.
Ihr HTTP-Port muss aus dem Docker-Netz erreichbar sein.

Es werden ausschließlich bereits installierte lokale Modelle benutzt. Der Client
prüft `/api/tags` und `/api/show`, verweigert Cloud-Modelle und öffentliche
Serveradressen und besitzt weder einen Modell-Download noch einen Cloud-Fallback.
Andere installierte Ollama-Modelle lassen sich konfigurieren, sofern sie die
benötigten Fähigkeiten haben; die Bildprüfung benötigt Vision.

`/ready` prüft Erweiterung und installierte Modellnamen. Ein tatsächlicher
Modelllauf ist damit noch nicht geprüft. Mit `COMIC_AUTOMATION_LLM_BACKEND=comfyui`
kann alternativ die bisherige native Textgenerierung verwendet werden; dafür wird
zusätzlich `qwen3vl_8b_fp8_scaled.safetensors` benötigt. Die Ollama-API ist in der
[offiziellen Dokumentation](https://docs.ollama.com/api/chat) beschrieben.

## Verbindliche Sprache: Deutsch

Alle neuen Geschichten, Titel, Erzählertexte und Sprechblasen müssen Deutsch sein.
API-Aufträge mit einer anderen Sprache werden abgelehnt. Ein Themenwunsch, eine
Bewertung oder eine gelernte Empfehlung kann diese Vorgabe nicht ändern.

Vor Figuren-/Bilderzeugung werden Titel und Geschichte separat auf Deutsch geprüft;
vor dem Rendern folgen alle Erzählertexte und Sprechblasen. Bei fremdsprachigen
Texten wird einmal übersetzt und erneut geprüft. Bleibt die Prüfung negativ, stoppt
der Auftrag mit einer Fehlermeldung. Die Sprachprüfung verwendet lokale Modelle;
Eigennamen bleiben erhalten. Bereits archivierte Testausgaben werden nicht überschrieben.

## Einen Auftrag starten

Auf dem DGX-Host:

```bash
curl -fsS -X POST http://192.168.1.224:8090/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "thema": "Eine Archivarin und ein Hausmeister finden einen geheimnisvollen Brief",
    "kacheln": 12,
    "stil": "Großstadt-Noir (düster)",
    "sprache": "de",
    "max_korrekturrunden": 2
  }'
```

Antwort: `202 Accepted` mit `id` und `status_url`. Ohne `thema` denkt sich das
Modell selbst ein Thema aus. Standard sind zwölf Kacheln und neue eigene Figuren.
Es werden frei erfundene Geschichten erzeugt, keine Nachrichten recherchiert.

Ein idempotenter PUT ist ebenfalls möglich:

```bash
curl -fsS -X PUT http://192.168.1.224:8090/jobs/0123456789abcdef0123456789abcdef \
  -H 'Content-Type: application/json' \
  -d '{"thema":"Ein verschwundenes Backup", "kacheln":4, "seed":1984}'
```

Die ID muss 32 hexadezimale Zeichen haben. Derselbe PUT mit denselben Parametern
liefert den bestehenden Auftrag zurück, auch wenn der Seed ursprünglich automatisch
gewählt wurde. Abweichende Parameter unter derselben ID werden abgelehnt.

Parameter:

| Feld | Standard / Bedeutung |
|---|---|
| `thema` | Leer: eigene Idee; sonst Thema oder kurze Vorgabe, maximal 8000 Zeichen |
| `kacheln` | 12 als Vorgabe; jede positive ganze Zahl ist möglich |
| `stil` | Großstadt-Noir (düster), Klassischer Comic, Ligne claire, Manga Schwarzweiß oder Aquarell-Reportage |
| `sprache` | Fest `de`; andere Sprachen werden abgelehnt |
| `max_korrekturrunden` | 2; erlaubt sind 0–3, insgesamt über alle Phasen hinweg |
| `figuren_ids` | Leer: neue Figuren erfinden; sonst bis zu vier bestehende Bibliotheks-IDs ausschließlich als Kopien verwenden |
| `seed` | Zufällig; optional feste Zahl 0–2147483647 |
| `signatur` | Leer; optional eigene Signatur |

## Einfacher lokaler Trigger: manuell oder crontab

Der Haupttrigger ist `POST /jobs`. Ein Aufruf startet einen neuen Auftrag; der
Automat erfindet selbst Geschichte und Figuren, berücksichtigt seine Erfahrungen
und arbeitet ohne notwendige Nutzerbewertung. Die Antwort bestätigt die Annahme,
der Comic entsteht anschließend im Hintergrund.

Minimaler curl-Aufruf:

```bash
curl -fsS -X POST http://192.168.1.224:8090/jobs \
  -H 'Content-Type: application/json' -d '{}'
```

Alternativ steht ein ausführbares Skript bereit, auch unabhängig vom aktuellen
Arbeitsverzeichnis:

```bash
/home/jee/docker/minimax-h3-dgx-spark/scripts/trigger_comic.sh
/home/jee/docker/minimax-h3-dgx-spark/scripts/trigger_comic.sh "Ein verschwundenes Backup"
COMIC_KACHELN=4 COMIC_STIL="Ligne claire" ./scripts/trigger_comic.sh
```

Standard: zwölf Kacheln, Großstadt-Noir, Deutsch, zwei Korrekturrunden. Optional
lassen sich `COMIC_KACHELN`, `COMIC_STIL`, `COMIC_KORREKTURRUNDEN`,
`COMIC_AUTOMATION_URL` und bei eingerichteter Authentifizierung
`COMIC_AUTOMATION_API_TOKEN` als Umgebungsvariablen setzen.
Das Skript gibt die Auftragsantwort aus und wartet nicht auf die Bildgenerierung.
Es wiederholt POST-Anfragen nicht automatisch, um bei Verbindungsabbrüchen keine
zusätzlichen Aufträge auszulösen.

Beispiel für `crontab -e`: jeden Tag um 20:00 Uhr nach der Zeitzone des Hosts:

```cron
0 20 * * * /home/jee/docker/minimax-h3-dgx-spark/scripts/trigger_comic.sh >> /home/jee/docker/minimax-h3-dgx-spark/comic-trigger.log 2>&1
```

Dieser Eintrag ist nur eine Vorlage und wurde nicht installiert. Jeder Cronlauf
legt einen neuen Auftrag an; noch laufende Comics werden durch den einzelnen
Worker nacheinander abgearbeitet. Ergebnisse und Erfahrungen stehen unter
http://192.168.1.224:8090/. Telegram bleibt optional und derzeit deaktiviert.

## Fortschritt und Ergebnisse

Unter **http://192.168.1.224:8090/** gibt es eine Redaktionsseite mit Geschichte,
Comic-Vorschau, Download und optionaler Bewertung. Die erzeugte Geschichte erscheint
bereits nach der Deutschprüfung, während Figuren und Bilder noch entstehen. Die
Anzeige aktualisiert sich automatisch und zeigt bis dahin einen verständlichen
Wartehinweis. Aufträge sind in der Auswahl auch am Titel erkennbar.

```bash
curl -fsS http://192.168.1.224:8090/jobs/AUFTRAGS-ID
curl -fsS http://192.168.1.224:8090/jobs
curl -f http://192.168.1.224:8090/jobs/AUFTRAGS-ID/artifacts/comic-bundle.zip -o comic.zip
```

Der Status enthält Phase, Ereignisse, Warnungen, Fehler und die Download-URLs
aller fertigen Artefakte. Mögliche Zustände:

- `queued`: wartet auf den einzelnen Worker.
- `running`: arbeitet, beispielsweise `story`, `scene_planning`, `rendering` oder `visual_review`.
- `completed`: die automatischen Prüfungen sind bestanden.
- `needs_review`: Korrekturbudget ausgeschöpft; Ergebnis und Prüfbericht zur manuellen Kontrolle.
- `failed`: technischer Fehler mit konkreter Fehlermeldung.

Das Bundle enthält Geschichte, Figurenbeschreibungen und Referenzbilder,
Szenenplan, Einzelillustrationen, beschriftete Kacheln, Gesamtcomic und Prüfberichte.
`workflow.json` lässt sich in ComfyUI öffnen; die Figurenreferenzen sind darin
als Bilder eingebettet und bleiben auch nach dem Aufräumen verwendbar.
Bei nicht behobenen Textüberläufen kann `needs_review` bereits vor der
Bilderzeugung entstehen; dann enthält das Bundle zunächst nur den Entwurf.

## Was der Automat prüft und verbessert

1. Geschichte mit Anfang, Wendung und Ende erfinden; feste Figuren beschreiben.
2. Geschichte durch das Sprachmodell prüfen und gegebenenfalls überarbeiten.
3. Referenzporträts für neue Figuren erzeugen. Ausgewählte vorhandene Figuren nur kopieren.
4. Die Geschichte mit dem vollständigen Sprachmodell in Szenen mit festen Figuren-IDs aufteilen.
5. Szenenfolge, Kontinuität, Sprecher und Textlängen prüfen; Beschriftung vorab tatsächlich setzen.
6. Comic erzeugen und die Dateien sofort in den Dienst kopieren.
7. Jedes Bild mit Qwen3-VL prüfen, einschließlich passender Figurenreferenzen und
   gegebenenfalls der vorherigen Kachel. Beanstandete Szenen gezielt neu erzeugen;
   vorgeschlagene Sprechblasenpositionen können ebenfalls korrigiert werden.
8. Ergebnis und Prüfberichte exportieren und die eigenen temporären ComfyUI-Dateien aufräumen.

Das Korrekturbudget gilt insgesamt, nicht unbegrenzt pro Kachel. Die Geschichte erhält höchstens eine Überarbeitung, damit Budget für Szenen und Bilder übrig bleibt. Eine fehlerhafte
JSON-Antwort darf je Modellaufruf einmal repariert werden. Modellkritik ist eine
zusätzliche Kontrolle, keine Garantie für perfekte Bilder, korrekte Figuren oder
sinnvolle Texte. Das Ergebnis wird niemals automatisch veröffentlicht.

## Selbstanalyse ohne Nutzerbewertung

Nach jedem fertigen Entwurf folgt automatisch die Phase `self_reflection`.
Das lokale LLM untersucht Geschichte, Szenen, Beschriftung und Bildprüfungen und
formuliert höchstens drei konkrete Empfehlungen für zukünftige Comics. Jede Regel
muss auf eine tatsächlich vorhandene Befund-ID verweisen. Die Regeln dürfen nur
als Prompt-Kontext dienen; sie ändern keine Workflows, Programme oder Modelle.

Vorher-/Nachher-Vergleiche zeigen, ob eine Korrektur laut Modellprüfung ein Problem
beseitigte, weniger Befunde brachte, unverändert blieb oder schlechter abschnitt.
Bei schlechter bewerteten Text- oder Szenenüberarbeitungen behält der Automat die
vorherige bessere Fassung; der verworfene Versuch bleibt in der Prüfhistorie sichtbar.
Eine Regel ist zunächst eine **Vermutung**. Erst ein aufgelöster Befund im erneuten
Modellvergleich stützt sie; auch das ist kein objektiver Qualitätsnachweis.

Die Erfahrungen werden unabhängig vom optionalen Nutzerfeedback dauerhaft in der
eigenen Datenbank gespeichert. Jeder neue Auftrag erhält bis zu zwölf Empfehlungen
und die Beobachtungen der letzten drei fertigen Comics. Bereits vorhandene Comics
liefern damit ebenfalls Ausgangsbefunde. Explizite Nutzerwünsche haben Vorrang.
Die selbstständige Analyse braucht keine Bewertung und wartet auf keine Freigabe.

```bash
curl -fsS http://192.168.1.224:8090/learning
```

Die Redaktionsseite zeigt gespeicherte Erfahrungen. Im jeweiligen Export stehen
`reports/learning-input.json`, `reports/self-reflection.json` und die vollständige
Prüfhistorie in `report.json`. Falls die Reflexion technisch scheitert, bleibt der
Comic erhalten; der Fehler wird sichtbar, statt eine Erfahrung zu erfinden.

## Optionales Feedback und nächste Geschichte

Du musst nicht jede Geschichte bewerten. Neue Aufträge sind jederzeit ohne
Bewertung möglich. Gespeichertes Feedback wird vor der nächsten Erzeugung in die
LLM-Vorgaben übernommen: Durchschnittswerte aller Bewertungen und die letzten zehn
bewerteten Geschichten mit Kommentar und Textauszug. Niedrig bewertete Aspekte
sollen verbessert, gute Eigenschaften beibehalten werden. Das ist gespeicherter
Redaktionskontext, kein Training der Modellgewichte.

Die fünf Kriterien sind Verständlichkeit, Spannung, Figuren, Dialoge und Ende/Pointe,
jeweils 1–5. Ein freier Kommentar ist optional. Bewertungen lassen sich ändern und
bleiben im eigenen Volume erhalten. Bereits gestartete Geschichten behalten ihren
gespeicherten Feedbackstand; spätere Aufträge übernehmen den neuesten Stand.

```bash
# Fragen und vorhandene Bewertung anzeigen
curl -fsS http://192.168.1.224:8090/jobs/AUFTRAGS-ID/feedback

# Bewertung speichern, ohne automatisch einen Auftrag zu starten
curl -fsS -X POST http://192.168.1.224:8090/jobs/AUFTRAGS-ID/feedback \
  -H 'Content-Type: application/json' \
  -d '{"bewertungen":{"verstaendlichkeit":4,"spannung":2,"figuren":4,"dialoge":3,"ende":2},"kommentar":"Mehr klare Wendungen, weniger Wortspiele."}'

# Nächste eigene Geschichte, unabhängig davon, ob die vorige bewertet wurde
curl -fsS -X POST http://192.168.1.224:8090/jobs/AUFTRAGS-ID/next
```

`/next` übernimmt Stil, Kachelanzahl und ausgewählte Figuren, wählt einen neuen
Seed und lässt das Modell ein neues Thema erfinden. Wiederholte Aufrufe auf derselben
Ausgangs-ID liefern denselben Folgeauftrag. Für eine weitere Geschichte `/next`
auf dessen neuer ID verwenden. Alternativ erzeugt `POST /jobs` einen unabhängigen
Auftrag, der ebenfalls bisheriges Feedback berücksichtigt. Die Automatik benötigt
keine Bewertung als Freigabe. Der Trigger bleibt bewusst ein HTTP-Aufruf; ein
Zeitplan oder ein dauerhafter Wiederholungsbetrieb ist noch nicht eingeschaltet.

Der verwendete Feedbackstand liegt im Export unter
`reports/editorial-preferences.json`. Die Bewertung kann nur für fertige Entwürfe
(`completed` oder `needs_review`) gespeichert werden.

## Trennung von deiner ComfyUI-Arbeit

Bestehende Workflows, Figuren und Ausgabedateien werden nicht verändert. Der
Automat schreibt auf ComfyUI nur unter dessen temporärem Verzeichnis
`comic-automation/<Auftrags-ID>/`. Neue Figuren bleiben im jeweiligen Auftrag;
die gemeinsame Figurenbibliothek wird nicht beschrieben.

Nach dem verifizierten Download entfernt er nur diesen temporären Ordner und
seine eigenen Verlaufseinträge. Der Server verweigert das Aufräumen, solange ein
eigener Auftrag noch läuft oder in der Warteschlange steht. Fremde Aufgaben werden
niemals abgebrochen; der globale `/interrupt`-Endpoint wird nicht verwendet.

Bei Zeitüberschreitung oder Verbindungsfehler bleibt `cleanup_pending` sichtbar.
Der Dienst versucht das Aufräumen später erneut. Die eigene Auftragsdatenbank und
Zwischenergebnisse bleiben über Container-Neustarts erhalten; laufende Aufträge
werden anhand ihrer gespeicherten ComfyUI-Prompt-IDs fortgesetzt. Wenn ComfyUI
selbst neu gestartet wird, können dessen temporäre Dateien fehlen; dann meldet der
Auftrag einen Fehler statt vorhandene fremde Dateien zu verwenden.

## Konfiguration

Optionale Umgebungsvariablen für Compose; keine Änderung der bestehenden `.env`
notwendig. Die Bezeichnungen haben das Präfix `COMIC_AUTOMATION_`:

- `BIND`, `PORT`: Standard `192.168.1.224:8090`. Die LAN-Adresse lässt sich überschreiben; optional `API_TOKEN` konfigurieren.
- `COMFYUI_URL`: Standard `http://comfyui:8188` im vorhandenen Docker-Netzwerk.
- `NETWORK`: Name des bestehenden ComfyUI-Netzwerks.
- `LLM_BACKEND`: `ollama` (Standard) oder `comfyui`, ausschließlich lokal.
- `OLLAMA_URL`: Standard `http://host.docker.internal:11434`, nur interne Adressen.
- `OLLAMA_TEXT_MODEL`: Standard `gemma3:27b`.
- `OLLAMA_CRITIC_MODEL`, `OLLAMA_VISION_MODEL`: Standard `qwen3.6:35b-a3b`.
- `TEXT_MODEL`, `VISION_MODEL`: Bei Backend `comfyui`, Standard jeweils `qwen3vl_8b_fp8_scaled.safetensors`.
- `PROMPT_TIMEOUT`: Wartezeit je ComfyUI-Aufruf in Sekunden, Standard 3600.

Mit gesetztem `COMIC_AUTOMATION_API_TOKEN` bei allen Auftragsaufrufen
`-H "Authorization: Bearer DEIN-TOKEN"` ergänzen. `/health` bleibt als lokale
Container-Lebensprüfung verfügbar; `/ready` prüft die Anbindung an ComfyUI.

```bash
docker compose -p comic-automation -f docker-compose.comic-automation.yml logs -f
docker compose -p comic-automation -f docker-compose.comic-automation.yml stop
```

`stop` hält nur den neuen Dienst an. ComfyUI und seine übrigen Aufgaben laufen weiter.

## Telegram-Nachricht als Trigger

Der optionale Telegram-Bot verwendet Long Polling und braucht keinen öffentlichen
Webhook. Er nimmt nur Nachrichten aus ausdrücklich freigegebenen Chats an.
Unbekannte Chats, Bot-Nachrichten, Kanalposts und bearbeitete Nachrichten werden
ignoriert. Verwende einen eigenen Comic-Bot, damit keine andere Bot-Anwendung um
dieselben Updates konkurriert. Vorhandene Webhooks werden erkannt und nicht verändert.

1. Einen eigenen Bot bei [@BotFather](https://t.me/BotFather) erstellen.
2. Im Repository `python3 scripts/setup_comic_telegram.py` ausführen. Das Skript
   fragt das Token verdeckt ab, zeigt nach einer `/start`-Nachricht mögliche Chat-IDs
   und speichert Token und Freigaben in `automation/comics/.env.telegram` mit Modus 600.
   Die Datei ist von Git ausgeschlossen. Alternativ die Beispieldatei
   `.env.telegram.example` kopieren und lokal ausfüllen. Token nicht im Chat posten.
3. Aktivieren:

```bash
docker compose -p comic-automation -f docker-compose.comic-automation.yml up -d --build
curl -fsS http://192.168.1.224:8090/telegram
```

Ohne Token oder Chat-Freigabe bleibt Telegram deaktiviert; die HTTP-API arbeitet
weiter. Der Status zeigt keine Zugangsdaten. Bei der ersten Aktivierung wird alter
Nachrichtenrückstau übersprungen; danach bleibt der Empfangsstand über Neustarts
erhalten. Sende den ersten Comic-Auftrag deshalb nach der Aktivierung.

Beispiele als Telegram-Nachricht an den Bot:

```text
/comic
/comic 4 noir Ein Hausmeister entdeckt einen geheimen Raum.
/comic 6 manga Eine Reise durch eine vergessene Bibliothek.
Ein Roboter sucht seinen verlorenen Schatten.
/status
```

Ohne Kachelzahl und Stil gelten zwölf Kacheln und Großstadt-Noir. Eine einfache
Textnachricht wird als Themenvorgabe behandelt. `/comic` ohne Thema lässt den
Automaten selbst eine Geschichte erfinden. Stil-Kürzel sind `klassisch`, `noir`,
`ligne`, `manga` und `aquarell`. `/help` zeigt Hilfe. Die Deutschpflicht bleibt fest.

Der Bot bestätigt den Auftrag und sendet den fertigen Comic als PNG-Datei an
denselben freigegebenen Chat. Bei offenen Prüfhinweisen oder Fehlern meldet er den
entsprechenden Zustand. Optionales Feedback bleibt auf der Redaktionsseite möglich.
Telegram-Nachrichten und Ergebnisse passieren Telegram; alle Modellberechnungen
bleiben lokal. Die Integration benutzt die [offizielle Telegram Bot API](https://core.telegram.org/bots/api).

Aufträge erhalten aus Bot-, Chat- und Nachrichten-ID eine feste ID. Wiederholte
Zustellungen erzeugen keinen zweiten Comic. Empfangsstand und ausstehende Antworten
liegen dauerhaft im eigenen Volume; Antworten werden bei Netzwerkproblemen erneut
versucht. Nach einem Absturz unmittelbar nach dem Versand kann eine Telegram-Antwort
erneut erscheinen, die Comicerzeugung wird dadurch nicht dupliziert.

## Redaktioneller Comic aus einem gelieferten Artikel

`editorial.py` rendert ein von Hand oder im Gespräch ausgearbeitetes Storyboard
unverändert über Workflow 04. Dieser Modus ruft keinen lokalen Geschichtenautor
auf. Ein Beispiel mit zwölf Kacheln liegt unter
`examples/comics/editorial/marius-dick/`. `article.txt` enthält die Quelle,
`storyboard.json` die bearbeitbaren Bildbeschreibungen, Erzählertexte und Figuren.
Die gespeicherten ComfyUI-Workflows und die gemeinsame Figurenbibliothek werden
hierbei nicht überschrieben; Figurenreferenzen werden pro Auftrag kopiert.

Im Container: `python /app/editorial.py /tmp/storyboard.json --job AUFTRAGS_ID`.
Die ID muss aus 32 kleinen Hexadezimalzeichen bestehen. Der Auftrag bleibt im
Status `editing`. Mit derselben ID können Bildbeschreibungen geändert und erneut
gerendert werden; unveränderte Kacheln werden aus dem Cache übernommen.
`python /app/editorial.py --job AUFTRAGS_ID --finalize --review 'Prüfvermerk'`
schließt die Redaktion ab und entfernt nur die eigenen temporären ComfyUI-Dateien.

Optional erzeugt `python3 scripts/layout_editorial_comic.py --job AUFTRAGS_ID
--output AUSGABEVERZEICHNIS` auf dem Host ein Erzähler-Porträt am Kachelrand,
Teilseiten mit je vier Kacheln und eine PDF. Dafür benötigt der Host Pillow.
Diese Layout-Dateien vor dem Abschluss in das eigene Auftragsverzeichnis kopieren,
damit sie im Downloadpaket enthalten sind. Das exportierte Workflow enthält die
Figurenreferenzen; das zusätzliche Seitenlayout ist im Export dokumentiert.

### Ein Aufruf für Rendern, Seitenlayout und Download

Auf dem Docker-Host im Repository:

```bash
python3 scripts/render_editorial_comic.py examples/comics/editorial/marius-dick/storyboard.json
```

Der Aufruf erstellt eine neue Auftrags-ID, rendert mit den lokalen ComfyUI-Modellen,
setzt das Sysop-Porträt (falls im Storyboard aktiviert), erzeugt Teilseiten und PDF,
überträgt diese in den eigenen Auftrag und schließt ihn ab. Das Paket liegt unter
`diagnostics/comics/AUFTRAGS_ID/comic-bundle.zip`. Links und ID werden ausgegeben.
Erforderlich sind Python 3 mit Pillow, Docker-Zugriff und der laufende Comic-Automat.
Kein Workflow wird installiert, ersetzt oder gespeichert. Ein Rohartikel wird hier
nicht automatisch in Szenen zerlegt: Das Storyboard wird zuvor im Gespräch erstellt
und kann als JSON bearbeitet werden. Der lokale Geschichtenautor wird nicht benutzt.

Für Korrekturschleifen zuerst mit `--draft` aufrufen. Nach Szenenänderungen mit
`--job AUSGEGEBENE_ID --draft` erneut aufrufen. Unveränderte Kacheln bleiben im
Cache. Zum Abschluss denselben Aufruf ohne `--draft` verwenden. Abgeschlossene
Aufträge sind gegen erneutes Rendern geschützt; ohne `--job` entsteht eine neue
Fassung. Ein tatsächlicher visueller Prüfvermerk kann mit `--review '…'` ergänzt
werden; das Skript behauptet standardmäßig keine visuelle Prüfung.

Optionen: `--output VERZEICHNIS`, `--base-url URL`, `--container CONTAINER`.
Alternativ werden `COMIC_AUTOMATION_URL`, `COMIC_AUTOMATION_CONTAINER` und für
HTTP-Zugriffe `COMIC_AUTOMATION_API_TOKEN` gelesen. Bei einem Abbruch vor dem
Abschluss die ausgegebene ID mit `--job` weiterverwenden.

## Lokale Vorarbeit und Bildprüfung im redaktionellen Skriptmodus

Die getestete Arbeitsteilung mit Befunden, Grenzen und allen Aufrufen steht in
[Lokale Arbeitsteilung](../../docs/Comic_Lokale_Arbeitsteilung.md).

```bash
python3 scripts/comic_local_assistant.py vorbereiten mein-artikel.txt --output diagnostics/mein-comic/quellenpaket.json
python3 scripts/render_editorial_comic.py mein-storyboard.json --local-check
```

`--local-check` führt nach dem Rendern eine lokale Bildbeobachtung durch und lässt
den Auftrag immer offen. `local-review.json` enthält ausschließlich Prüfhinweise.
Geschichte und Szenen werden nicht umgeschrieben. Formale Regeln bleiben
Skriptprüfungen. Ein semantischer Textvergleich wurde wegen beobachteter Fehlalarme
nicht als Standard aktiviert. Die bisherigen Aufrufe ohne diese Option bleiben erhalten.

## Geschichten auf der Redaktionsseite verwalten

Unter `http://192.168.1.224:8090/` gibt es **Geschichten verwalten**:

1. **Neue Geschichte** öffnet eine leere Definition.
2. Ein fertiges Storyboard als JSON importieren oder eine vorhandene Ausgabe über
   **Ausgewählte Ausgabe übernehmen** in eine bearbeitbare Geschichte kopieren.
3. Titel, Artikel, Szenen, Erzählertexte, Sprechblasen und Bildstil bearbeiten.
   Referenzbilder bleiben beim Import erhalten. Ein Stilwechsel löscht keine Szenen.
4. **Definition speichern** sichert einen Bearbeitungsstand. Gleichzeitige Änderungen
   in einem zweiten Browserfenster werden über die Versionsnummer erkannt.
5. **Speichern und Comic erzeugen** erstellt eine eigene neue Ausgabe. Frühere
   Ausgaben bleiben erhalten. Das eigene Storyboard wird nicht durch einen LLM
   umgeschrieben; der Auftrag bleibt nach dem Rendering zur Sichtprüfung offen.
6. **Storyboard herunterladen** exportiert die bearbeitete JSON zur Verwendung mit
   dem Hostskript. Der Skriptablauf und die direkte redaktionelle Webproduktion verwenden dasselbe
   Seitenlayout: Gesamtbild, Einzelkacheln, Teilseiten, PDF und ZIP mit Workflow.
   Ein vorhandenes Sysop-Erzählerporträt wird dabei erhalten.

Alternativ die Arbeitsweise **Geschichte mit lokalem Modell erfinden** wählen.
Dann wird der Artikelbereich als Themenvorgabe an den bestehenden automatischen
Ablauf übergeben. Dieser Modus darf die Geschichte ausarbeiten und verändern.

**Geschichte löschen** entfernt ihre Definition und die mit ihr erzeugten Ausgaben.
Eine nur als Vorlage übernommene Originalausgabe wird dabei nicht gelöscht.
Einzelausgaben lassen sich separat löschen. Solange eine zugehörige Ausgabe läuft
oder wartet, ist das Löschen gesperrt. Die gemeinsame Figurenbibliothek und
ComfyUIs gespeicherte Workflows bleiben erhalten.

Die Verwaltung speichert Definitionen in einer zusätzlichen Tabelle im bestehenden
Automationsvolume. Ein Kopieren der Storyboard-Referenzen in die gemeinsame
Figurenbibliothek findet nicht statt.

### Schnittstellen

Alle Endpunkte verwenden die vorhandene optionale Bearer-Anmeldung.

| Aufruf | Zweck |
|---|---|
| `GET /styles` | Unterstützte Stile |
| `GET /stories` | Kompakte Liste ohne eingebettete Referenzbilder |
| `GET /stories/<ID>` | Vollständige Definition |
| `POST /stories` | Definition mit `mode`, `name`, `payload` anlegen |
| `POST /stories` mit `from_job` | Vorhandene Ausgabe als Definition übernehmen |
| `PATCH /stories/<ID>` | Definition ändern; aktuelle `version` mitsenden |
| `POST /stories/<ID>/generate` | Neue Ausgabe; aktuelle `version` mitsenden |
| `DELETE /stories/<ID>` | Definition und zugehörige Ausgaben löschen; aktuelle `version` mitsenden |
| `DELETE /jobs/<ID>` | Einzelne nicht laufende Ausgabe löschen |

`mode` lautet `editorial` für unveränderte Storyboards oder `automatic` für den
lokalen Geschichtenautor. `payload` enthält das Storyboard beziehungsweise die
Parameter des bisherigen automatischen Aufrufs. Ein Versionskonflikt oder ein
Löschversuch während der Erzeugung liefert HTTP 409.

## Unterstützte Bildstile

Die Auswahl umfasst elf Stile. Alle verwenden die vorhandenen lokalen Bildmodelle;
die Unterschiede werden durch die jeweiligen Bildanweisungen definiert.

| Stil | Bildwirkung |
|---|---|
| Klassischer Comic | Klare Konturen und zurückhaltende Farben |
| Großstadt-Noir (düster) | Kaltes Blau, tiefe Schatten und filmische Großstadtstimmung |
| Ligne claire | Gleichmäßige Linien, flächige Farben und präzise Architektur |
| Manga Schwarzweiß | Tusche, Rasterflächen und expressive Bildkomposition |
| Aquarell-Reportage | Wasserfarben, Papierstruktur und journalistische Zurückhaltung |
| Graphic Novel realistisch | Detaillierte Texturen und filmische, realistische Darstellung |
| Holzschnitt / Linolschnitt | Geschnittene Formen und starke Schwarzweiß-Kontraste |
| Retro-Zeitungscomic | Begrenzte Farben und sichtbare Druckraster |
| Europäischer Abenteuercomic | Lebendige Farben, klare Handlung und detailreiche Schauplätze |
| Science-Fiction / Cyberpunk | Neonakzente, technische Architektur und futuristische Atmosphäre |
| Warme Alltagsillustration | Weiches Licht, warme Farben und ruhige persönliche Szenen |


## Einfacher Einstieg mit einem eingefügten Artikel

Auf der Redaktionsseite stehen im normalen Ablauf nur Titel, Artikel, Bildstil
und Kachelanzahl im Vordergrund. Der lokale Zugangsschlüssel ist unter
**Verbindungseinstellungen** verborgen und schützt ausschließlich den Zugriff
auf den lokalen Comic-Dienst. Hier keinen OpenAI- oder ChatGPT-Schlüssel eintragen.
Ohne konfigurierten lokalen Zugangsschutz bleibt das Feld leer.

1. Titel und Artikel eingeben, Stil und Kachelanzahl wählen.
2. **Szenen erstellen** anklicken. Die lokalen Modelle planen Figuren und Kacheln
   aus dem Originaltext. Es werden noch keine Bilder erzeugt.
3. Die vorbereiteten Szenen prüfen und gegebenenfalls ändern.
4. **Comic erzeugen** anklicken. Der bestätigte Szenenplan wird gerendert.

Der Titel und der eingefügte Originalartikel bleiben erhalten. Die lokale Planung
ist ein Vorschlag und keine automatische Faktenfreigabe. Nicht wörtlich im
Original belegte Sprechblasen werden entfernt. Bei Änderungen in einem anderen
Browserfenster überschreibt ein verspätetes Planungsergebnis diese nicht.

Speicherstände werden intern weiterhin versioniert; technische Fassungsnummern
werden in der normalen Oberfläche nicht mehr angezeigt. Arbeitsweise,
Storyboard-Import/-Export und Übernahme alter Ausgaben stehen unter **Erweiterte
Optionen**. Ein bereits vollständiges Storyboard kann direkt gerendert werden.
Werden Artikel oder Kachelanzahl verändert, bietet die Seite erneut die Planung an;
ein Stilwechsel erhält den Szenenplan.

`POST /stories/<ID>/plan` startet die Vorplanung mit der aktuellen `version`.
Planungsaufträge sind getrennt von erzeugten Comic-Ausgaben und führen niemals
selbstständig zur Bilderzeugung. Ein erneuter gleichzeitiger Planungsauftrag
für dieselbe Geschichte wird abgewiesen.


### Fortschritt während der Szenenplanung

Nach **Szenen erstellen** zeigt die Seite den aktuellen Arbeitsschritt, erledigte
Schritte sowie Gesamtzeit und Dauer des aktuellen Schritts. Die Schritte lauten:
Figuren erkennen, Geschichte in Kacheln aufteilen, Texte und Zuordnungen prüfen,
Szenen bereitstellen. Eine notwendige Beschriftungskorrektur wird gesondert angezeigt.
Während ein anderer Auftrag läuft, erscheint der Wartestatus.

Die Anzeige fragt den laufenden Auftrag alle zwei Sekunden ab; die Zeit läuft
sekündlich weiter. Die Schrittliste bleibt bei einem Fehler zur Einordnung sichtbar.
Bei verbleibenden Beschriftungsproblemen bleibt der Entwurf bearbeitbar. Die
Bilderzeugung prüft den korrigierten Plan erneut, bevor Bilder gezeichnet werden.
Unbekannte Sprechblasen-Formatangaben lokaler Modelle werden auf das unterstützte
Standardformat zurückgeführt; die gesprochenen Texte werden dabei nicht umgeschrieben.

## Dieselbe Ausgabe anhand einer Bewertung verbessern

**Diesen Comic anhand meiner Bewertung verbessern** ist eine eigene Aktion an der
oben ausgewählten fertigen Ausgabe. Sie speichert die angezeigten Bewertungen und
Bemerkungen und erstellt daraus einen neuen, getrennten Renderauftrag. Das ist
etwas anderes als **Neue Geschichte erfinden**, das eine neue Handlung schreibt.

Für die Verbesserung gilt:

- Der aktuell oben ausgewählte **Bildstil** wird übernommen.
- Die **Kachelanzahl stammt ausschließlich aus der bewerteten Ausgabe**. Eine
  andere Zahl im Eingabeformular ändert sie bei dieser Aktion nicht.
- Titel, Originalgeschichte, Figuren-IDs, Referenzbilder und gesprochene Zitate
  bleiben erhalten. Änderungen betreffen Bildregie, sichtbare Zustände je Figur
  und bei Bedarf Erzählertexte.
- Wortgleiche Wiederholungen eines Sprechblasentexts im Erzählerkasten werden entfernt.
- Pro Kachel können Zustände unter `character_states` festgehalten werden, etwa
  Haarlänge oder Kleidung. Dadurch lässt sich eine Veränderung eindeutig einer
  Figur zuordnen, während das Gesicht über die Referenz erhalten bleibt.
- Bei gleichem Stil werden unveränderte Illustrationen übernommen; nur betroffene
  Bilder werden neu erzeugt. Ein Stilwechsel zeichnet alle Bilder neu.
- Das Original wird nicht überschrieben. Während es als Grundlage einer laufenden
  Verbesserung benötigt wird, kann es nicht gelöscht werden.

Die neue Ausgabe enthält `improvement-report.json` mit Bewertungsstand,
Stilentscheidung, Kachelanzahl, entfernten Doppeltexten und Änderungen pro Kachel.
Die Seite zeigt diese Angaben unter **Was geändert wurde**. Modellvorschläge und
neue Bilder müssen weiterhin gesichtet werden; die neue Ausgabe bleibt zur
Prüfung offen. Der gespeicherte Geschichtenentwurf wird nicht stillschweigend
überschrieben.

`POST /jobs/<ID>/improve` akzeptiert ausschließlich das optionale Feld `stil`.
Kachelanzahl und andere unveränderliche Vorgaben werden nicht aus dem Aufruf
übernommen. Fehlt eine gespeicherte Bewertung, wird der Aufruf abgewiesen.
Die Bildkorrektur arbeitet mit lokalen Modellen. Der private Hilfsendpunkt
`/dgx-comics/automation/retain-panel` übernimmt Originalillustrationen nur in die
temporäre Umgebung des neuen Auftrags; gemeinsame Figuren und gespeicherte
ComfyUI-Workflows werden dabei nicht verändert.


### Kommentar ohne Punkte speichern

Im optionalen Feedback genügt ein Kommentar. Alle fünf Punktbewertungen sind
freiwillig und können unter **Punkte vergeben (optional)** einzeln ergänzt werden.
Leere Auswahlfelder werden nicht als null Punkte gespeichert und fließen nicht in
Durchschnittswerte ein. Auch ein reiner Kommentar kann für **Diesen Comic anhand
meiner Bewertung verbessern** verwendet werden. Das Speichern allein startet
weiterhin keinen neuen Lauf.

API-Beispiel: `POST /jobs/<ID>/feedback` mit
`{"kommentar":"Bitte die Sprechblasen korrigieren."}`. Ein vollständig leeres
Feedback wird abgewiesen.

## Comic-Bilder für Substack teilen

Bei einer fertigen Ausgabe steht **Auf Substack teilen** neben den Downloads.
Der Dialog verwendet ausschließlich bereits vorhandene Kacheln; er startet keine
Geschichten-, Modell- oder Bildgenerierung.

Unter **Meine Veröffentlichungsziele** trägst du deine Substack-Adresse und optional
deine X-Adresse selbst ein. Beide Felder sind anfangs leer und bleiben frei
änderbar. Die Einstellungen liegen dauerhaft im Automationsvolume. Das Eintragen
einer Profiladresse verbindet kein Konto und erfordert keinen ChatGPT-Schlüssel.

**Bildpaket laden und Substack öffnen** öffnet die gespeicherte Substack-Adresse
und lädt eine ZIP-Datei mit nummerierten PNG-Kacheln, Titel und kurzer Anleitung.
Die ZIP-Datei entpacken und die PNGs im Substack-Editor der Reihe nach einfügen.
Dort Darstellung prüfen und veröffentlichen. Die Funktion meldet weder einen
Upload noch eine Veröffentlichung, die sie nicht tatsächlich ausführt.

Die Bilder behalten ihre Originalpixel. Technische PNG-Textdaten einschließlich
eingebettetem ComfyUI-Workflow und Figurenreferenzen werden aus den Freigabekopien
entfernt. Die Originaldateien und das vollständige Comic-Paket bleiben unverändert.
Das Bildpaket enthält keine PDF. Einzelkacheln lassen sich im Dialog ansehen und
separat herunterladen.

Auf unterstützten Geräten bietet **Über eine App teilen** zusätzlich das native
Teilen der Bilddateien an. Welche Apps erscheinen und Dateien akzeptieren, bestimmt
das Gerät. Die Web Share API benötigt einen sicheren Browserkontext, gewöhnlich
HTTPS oder localhost. Unter `http://192.168.1.224:8090` steht deshalb der
Bildpaket-Weg zur Verfügung. Ein vollautomatischer Substack-Upload oder ein
Veröffentlichen ohne den Substack-Editor ist mit dieser Version nicht eingerichtet.
**Auf X teilen** öffnet denselben Bilddialog für X. Nach dem Speichern deiner
frei wählbaren X-Profiladresse öffnet **Bildpaket laden und X öffnen** den
X-Beitragseditor mit dem Titel als vorbereitetem Text und lädt die PNGs herunter.
Die Bilder anschließend selbst anhängen; längere Comics lassen sich beispielsweise
mit vier Kacheln je Beitrag als Thread veröffentlichen. **Mein X-Profil öffnen**
öffnet die eingetragene Profiladresse. Diese Adresse wählt kein angemeldetes Konto
aus: Prüfe das Konto im X-Editor. Es werden keine Bilder automatisch hochgeladen
oder Beiträge automatisch veröffentlicht. Es sind keine X-API-Schlüssel erforderlich.
Der Editor verwendet [X Web Intent](https://publish.x.com/); das Anhängen und
Veröffentlichen erfolgt wie in der [X-Anleitung für Bilder](https://help.x.com/en/using-x/posting-gifs-and-pictures).

| Aufruf | Zweck |
|---|---|
| `GET /sharing` | Gespeicherte, frei konfigurierbare Zieladressen |
| `PUT /sharing` | `substack_url` und `x_url` speichern; leere Werte sind möglich |
| `GET /jobs/<ID>/share` | Titel und nummerierte Bildadressen |
| `GET /jobs/<ID>/share/images/01.png` | PNG-Kopie ohne technische Textmetadaten |
| `GET /jobs/<ID>/share/images.zip` | Bildpaket aus vorhandenen Kacheln |

Diese Endpunkte verwenden den vorhandenen optionalen lokalen Zugangsschutz.
Sie senden keine Beiträge an externe Dienste.

Quellen: [Beiträge auf Substack veröffentlichen](https://support.substack.com/hc/en-us/articles/360037831771-How-do-I-publish-a-new-post-on-Substack)
und [Web Share API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Share_API).

## Figuren unter „Erweiterte Optionen“

**Figuren dieser Geschichte** zeigt die Besetzung mit Referenzbildern. Jede Karte
lässt sich öffnen; Name, festes Aussehen, Kleidung, Vorgeschichte, Persönlichkeit,
Motivation und Gesinnung sind bearbeitbar. Änderungen mit **Speichern** an der
Geschichte sichern. Referenzbilder lassen sich als PNG, JPEG oder WebP hochladen;
die Freigabe erfolgt weiterhin ohne private Referenzbilder und Profilangaben.

Die Gesinnung ist freiwillig. Das klassische RPG-Raster verbindet
rechtschaffen / neutral / chaotisch mit gut / neutral / böse. **Nicht festgelegt**
ist die Standardeinstellung und ausdrücklich etwas anderes als **Neutral**.
Nicht gesetzte Werte werden dem Szenenmodell nicht als Gesinnung vorgegeben.
Bei journalistischen Artikeln sind diese Angaben Gestaltungsvorgaben und dürfen
keine unbelegten Aussagen oder Änderungen an der gelieferten Handlung erzeugen.

Die **Wiederverwendbare Figurenbibliothek** zeigt auch Sysop und andere gespeicherte
Figuren. **In diese Geschichte übernehmen** legt eine bearbeitbare Kopie mit
Referenzbildern an. **Bibliotheksfigur speichern** ändert das wiederverwendbare
Profil; **In Bibliothek speichern** übernimmt einen Geschichtencharakter in die
Bibliothek. Vorhandene Figuren-IDs werden dabei erhalten. Bibliotheksänderungen
werden mit Versionsprüfung gespeichert, damit parallele Bearbeitung nicht
unbemerkt überschrieben wird.

**Aussehen & Gesinnung neu erzeugen** startet ausschließlich einen Figurenauftrag
mit den eingerichteten lokalen Modellen: Das lokale Sprachmodell entwirft die
Beschreibung und optional eine RPG-Gesinnung; ComfyUI zeichnet ein neues
Referenzbild im oben gewählten Stil. ID, Name, Vorgeschichte, Persönlichkeit,
Motivation und Kleidung bleiben erhalten. Ohne Haken bei **Beim Neuerzeugen auch
eine Gesinnung bestimmen** bleibt die neue Gesinnung nicht festgelegt.
Das Ergebnis wird zunächst im Editor gezeigt und muss gespeichert werden.
Diese Funktion erzeugt keinen neuen Comic und ändert keine gespeicherten Workflows.
Bereits gerenderte Comic-Bilder werden durch Profiländerungen nicht verändert.

**Aus Geschichte löschen** entfernt die Figur sowie ihre Sprecherzuordnungen und
Sprechblasen aus dem Entwurf; die Szenentexte danach selbst prüfen. **Aus Bibliothek
löschen** entfernt das wiederverwendbare Profil, bewahrt aber gespeicherte
Figurenkopien und unveränderliche Referenzdateien. Wird eine Figur von einer
Definition noch direkt über eine Bibliotheks-ID verwendet, wird das Löschen
verhindert, bis diese Geschichte eine eigene Kopie enthält.

| Aufruf | Zweck |
|---|---|
| `GET /characters` | Bibliothek und auswählbare Gesinnungen |
| `POST /characters` | Bibliotheksprofil mit Versionsprüfung speichern |
| `DELETE /characters/<ID>` | Bibliotheksprofil mit Versionsangabe entfernen |
| `GET /characters/<ID>/references/<DATEI>` | Gespeichertes Referenzbild anzeigen |
| `POST /characters/regenerate` | Lokalen Figurenauftrag anlegen, Felder `profile`, `style`, `determine_alignment` |
| `GET /characters/regenerations/<AUFTRAGS-ID>` | Fortschritt und nach Abschluss das neue Profil |

Der Figurenauftrag läuft in derselben dauerhaften Warteschlange wie Comics,
übernimmt deren lokalen Zugangsschutz und bereinigt nur seine eigene ComfyUI-Sitzung.

## Originalgespräche von Anfang an als Sprechblasen

Beim Klick auf **Szenen erstellen** werden zuerst die Figuren erkannt. Danach
werden die Gesprächszitate aus dem Ausgangstext in einer Dialogliste gesichert.
Unterstützt sind deutsche, französische und gerade Anführungszeichen sowie
Sprecherzeilen wie `Markus: Nein! Nein!`. Eindeutige Sprecherangaben vor oder
nach dem Zitat werden direkt übernommen. Für Zuordnungen aus dem Gesprächskontext
wird das bereits eingerichtete lokale Sprachmodell verwendet.

Zitierte Begriffe, Schriftstücke und Gedanken werden von gesprochenen Worten
getrennt. Unsichere Sprecher und unbestimmte Alternativen wie „Oh!“ oder „Uh!“
bleiben als offene Hinweise sichtbar; sie werden nicht als sichere Aussage
übernommen. Eine Modellzuordnung ist trotzdem vor dem Rendern redaktionell zu prüfen.

Der Szenenplan verteilt ausschließlich die IDs der erkannten Gesprächszitate
auf die Kacheln. Der Originalwortlaut und die Figur werden anschließend aus
der Dialogliste eingesetzt. Die Prüfung verhindert fehlende, doppelte,
vertauschte und frei erfundene Gesprächseinträge. Längere Originalzitate werden
an Wortgrenzen auf mehrere Sprechblasen verteilt, ohne sie umzuschreiben oder
Auslassungszeichen einzufügen. Bei zu viel Text wird die Verteilung erneut
geprüft; ungeklärte Platzprobleme bleiben als Hinweise am bearbeitbaren Entwurf.

**Erzählertext** ist optional und dient Handlung, Ort, Zeit oder Übergängen.
Gesprochene Originalzitate gehören in **Gespräche / Sprechblasen**. Wortgleiche
Doppelungen werden entfernt. Jede Sprechblase lässt sich mit Figurenauswahl,
Text und Sprechweise bearbeiten, hinzufügen oder entfernen. Positionen und
weitere Angaben bleiben im aufklappbaren JSON-Editor verfügbar.

Die Schrift wird bei neuen gerenderten Sprechblasen nicht unter 22 Pixel,
beim Flüstern nicht unter 20 Pixel verkleinert. Sprechernamen werden nur im Editor angezeigt; neue Erzählerkästen bleiben
mindestens 24 Pixel groß, jeweils
bezogen auf die 768 × 672 Pixel große Einzelkachel. Passt Text damit nicht,
meldet die Layoutprüfung den Platzmangel. Das garantiert keine Lesbarkeit
nach beliebiger Verkleinerung durch Plattformen; die Original-PNGs vor dem
Posten in der tatsächlichen Darstellung prüfen.

Die Dialogliste liegt unter `dialogue_ledger` in der bearbeitbaren Geschichte
und als `dialogue-ledger.json` im privaten Planungsauftrag. Sie wird nicht in
das öffentliche Bildpaket für Substack oder X aufgenommen. Das Einspielen
dieser Funktion verändert weder vorhandene Szenenpläne noch fertige Comics
und startet keinen neuen Lauf.

Für eine bereits gespeicherte Geschichte kann unter **Erweiterte Optionen →
Szenen neu planen** die neue Dialogübernahme ausdrücklich gestartet werden. Der
bisherige Szenenentwurf wird nach Bestätigung ersetzt; Figurenprofile, Artikel
und bereits erzeugte Comics bleiben erhalten. Erst nach der anschließenden
Prüfung auf **Comic erzeugen** klicken. Die Installation selbst startet nichts.

## Sprechblasen mit der Maus positionieren

Bei einer fertigen Ausgabe mit vorhandenen Originalzeichnungen steht
**Sprechblasen positionieren** neben den Downloads. Der Dialog arbeitet mit der
ausgewählten Comic-Ausgabe; die bearbeitbare Geschichten-Definition bleibt dabei
unverändert.

- **Verschieben:** den blauen Rahmen einer ausgewählten Sprechblase ziehen.
- **Größe:** eine der vier blauen Ecken ziehen. Die Schrift wird nicht unter die
  festgelegte Mindestgröße verkleinert.
- **Sprecherziel:** den gelben Punkt am Schweif zur sprechenden Figur ziehen.
- **Schutzbereiche:** **Bereich schützen** aktivieren und ein Rechteck um Gesicht,
  Hand oder ein wichtiges Detail ziehen. Bereiche lassen sich einzeln entfernen.
- **Automatisch anordnen:** sucht freie Positionen mit wenig Bildstruktur,
  berücksichtigt Leserichtung, andere Blasen, Randabstand, Erzählerkasten und
  markierte Schutzbereiche. Die Schweifziele bleiben erhalten. Es findet keine
  automatische Gesichtserkennung statt; die Positionen anschließend prüfen.
- **Rückgängig:** stellt die vorherige Bearbeitung wieder her.

Während des Ziehens wird eine vereinfachte Vorschau gezeigt. Nach dem Loslassen
folgt die exakte Beschriftung aus demselben Layoutmodul wie beim Export.
Überschneidungen mit anderen Blasen, Erzählerkasten oder Schutzbereichen werden
angezeigt. Bei zu wenig Platz für lesbaren Text ist das Übernehmen gesperrt.
Beim Speichern werden alle Kacheln erneut geprüft, auch die gerade nicht sichtbaren.

**Neue Beschriftung übernehmen** erzeugt eine eigene Ausgabe mit aktualisierten
PNG-Kacheln, Gesamtbild, Teilseiten, PDF und Downloadpaket. Die Dateien
`panels/NN_art.png` werden bytegleich übernommen. Der ursprüngliche Comic und
seine Dateien bleiben erhalten. Das läuft als CPU-Layout ohne LLM, Diffusionsmodell,
ComfyUI-Auftrag oder Änderung an gespeicherten Workflows. Lediglich die Illustration
wird wiederverwendet; Sprechblasen und Erzählerkästen werden neu gezeichnet.

| Aufruf | Zweck |
|---|---|
| `GET /jobs/<ID>/lettering` | Kacheln, Figuren und Versionskennung zum Positionieren |
| `POST /jobs/<ID>/lettering/preview` | Exakte Vorschau und Layoutprüfung ohne Speichern |
| `POST /jobs/<ID>/lettering/automatic` | Vorschlag unter Beachtung geschützter Bereiche |
| `POST /jobs/<ID>/lettering` | Geprüfte Beschriftung als neue Ausgabe vormerken |

Die POST-Anfragen verwenden `version` aus dem GET-Aufruf. Vorschau und automatische
Anordnung erwarten zusätzlich `panel` (ab 0) und `layout` mit `dialog`, `bubbles`
und `protected_areas`. Zum Übernehmen `panels` mit genau einem solchen Layout pro
Kachel senden. Der vorhandene lokale Zugangsschutz gilt auch für diese Endpunkte.

Das Automationsimage enthält dafür [Pillow](https://pypi.org/project/pillow/) und
Kopien der gemeinsam verwendeten Layoutmodule und Schrift. Die Compose-Datei
übergibt diese Verzeichnisse als zusätzliche Build-Kontexte; normale Builds über
`docker compose -p comic-automation -f docker-compose.comic-automation.yml build`
übernehmen sie automatisch.

Die Aufteilung der Originalgespräche wird vom Skript vor der Bildbeschreibung
festgelegt. Dazu entstehen chronologische Quellabschnitte, die den gesamten
Artikel einschließlich des Schlusses abdecken und keine Zitate zerschneiden.
Sprechlast und Textumfang fließen in die Aufteilung ein. Das lokale Modell
formuliert für jeden vorgegebenen Abschnitt die Bildkomposition. Seine eigenen
`quote_ids` oder `bubbles` werden nicht übernommen; gesicherte Sprecher und
Originaltexte werden aus der Dialogliste eingesetzt. Dadurch führen erfundene
Zitat-IDs oder versehentlich verwendete unsichere Zitate nicht mehr zum Abbruch
`Nur gesprochene Zitat-IDs als Sprechblasen verwenden`. Bildbeschreibungen und
Sprecherzuordnungen aus dem Kontext bleiben vor dem Rendern redaktionell zu prüfen.

Bei einer fehlgeschlagenen Szenenplanung ist der Auftrag bereits beendet.
Der Fortschrittsbalken läuft dann nicht weiter. Direkt im Fehlerbereich stehen
**Szenenplanung neu starten** und **Fehler schließen** bereit. Schließen markiert
den alten Fehler dauerhaft als erledigt, ohne Artikel, Figuren, vorhandene
Szenen oder die gespeicherte Fehlerdiagnose zu löschen. Ein Neustart geschieht
nur nach ausdrücklichem Klick. Dafür steht auch weiterhin **Erweiterte Optionen →
Szenen neu planen** zur Verfügung. Die Hauptschaltflächen werden nach einem
Fehler wieder freigegeben.

## Blasenform wählen, ohne Sprechernamen im Bild

In **Gespräche / Sprechblasen** sowie **Sprechblasen positionieren** besitzt jede
Blase die Auswahl **Blasenstil**: Abgerundet, Oval, Eckig, Gedankenwolke, Gezackt,
Gestrichelt oder Nach Sprechweise. Die Sprechweise steuert die Betonung und
Schriftgröße; die separat gewählte Blasenform bleibt davon unabhängig. Nur
**Nach Sprechweise** wählt bei Rufen eine gezackte und bei Flüstern eine
gestrichelte Form. Gedankenwolken haben kleine Verbindungsblasen statt eines
durchgehenden Schweifs.

Im Positionierungsdialog kann **Stil auf alle Blasen anwenden** die ausgewählte
Form für den gesamten Comic setzen. Das ändert zunächst den Entwurf im Dialog;
**Rückgängig** stellt die vorherigen Stile wieder her. Erst **Neue Beschriftung
übernehmen** speichert eine neue Ausgabe und prüft alle Kacheln auf Textpassung.

Sprechernamen erscheinen nicht mehr als zusätzliche Überschrift in den Blasen.
Die Figurenzuordnung bleibt als `speaker` erhalten und ist im Editor sichtbar.
Auch ältere Angaben `show_name: true` erzeugen bei einer neuen Beschriftung
keine Namen mehr. Die Form liegt im Feld `bubble_style`; ohne Angabe ist sie
abgerundet. Fertige PNGs ändern sich erst, wenn die neue Beschriftung ausdrücklich
übernommen wird. Die vorhandenen Zeichnungen werden dafür nicht neu erzeugt.

## Genau ein Bild mit einem Korrekturtext neu erzeugen

Unter **Sprechblasen positionieren** steht bei einer fertigen Ausgabe das Feld
**Ein Bild korrigieren**. Bild auswählen, den Korrekturwunsch eingeben und auf
**Nur dieses Bild neu erzeugen** klicken. Beispiel: **Bild 4** auswählen und
`Bei Ria die Haare kürzer, kinnlanger Bob. Alles andere beibehalten.` eintragen.
Die kleine Vorschau zeigt die ausgewählte bisherige Kachel.

Der Auftrag übernimmt die Figurenreferenzen und den Bildstil dieser Ausgabe.
Ein lokales Modell liest das Bild und übersetzt den Wunsch in eine korrigierte
Bildbeschreibung und gegebenenfalls einen Figurenzustand nur für diese Kachel.
Danach enthält der Bildgenerierungsgraph genau **eine** Kachel. Die anderen
Originalzeichnungen und fertig beschrifteten Kacheln werden bytegleich übernommen;
Titel, Artikel, Dialoge, Sprecher, Blasenstile und Kachelanzahl bleiben erhalten.
Figurenbibliothek und gespeicherte Workflows werden nicht geändert.

Das Ergebnis ist eine eigene Ausgabe mit aktualisiertem Gesamtbild, Teilseiten,
PDF und Downloadpaket. Die Originalausgabe bleibt erhalten. Korrigierte Kachel
und Blasenpositionen anschließend prüfen. Für eine weitere Korrektur die neue
Ausgabe verwenden, wenn die erste Änderung erhalten bleiben soll.

`POST /jobs/<ID>/correct-panel` erwartet `version` aus
`GET /jobs/<ID>/lettering`, `panel` als Index ab 0 und `correction` mit 1–2000
Zeichen. Stil und Kachelanzahl werden vom Ausgangscomic übernommen und sind in
diesem Aufruf nicht überschreibbar. Eine andere Bildnummer im Kommentar als in
der Auswahl wird zurückgewiesen. Doppelte laufende Korrekturen derselben Kachel
werden verhindert. Das private `panel-correction-report.json` dokumentiert
Korrektur, betroffene Kachel, übernommene Bilder und die geänderte Bildbeschreibung.

## Freie Kachelanzahl, EPUB und Taschenbuch

Die feste Begrenzung auf zwölf Kacheln ist entfernt. Große Aufträge werden in
Abschnitten geplant und in Einzelbildern gezeichnet. Der Szeneneditor zeigt
je zwölf Kacheln pro Bearbeitungsseite; beim Blättern bleiben alle Eingaben
erhalten. `comic.png` zeigt bei großen Comics eine gekennzeichnete Vorschau,
Teilseiten und Buch-Exporte enthalten alle Kacheln.

Unter **Buch exportieren: EPUB & Taschenbuch** können Autor, Buchtitel,
Impressum, Texte für Anfang und Ende, Klappentext und Druckeinstellungen
festgelegt werden. Die Dateien entstehen aus vorhandenen Kacheln ohne neuen
Bildlauf. Details, KDP-Prüfungen, Einschränkungen und API stehen in
[Comic-Bücher für KDP](../../docs/Comic_Buecher_KDP.md).

## Bücher und Filme als Vorlagen

Der neue Quellenbereich erstellt lokal ein bearbeitbares deutsches Comic-Skript
und übernimmt es direkt als neue Geschichte. Bilder werden erst nach deiner
Prüfung gestartet. Quellen sind erweiterbar und bleiben gespeichert.
[Bedienung, Skriptformat und API](../../docs/Comic_Quellengenerator.md).

## Serien und Fortsetzungen

Über „Auf dieser Geschichte aufbauen“ eine eigene Folge mit denselben Figuren
und Referenzbildern anlegen. Feste Fakten, offene Fäden und der bisherige Schluss
gehen als Kontext in die Szenenplanung ein. Das Anlegen startet keinen Modell-
oder Bildlauf. [Bedienung und API](../../docs/Comic_Serien.md).

## Experimentelle Regiefassungen

„Mehr Wow · Experiment“ erzeugt aus der ausgewählten fertigen Ausgabe eine
eigene Variante mit Reglern für Spannung, Wut, Action, Blut, Dialoge und Bildwirkung.
Dramaturgie und Dialoge dürfen optional frei überarbeitet werden. Das Original
bleibt erhalten. [Ablauf und API](../../docs/Comic_Experimente.md).
