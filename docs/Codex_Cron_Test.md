# Cron und Codex gezielt testen

Der Test führt keine Aufgaben aus `todo.txt` aus. Er prüft zuerst die Umgebung und kann danach einen kleinen lesenden Codex-Auftrag starten. Der produktive Comic-Lauf bleibt getrennt und deaktiviert.

## Festgestellte Ursache

Codex liegt unter `/home/jee/.local/bin/codex`. Mit dem nachgebildeten Cron-Pfad `/usr/bin:/bin` wird der bloße Befehlsname `codex` nicht gefunden. Der absolute Aufruf funktioniert. Die vorhandene Anmeldung verwendet ChatGPT; es wird kein zusätzlicher API-Schlüssel eingesetzt.

Ein Hintergrundauftrag verwendet `codex exec`. Ein neuer Testlauf nimmt keine vorherige Unterhaltung wieder auf. Für eine spätere Fortsetzung muss die gewünschte Sitzungskennung ausdrücklich festgelegt werden; `--last` kann eine andere Unterhaltung auswählen.

## Nur die Umgebung prüfen

Im Projektverzeichnis:

```bash
python3 scripts/test_codex_cron.py
```

Das prüft den absoluten Programmpfad, Version und Anmeldestatus ohne Modellauftrag. Eine reproduzierbare minimale Cron-Umgebung:

```bash
/usr/bin/env -i HOME=/home/jee USER=jee LOGNAME=jee SHELL=/bin/sh PATH=/usr/bin:/bin /usr/bin/python3 /home/jee/docker/minimax-h3-dgx-spark/scripts/test_codex_cron.py
```

## Kleinen Funktionstest bewusst ausführen

```bash
python3 scripts/test_codex_cron.py --model-test
```

Dieser einzelne Codex-Aufruf liest nur `todo.txt` und die Fortschrittsdatei und nennt den ersten offenen Arbeitsbereich. Er verwendet den nur lesbaren Sandbox-Modus, eine neue kurzlebige Sitzung, JSON-Ereignisse, eine schema-geprüfte Antwort und ein Zeitlimit von 180 Sekunden. Es gibt keinen automatischen Wiederholungsversuch. Vor und nach dem Test werden ausgewählte Projektdateien und die gespeicherten Geschichten/Aufträge auf Änderungen verglichen.

## Tatsächlicher Einmaltest über Cron

Für den eingerichteten Diagnoseversuch wird derselbe Aufruf mit `--once --model-test` einmal durch Cron gestartet. Eine exklusiv angelegte Startdatei verhindert wiederholte Modellaufrufe. Nach Abschluss entfernt das Testskript ausschließlich die mit `# comic-codex-cron-test-einmalig` markierte eigene Zeile. Die vorherige Crontab liegt zusätzlich im Protokollverzeichnis. Andere Einträge werden beibehalten.

Bei Stromausfall verhindert die vorhandene Startdatei einen erneuten Modellaufruf; ein unvollständiger Test muss zuerst anhand der Protokolle geprüft werden. Ein Cron-Start allein beweist keinen erfolgreichen Codex-Abschluss.

## Protokolle

Alles liegt unter `/home/jee/.local/state/comic-codex-cron-test/`:

- `status.json`: letzter Zustand mit Start-/Endzeit, Rückgabecode und Ergebnis.
- `cron.log`: Standardausgabe und Fehler des tatsächlichen Cron-Aufrufs.
- `crontab-vor-test.txt`: Crontab vor dem Einmaltest.
- `einmalig-gestartet.json`: verhindert einen zweiten Start desselben Einmaltests.
- `lauf-…/ereignisse.jsonl`: Codex-Ereignisse.
- `lauf-…/fehler.log`: Codex-Fehlerausgabe.
- `lauf-…/antwort.json`: abschließende Testantwort, sofern erfolgreich erzeugt.
- `lauf-…/ergebnis.json`: dauerhaftes Ergebnis des jeweiligen Testlaufs.

Lesen:

```bash
cat /home/jee/.local/state/comic-codex-cron-test/status.json
tail -n 40 /home/jee/.local/state/comic-codex-cron-test/cron.log
```

Rückgabecode `0` bedeutet erfolgreicher Test, `124` bedeutet Zeitüberschreitung. Ein anderer Code und die Fehlerprotokolle zeigen beispielsweise ein Anmelde-, Limit- oder Startproblem. Eine Erfolgsmeldung setzt außerdem eine gültige Antwort und unveränderte geprüfte Projekt-/Comicdaten voraus.

Grundlagen: [Offizielle OpenAI-Dokumentation zu nicht interaktiven Codex-Läufen](https://developers.openai.com/blog/codex-as-a-platform) und [strukturierte Codex-Läufe mit Rückgabecode und Zeitlimit](https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex).

## Nachgewiesener Testlauf

Am **26. Oktober 2026 um 07:34 Uhr (Europe/Warsaw)** hat der echte Cron-Dienst den Einmaltest gestartet. Ende um 07:34:11 Uhr, Rückgabecode **0**. Codex hat beide Dateien gelesen und die verbleibenden **364 Skripte** als ersten offenen Arbeitsbereich benannt. Die geprüften Projektdateien, Geschichten und Renderaufträge blieben unverändert. Der Testeintrag wurde entfernt und die übrige Crontab gegen den vorherigen Stand geprüft.

Der produktive Auftrag aus `todo.txt` wurde nicht gestartet; sein bisheriger Cron-Eintrag bleibt auskommentiert.
