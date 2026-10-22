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
| `kacheln` | 12; erlaubt sind 1–12 |
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
