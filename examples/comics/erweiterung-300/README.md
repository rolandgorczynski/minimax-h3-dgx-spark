# Die nächsten 100 Sagen, Mythen und Legenden

**100 neue Skripte fertig und importiert. Die Auswahl umfasst jetzt 300 Geschichten.** Die separate Schneiderlein-Referenz bleibt zusätzlich erhalten.

Alle Szenen, Erzählertexte und Dialoge wurden von Codex selbst aus den vollständigen historischen Quellen und den vorhandenen redaktionellen Sinnanalysen geschrieben. Kein lokales oder separates Modell wurde als Ersatzautor eingesetzt. Es wurden keine Bilder erzeugt und keine bestehenden Geschichten oder Workflows überschrieben.

## Ablauf und Gestaltung

Jede Geschichte übernimmt die empfohlene Kachelzahl ihrer Sinnanalyse. Jede dritte Kachel enthält Erzählertext; zusätzliche Erzählertexte erklären erforderliche Übergänge. Kacheln ohne Gespräch haben nur Erzählertext. Erzähler und gesprochener Dialog werden nicht in derselben Kachel kombiniert. Jeder Dialog ist einer sichtbaren Figur eindeutig zugeordnet.

Die Bildbeschreibung beschreibt einen einzelnen Moment. Figuren erhalten eigene stabile Kennungen. Kleidung, Waffen und wichtige Gegenstände sowie Tod, Geistererscheinung und ausdrücklich beschriebene Veränderungen werden im Kontinuitätsregister geführt. Beispielsweise bleibt die Scheide bei gezogener Klinge leer, ein weggeworfener Ring verschwunden und ein abgelegter Spaten zurück. Vorherige Referenzfiguren werden nicht überschrieben.

Die Sagen bleiben als Überlieferungen erkennbar; getrennte Fassungen und verschiedene Zeitebenen werden nicht zu einer gleichzeitigen Handlung vermischt. Gewalttaten werden gegebenenfalls erzählt, aber nicht drastisch bebildert. Historische Abwertungen werden nicht als heutige Tatsachen übernommen.

Der Bildstil bleibt offen und wird in Schritt 2 gewählt. Die neuen Figuren haben noch keine Referenzbilder. Die redaktionelle und technische Prüfung ersetzt keine Sichtprüfung der später erzeugten Bilder.

## Prüfung

100 neue Geschichten mit **1.180 Kacheln**. Nach dem Import wurden Figuren und Szenen aus der Studio-API zurückgelesen und vollständig mit den lokalen Definitionen verglichen. Quelltext-Hashes und empfohlene Kachelzahlen stimmen; die Beschriftungsprüfung meldet keine ungelösten Textfelder. Die vollständigen Ergebnisse stehen in [Abschlusspruefung.json](Abschlusspruefung.json).

Die bisherigen 200 Auswahlkennungen bleiben erhalten; die 100 neuen Kennungen sind davon verschieden. Das Dashboard wurde in beiden Geschichtenauswahlen und im Quellenkatalog mit jeweils 300 Einträgen ohne JavaScript-Fehler geprüft. Der automatische Skript-Cron bleibt pausiert. Weitere Quellen bleiben zurückgestellt.

## Grundlage und Nachweise

Grundlage dieser Erweiterung ist Ludwig Bechsteins *Deutsches Sagenbuch* (1853), nach der bereits im Projekt abgelegten historischen Textfassung. Jede Definition enthält den vollständigen Quelltext, Originaltitel, Autor, Editionsangabe, Herkunftslink und die vorhandenen Rechte- und Transkriptionsnachweise unter `source_provenance`. Die neuen Comictexte sind redaktionelle Bearbeitungen, keine Übernahme moderner Comicfassungen.

Die Transkriptionsnachweise nennen TextGrid und www.editura.de, Digitale Bibliothek, mit [CC BY 3.0 DE](https://creativecommons.org/licenses/by/3.0/de/). Editorische Annotationen und fremde Bilder werden nicht übernommen. Die jeweiligen Quellseiten sind unten direkt verlinkt.

## Dateien und Wiederholbarkeit

- `Auftrag.json`: diese 100 Quellen mit Hash und empfohlenem Umfang.
- `Redaktion.json`: selbst verfasste Figuren, Regie, Texte und Zustandswechsel.
- `Pruefbericht.json` und `*-beschriftungspruefung.json`: technische Beschriftungsprüfung.
- `Importiert.json`: Kennungen der neu angelegten Studio-Geschichten.
- `Abschlusspruefung.json`: Gesamtvergleich mit dem laufenden Studio.
- `*.txt`: kopierbare Lesefassung im Eingabeformat.
- `*.json`: vollständige Studio-Definition mit Quelle und Sinnanalyse.

Die lokalen Artefakte lassen sich ohne Modellaufrufe reproduzieren. Dieser Befehl erstellt keine Bilder und verändert das Studio nicht:

```bash
python3 scripts/build_comic_selection_extension.py --folder examples/comics/erweiterung-300 --namespace comic-auswahl-300
```

Einzelne Definitionen können mit `python3 scripts/import_comic_script.py DATEI` zunächst lesend geprüft werden. `--apply` importiert sie als neue Geschichte; identische vorhandene redaktionelle Kennungen werden erkannt. Das setzt eine im Studio freigegebene Quelle voraus.

Private Vorher-Sicherungen und Fassungen vor den Endkorrekturen liegen unter `/home/jee/docker-data/comic-automation/bildregie-redaktion/20261028-erweiterung-300/`. Der [Fortschrittsbericht](../../../docs/Comic_Auswahl_300_Fortschritt.md) verlinkt alle importierten Skripte.

## Alle 100 Geschichten

| Nr. | Geschichte | Kacheln | Lesefassung | Definition | Originalquelle |
|---:|---|---:|---|---|---|
| 1 | Roß Bayard – Der Preis des Gehorsams | 18 | [Text](bayard-reinhold-18.txt) | [JSON](bayard-reinhold-18.json) | [Roß Bayard und Schloß Bayard](https://textgridrep.org/browse/kgq5.0) |
| 2 | Die Toten in Löwen – Zwei Beziehungen | 16 | [Text](tote-loewen-16.txt) | [JSON](tote-loewen-16.json) | [Die Toten in Löwen](https://textgridrep.org/browse/kdkp.0) |
| 3 | Der Schwanritter – Die Frage nach der Herkunft | 18 | [Text](schwanritter-helias-18.txt) | [JSON](schwanritter-helias-18.json) | [Der Schwanritter](https://textgridrep.org/browse/khsd.0) |
| 4 | Gelre, Gelre! – Der Ruf bleibt | 10 | [Text](gelre-drache-10.txt) | [JSON](gelre-drache-10.json) | [Gelre, Gelre!](https://textgridrep.org/browse/kj3k.0) |
| 5 | Des Riesen Handwerfen – Die neue Grenze | 14 | [Text](riesen-handwerfen-14.txt) | [JSON](riesen-handwerfen-14.json) | [Des Riesen Handwerfen](https://textgridrep.org/browse/kjdq.0) |
| 6 | Herr Lem – Die zurückgeholte Herde | 10 | [Text](herr-lem-walberech-10.txt) | [JSON](herr-lem-walberech-10.json) | [Herr Lem](https://textgridrep.org/browse/kg5z.0) |
| 7 | Gangolfs Brunnen – Verkauftes Wasser | 10 | [Text](gangolf-brunnen-10.txt) | [JSON](gangolf-brunnen-10.json) | [Gangolfs Brunnen](https://textgridrep.org/browse/kj2t.0) |
| 8 | Die Isabellenfarbe – Was eine Mode kostet | 12 | [Text](isabellenfarbe-12.txt) | [JSON](isabellenfarbe-12.json) | [Die Isabellenfarbe](https://textgridrep.org/browse/kdxd.0) |
| 9 | Faust und Jost – Die ausgeschlagene Freiheit | 16 | [Text](faust-jost-16.txt) | [JSON](faust-jost-16.json) | [Doktor Faust und sein Teufel Jost](https://textgridrep.org/browse/kgm8.0) |
| 10 | Vom Zauberer Agrippa – Der gerettete Schein | 14 | [Text](agrippa-schueler-14.txt) | [JSON](agrippa-schueler-14.json) | [Vom Zauberer Agrippa](https://textgridrep.org/browse/khkg.0) |
| 11 | Jan von Nivelle – Die freie Wahl | 12 | [Text](jan-nivelle-hund-12.txt) | [JSON](jan-nivelle-hund-12.json) | [Der Hund des Jan von Nivelle](https://textgridrep.org/browse/kgfw.0) |
| 12 | St. Johannisäpfel – Der grünende Stab | 8 | [Text](johannisaepfel-8.txt) | [JSON](johannisaepfel-8.json) | [St. Johannisäpfel](https://textgridrep.org/browse/kddt.0) |
| 13 | So viel Kinder als Tage im Jahre – Die verweigerte Gabe | 12 | [Text](losduinen-taufbecken-12.txt) | [JSON](losduinen-taufbecken-12.json) | [So viel Kinder als Tage im Jahre](https://textgridrep.org/browse/kf3s.0) |
| 14 | Der ewige Jäger – Der versäumte Abschied | 8 | [Text](ewiger-jaeger-wynendael-8.txt) | [JSON](ewiger-jaeger-wynendael-8.json) | [Der ewige Jäger](https://textgridrep.org/browse/kdjb.0) |
| 15 | Kludde – Der Schlüssel unter der Platte | 12 | [Text](kludde-schluessel-12.txt) | [JSON](kludde-schluessel-12.json) | [Tückebold Kludde](https://textgridrep.org/browse/kg58.0) |
| 16 | Lodder und Wapper – Das grausame Lachen | 16 | [Text](lodder-wapper-16.txt) | [JSON](lodder-wapper-16.json) | [Die Tückebolde Lodder und lange Wapper](https://textgridrep.org/browse/kdw4.0) |
| 17 | Osschaert – Der trockene Graben | 12 | [Text](osschaert-trockener-weg-12.txt) | [JSON](osschaert-trockener-weg-12.json) | [Der Geist Osschaert](https://textgridrep.org/browse/khgt.0) |
| 18 | Die Mahr – Der hilfreiche Rivale | 10 | [Text](mahr-verrat-10.txt) | [JSON](mahr-verrat-10.json) | [Die Mahr](https://textgridrep.org/browse/kf0x.0) |
| 19 | Das Rotmützchen – Der verspielte Beistand | 12 | [Text](rotmuetzchen-verloren-12.txt) | [JSON](rotmuetzchen-verloren-12.json) | [Die Klabautermännchen](https://textgridrep.org/browse/kfmd.0) |
| 20 | Flerus – Milch und Lauch | 8 | [Text](flerus-milch-8.txt) | [JSON](flerus-milch-8.json) | [Nix Flerus](https://textgridrep.org/browse/kgv8.0) |
| 21 | Die Meerminnen – Der einsame Turm | 12 | [Text](meerminnen-turm-12.txt) | [JSON](meerminnen-turm-12.json) | [Die Meerminnen](https://textgridrep.org/browse/kgng.0) |
| 22 | Bernlef – Die Stimmen im Hügel | 6 | [Text](bernlef-erinnerung-6.txt) | [JSON](bernlef-erinnerung-6.json) | [Geister in Friesland](https://textgridrep.org/browse/kggk.0) |
| 23 | Stavorens Ursprung – Drei Wege | 10 | [Text](stavoren-brueder-10.txt) | [JSON](stavoren-brueder-10.json) | [Stavorens Ursprung](https://textgridrep.org/browse/kdfc.0) |
| 24 | Der Feuerpütz – Die andere Gefahr | 12 | [Text](feuerpuetz-kalter-stoff-12.txt) | [JSON](feuerpuetz-kalter-stoff-12.json) | [Der Feuerpütz](https://textgridrep.org/browse/kdf8.0) |
| 25 | Der Wasserpütz – Der Preis der schnellen Rettung | 8 | [Text](wasserpuetz-preis-8.txt) | [JSON](wasserpuetz-preis-8.json) | [Der überquellende Wasserpütz](https://textgridrep.org/browse/kgdn.0) |
| 26 | Der Frauensand – Das Köstlichste | 12 | [Text](frauensand-weizen-12.txt) | [JSON](frauensand-weizen-12.json) | [Das Wunderkorn von Stavoren und der Frauensand](https://textgridrep.org/browse/kj0s.0) |
| 27 | Stavorens Untergang – Der wiederkehrende Ring | 16 | [Text](stavoren-ring-16.txt) | [JSON](stavoren-ring-16.json) | [Stavorens Untergang](https://textgridrep.org/browse/kgb0.0) |
| 28 | Die sieben Meerminnen – Der lebenslange Schwur | 14 | [Text](sieben-meerminnen-14.txt) | [JSON](sieben-meerminnen-14.json) | [Die sieben Meerminnen](https://textgridrep.org/browse/kd83.0) |
| 29 | Radbot – Der Fuß im Taufbecken | 18 | [Text](radbot-vorfahren-18.txt) | [JSON](radbot-vorfahren-18.json) | [Der Friesen Bekehrung](https://textgridrep.org/browse/kdgj.0) |
| 30 | Wittekinds Taufe – Der andere Blick | 10 | [Text](wittekind-ostern-10.txt) | [JSON](wittekind-ostern-10.json) | [Wittekinds Taufe](https://textgridrep.org/browse/kgj0.0) |
| 31 | Das Oldenburger Horn – Der ungeprüfte Trank | 12 | [Text](oldenburger-horn-12.txt) | [JSON](oldenburger-horn-12.json) | [Das Oldenburger Horn](https://textgridrep.org/browse/kfd4.0) |
| 32 | Friedrich – Der Strohmann vor dem Löwen | 12 | [Text](friedrich-loewensieger-12.txt) | [JSON](friedrich-loewensieger-12.json) | [Friedrich der Löwensieger](https://textgridrep.org/browse/kfzd.0) |
| 33 | Das Zwergvolk – Der vergessene Krug | 10 | [Text](osenberg-krug-10.txt) | [JSON](osenberg-krug-10.json) | [Das Zwergvolk im Osenberge](https://textgridrep.org/browse/kj29.0) |
| 34 | Die Elben – Die Größe des Kleinen | 6 | [Text](elben-eierschale-6.txt) | [JSON](elben-eierschale-6.json) | [Die Elben](https://textgridrep.org/browse/kgw6.0) |
| 35 | Das heilige Land – Der weggefegte Segen | 10 | [Text](helgoland-heringe-10.txt) | [JSON](helgoland-heringe-10.json) | [Das heilige Land](https://textgridrep.org/browse/kf76.0) |
| 36 | Fositesland – Der bleibende Brunnen | 12 | [Text](fositesland-brunnen-12.txt) | [JSON](fositesland-brunnen-12.json) | [Fositesland](https://textgridrep.org/browse/kfds.0) |
| 37 | Helgoland – Die steinernen Zeugen | 14 | [Text](helgoland-steinerne-zeugen-14.txt) | [JSON](helgoland-steinerne-zeugen-14.json) | [Der Jungfernstuhl und der Mönch auf Helgoland](https://textgridrep.org/browse/kgnv.0) |
| 38 | Mannigfual – Seife für ein Riesenschiff | 12 | [Text](mannigfual-seife-12.txt) | [JSON](mannigfual-seife-12.json) | [Mannigfual](https://textgridrep.org/browse/kdhr.0) |
| 39 | Der Geldsot – Die letzte Antwort | 14 | [Text](geldsot-stoerung-14.txt) | [JSON](geldsot-stoerung-14.json) | [Der Geldsot](https://textgridrep.org/browse/kj26.0) |
| 40 | Röwerlöwe – Die lange Feindschaft | 10 | [Text](roewerloewe-freiheit-10.txt) | [JSON](roewerloewe-freiheit-10.json) | [Röwerlöwe](https://textgridrep.org/browse/kddr.0) |
| 41 | König Dan – Die vertagte Wiederkehr | 10 | [Text](koenig-dan-warten-10.txt) | [JSON](koenig-dan-warten-10.json) | [König Dan](https://textgridrep.org/browse/kf42.0) |
| 42 | Der Tausendteufelsdamm – Das unterschätzte Land | 18 | [Text](tausendteufelsdamm-18.txt) | [JSON](tausendteufelsdamm-18.json) | [Die Schlacht auf dem Tausendteufelsdamme](https://textgridrep.org/browse/kfxt.0) |
| 43 | Die Wunderbäume – Hilfe trotz altem Unrecht | 12 | [Text](wunderbaeume-freiheit-12.txt) | [JSON](wunderbaeume-freiheit-12.json) | [Wunderbäume in Dithmarschen und Holstein](https://textgridrep.org/browse/kffh.0) |
| 44 | Der Freischütz von Marne – Der teure Ausweg | 16 | [Text](freischuetz-marne-16.txt) | [JSON](freischuetz-marne-16.json) | [Der wilde Jäger in Dithmarschen](https://textgridrep.org/browse/khv2.0) |
| 45 | König Abels Jagd – Der zehnte Hund | 10 | [Text](abel-neunter-hund-10.txt) | [JSON](abel-neunter-hund-10.json) | [König Abels Jagd](https://textgridrep.org/browse/kgxd.0) |
| 46 | Der Wode – Die unbedachte Auskunft | 12 | [Text](wode-verrat-12.txt) | [JSON](wode-verrat-12.json) | [Der Wode](https://textgridrep.org/browse/khq8.0) |
| 47 | Die Unterirdischen – Das unversehrte Haus | 8 | [Text](amrum-hausbrand-8.txt) | [JSON](amrum-hausbrand-8.json) | [Die Unterirdischen](https://textgridrep.org/browse/kfns.0) |
| 48 | Die Kielkröpfe – Die Gegenrede der Mutter | 10 | [Text](jaegerup-gegenrede-10.txt) | [JSON](jaegerup-gegenrede-10.json) | [Die Kielkröpfe](https://textgridrep.org/browse/kf1z.0) |
| 49 | Die Nissen – Zwei treue Diebe | 10 | [Text](nissen-heuverlust-10.txt) | [JSON](nissen-heuverlust-10.json) | [Die Nissen und die Wolterkens](https://textgridrep.org/browse/kg13.0) |
| 50 | Allerünken – Die volle Küche | 10 | [Text](alleruenken-haendewaschen-10.txt) | [JSON](alleruenken-haendewaschen-10.json) | [Allerünken](https://textgridrep.org/browse/kgf4.0) |
| 51 | Das Glück der Rantzau – Der Preis des Beweises | 16 | [Text](rantzau-hering-16.txt) | [JSON](rantzau-hering-16.json) | [Das Glück der Rantzau](https://textgridrep.org/browse/kfhp.0) |
| 52 | Schwertmann – Die verschlossene Kiepe | 14 | [Text](schwertmann-kiepe-14.txt) | [JSON](schwertmann-kiepe-14.json) | [Schwertmann](https://textgridrep.org/browse/kdp2.0) |
| 53 | Die schwarze Gret – Der beste Fisch | 12 | [Text](gret-fischer-12.txt) | [JSON](gret-fischer-12.json) | [Die schwarze Gret und das Danewerk](https://textgridrep.org/browse/kgdw.0) |
| 54 | Prinzessin Thüra – Die erfundenen Unholde | 10 | [Text](thuera-ausrede-10.txt) | [JSON](thuera-ausrede-10.json) | [Prinzessin Thüra](https://textgridrep.org/browse/khfq.0) |
| 55 | Die Sassen und die Jüten – Noch nicht vorbei | 16 | [Text](sassen-kropper-busch-16.txt) | [JSON](sassen-kropper-busch-16.json) | [Die Sassen und die Jüten](https://textgridrep.org/browse/kj3p.0) |
| 56 | Totenkopf wandert – Die nicht endende Verfolgung | 14 | [Text](adelbrand-antolille-14.txt) | [JSON](adelbrand-antolille-14.json) | [Totenkopf wandert](https://textgridrep.org/browse/kf3p.0) |
| 57 | Die schwarze Schule – Bis das Band sitzt | 10 | [Text](ziegler-strumpfband-10.txt) | [JSON](ziegler-strumpfband-10.json) | [Die schwarze Schule](https://textgridrep.org/browse/kh1r.0) |
| 58 | Die Gabler – Milch und Menschen | 12 | [Text](gabler-katze-12.txt) | [JSON](gabler-katze-12.json) | [Spottnamen und Schildbürger im Norden](https://textgridrep.org/browse/kfs3.0) |
| 59 | Rungholt – Hinter dem sicheren Deich | 12 | [Text](rungholt-deich-12.txt) | [JSON](rungholt-deich-12.json) | [Die Rungholder auf Nordstrand](https://textgridrep.org/browse/kdt0.0) |
| 60 | Treuer Herr, treuer Knecht – Die Probe vor der Nachricht | 12 | [Text](geert-burchard-12.txt) | [JSON](geert-burchard-12.json) | [Treuer Herr, treuer Knecht](https://textgridrep.org/browse/khnd.0) |
| 61 | Der Dom zu Schleswig – Der bleibende Schatten | 8 | [Text](schleswig-schwertschatten-8.txt) | [JSON](schleswig-schwertschatten-8.json) | [Der Dom zu Schleswig](https://textgridrep.org/browse/kgsk.0) |
| 62 | Die nächtliche Trauung – Das offene Grab | 14 | [Text](naechtliche-trauung-14.txt) | [JSON](naechtliche-trauung-14.json) | [Die nächtliche Trauung](https://textgridrep.org/browse/kfg3.0) |
| 63 | Der schnelle Reiter Tod – Beim dritten Fragen | 12 | [Text](schneller-reiter-tod-12.txt) | [JSON](schneller-reiter-tod-12.json) | [Der schnelle Reiter Tod](https://textgridrep.org/browse/kfzn.0) |
| 64 | Der Zauberer von Plön – Das verschobene Wort | 14 | [Text](ploen-drohung-14.txt) | [JSON](ploen-drohung-14.json) | [Der Zauberer von Plön](https://textgridrep.org/browse/kfq6.0) |
| 65 | Die Seeräuber – Der Schatz im Holz | 12 | [Text](stoertebeker-masten-12.txt) | [JSON](stoertebeker-masten-12.json) | [Die Seeräuber](https://textgridrep.org/browse/kh3k.0) |
| 66 | Die Krempner Glocke – Der Klang des Verlusts | 14 | [Text](krempner-glocke-14.txt) | [JSON](krempner-glocke-14.json) | [Die Krempner Glocke](https://textgridrep.org/browse/kf6q.0) |
| 67 | Die Enten – Der verräterische Ausruf | 14 | [Text](enten-zeugen-14.txt) | [JSON](enten-zeugen-14.json) | [Enten zeigen den Mord an](https://textgridrep.org/browse/kj04.0) |
| 68 | Die Schwesterntürme – Zwei Spitzen | 6 | [Text](altenbruch-schwestern-6.txt) | [JSON](altenbruch-schwestern-6.json) | [Die Schwesterntürme](https://textgridrep.org/browse/kg31.0) |
| 69 | Die Hand aus dem Grabe – Die bleibende Grenze | 12 | [Text](hand-aus-grab-12.txt) | [JSON](hand-aus-grab-12.json) | [Die Hand aus dem Grabe](https://textgridrep.org/browse/kdpj.0) |
| 70 | Bischof Blücher – Die leere Kornkammer | 8 | [Text](bluecher-korn-8.txt) | [JSON](bluecher-korn-8.json) | [Bischof Blücher](https://textgridrep.org/browse/kg7r.0) |
| 71 | Der Gast des Toten – Die verlorene Stunde | 16 | [Text](gast-toten-jahrhundert-16.txt) | [JSON](gast-toten-jahrhundert-16.json) | [Der Gast des Toten](https://textgridrep.org/browse/khxs.0) |
| 72 | Eulenspiegels Grab – Noch einmal verkehrt | 6 | [Text](eulenspiegel-grab-6.txt) | [JSON](eulenspiegel-grab-6.json) | [Till Eulenspiegels Grab](https://textgridrep.org/browse/kgtc.0) |
| 73 | Dort tanzt Bornholm hin – Die teure Ehre | 8 | [Text](bornholm-tanz-8.txt) | [JSON](bornholm-tanz-8.json) | [Dort tanzt Bornholm hin](https://textgridrep.org/browse/kg0f.0) |
| 74 | Die drei Meister – Der Applaus | 12 | [Text](drei-meister-auswahl-12.txt) | [JSON](drei-meister-auswahl-12.json) | [Die drei Meister](https://textgridrep.org/browse/khrw.0) |
| 75 | Rabundus’ Rose – Die verschobene Warnung | 14 | [Text](rabundus-rose-14.txt) | [JSON](rabundus-rose-14.json) | [Rabundus Rose](https://textgridrep.org/browse/khs0.0) |
| 76 | Der Wald kommt – Die Fahne der Frauen | 14 | [Text](luebeck-wald-14.txt) | [JSON](luebeck-wald-14.json) | [Der Wald kommt](https://textgridrep.org/browse/kgxm.0) |
| 77 | Der Herthasee – Hinter dem Friedensfest | 10 | [Text](herthasee-friedensfest-10.txt) | [JSON](herthasee-friedensfest-10.json) | [Der Herthasee](https://textgridrep.org/browse/kh31.0) |
| 78 | Pape Döne – Die letzte Ausflucht | 16 | [Text](pape-doene-beichte-16.txt) | [JSON](pape-doene-beichte-16.json) | [Pape Dönes Glockenspiel](https://textgridrep.org/browse/kj36.0) |
| 79 | Die Ururalte – Der vergessene Teil des Wunsches | 10 | [Text](ururalte-wunsch-10.txt) | [JSON](ururalte-wunsch-10.json) | [Die Ururalte](https://textgridrep.org/browse/kgsq.0) |
| 80 | Altmecklenburg – Der ausgelöste Herzog | 10 | [Text](mecklenburg-frauen-10.txt) | [JSON](mecklenburg-frauen-10.json) | [Altmecklenburg](https://textgridrep.org/browse/kgk0.0) |
| 81 | Der Fürstin Traum – Das sichtbare Versprechen | 12 | [Text](anastasia-panier-12.txt) | [JSON](anastasia-panier-12.json) | [Der Fürstin Traum](https://textgridrep.org/browse/khw5.0) |
| 82 | Das Teufelsgitter – Das falsche Schuldbuch | 8 | [Text](wismar-schuldbuch-8.txt) | [JSON](wismar-schuldbuch-8.json) | [Das Teufelsgitter](https://textgridrep.org/browse/kh8v.0) |
| 83 | Der englische Schweiß – Die verbotene Frage | 12 | [Text](varus-testament-12.txt) | [JSON](varus-testament-12.json) | [Der englische Schweiß](https://textgridrep.org/browse/kj9d.0) |
| 84 | Die Wassermuhme – Die Stunde im Dorf | 10 | [Text](wassermuhme-stunde-10.txt) | [JSON](wassermuhme-stunde-10.json) | [Die Wassermuhme](https://textgridrep.org/browse/khg9.0) |
| 85 | Der Gast des Pfingsttänzers – Der ungebetene Begleiter | 12 | [Text](pfingsttaenzer-gast-12.txt) | [JSON](pfingsttaenzer-gast-12.json) | [Der Gast des Pfingsttänzers](https://textgridrep.org/browse/khc8.0) |
| 86 | Der Gast des Kornwucherers – Drei verlorene Ernten | 18 | [Text](kornwucherer-gast-18.txt) | [JSON](kornwucherer-gast-18.json) | [Der Gast des Kornwucherers](https://textgridrep.org/browse/kj8x.0) |
| 87 | Der heilige Damm – Die dunkle Gestalt im Meer | 10 | [Text](heiliger-damm-10.txt) | [JSON](heiliger-damm-10.json) | [Der heilige Damm](https://textgridrep.org/browse/kg1q.0) |
| 88 | Die Sieben in Rostock – Die kleine Gegenrechnung | 6 | [Text](rostock-sieben-6.txt) | [JSON](rostock-sieben-6.json) | [Die Sieben in Rostock](https://textgridrep.org/browse/khcs.0) |
| 89 | Sankt Nikolaus – Das verlorene Rennen | 12 | [Text](nikolaus-rennen-12.txt) | [JSON](nikolaus-rennen-12.json) | [Sankt Nikolaus in Greifswald](https://textgridrep.org/browse/khq2.0) |
| 90 | Vineta – Die zweite Stadt am Himmel | 12 | [Text](vineta-doppelbild-12.txt) | [JSON](vineta-doppelbild-12.json) | [Vineta](https://textgridrep.org/browse/kh03.0) |
| 91 | Weh über Pommerland – Der Sieg ist nicht der Frieden | 10 | [Text](pommerland-warnvoegel-10.txt) | [JSON](pommerland-warnvoegel-10.json) | [Weh über Pommerland!](https://textgridrep.org/browse/kfh9.0) |
| 92 | Julin – Der dritte Freikauf | 16 | [Text](julin-loesegeld-16.txt) | [JSON](julin-loesegeld-16.json) | [Julin](https://textgridrep.org/browse/khhh.0) |
| 93 | Widewuto und Bruteno – Der angenommene Name | 14 | [Text](widewuto-bruteno-name-14.txt) | [JSON](widewuto-bruteno-name-14.json) | [Die Könige Widewuto und Bruteno](https://textgridrep.org/browse/khgj.0) |
| 94 | Romove – Was vom Heiligtum bleibt | 10 | [Text](romove-eiche-10.txt) | [JSON](romove-eiche-10.json) | [Romove](https://textgridrep.org/browse/kfp9.0) |
| 95 | Widewuto – Der letzte Dienst | 8 | [Text](widewuto-selbstopfer-8.txt) | [JSON](widewuto-selbstopfer-8.json) | [König Widewuto opfert sich selbst](https://textgridrep.org/browse/kgx3.0) |
| 96 | Sankt Adalbert – Die zwei Pfennige | 12 | [Text](adalbert-zwei-pfennige-12.txt) | [JSON](adalbert-zwei-pfennige-12.json) | [Sankt Adalbert](https://textgridrep.org/browse/kgdr.0) |
| 97 | Heiligenbeil – Das gewechselte Zeichen | 12 | [Text](heiligenbeil-eiche-12.txt) | [JSON](heiligenbeil-eiche-12.json) | [Heiligenbeil](https://textgridrep.org/browse/kgrh.0) |
| 98 | Das Bernsteinrecht – Der verspätete Ruf | 12 | [Text](bernsteinrecht-strand-12.txt) | [JSON](bernsteinrecht-strand-12.json) | [Das Bernsteinrecht](https://textgridrep.org/browse/kd9j.0) |
| 99 | Die Nixe von Nidden – Der weichende Strand | 10 | [Text](nidden-schwimmende-insel-10.txt) | [JSON](nidden-schwimmende-insel-10.json) | [Die Nixe von Nidden](https://textgridrep.org/browse/kgk9.0) |
| 100 | Der Glomssack zu Memel – Der letzte Käse | 12 | [Text](memel-letzter-kaese-12.txt) | [JSON](memel-letzter-kaese-12.json) | [Der Glomssack zu Memel](https://textgridrep.org/browse/kdnz.0) |
