# Weitere 100 Sagen, Mythen und Legenden

**100 neue Skripte fertig und importiert. Aktuelle Auswahl: 200 Geschichten.** Die separate Schneiderlein-Referenz bleibt außerhalb dieser Auswahl.

Die vollständigen historischen Quellen und die bereits redaktionell geprüften Sinnanalysen bilden die Grundlage. Alle Szenen, Erzählertexte und Dialoge dieser Erweiterung wurden von Codex selbst verfasst. Kein lokales oder separates Modell wurde als Ersatzautor eingesetzt.

## Ablauf und Gestaltung

Die empfohlene Kachelzahl wurde jeweils übernommen. Jede dritte Kachel enthält Erzählertext, zusätzliche Erzählertexte schließen Übergänge und stille Szenen. Gesprochener Dialog und Erzähler stehen nicht in derselben Kachel. Figuren, Verwandlungen, Kleidung, Waffen und Gegenstände werden je Kachel geführt; ein Bild beschreibt einen Zeitpunkt.

Der Bildstil bleibt offen und wird in Schritt 2 gewählt. Es wurden **keine Bilder erzeugt** und keine bestehenden Geschichten oder Workflows überschrieben. Neue Figuren haben eigene stabile Kennungen und noch keine Referenzbilder. Die später erzeugten Bilder müssen weiterhin angesehen werden.

Die alten Sagen werden als Überlieferung erzählt. Unterschiedliche Fassungen bleiben unterscheidbar. Historische Gruppenabwertungen werden nicht als heutige Tatsachen übernommen.

## Prüfung

100 zusätzliche Geschichten mit **1.146 Kacheln**, ohne Beschriftungswarnungen oder ungelöste Textfelder. Alle Szenen und Figuren wurden nach dem Import aus der Studio-API zurückgelesen und mit den lokalen Definitionen verglichen. Die ursprünglichen 100 Auswahlkennungen sind erhalten, die 100 neuen Kennungen überschneiden sich nicht mit ihnen. Im Browser sind 200 Geschichten in Schritt 1, 200 Skripte in Schritt 2 und 200 Quellen geprüft.

Der automatische Skript-Cron bleibt pausiert. Die übrigen Quellen bleiben zurückgestellt.

## Dateien

- `Auftrag.json`: die eingefrorenen 100 zusätzlichen Quellen mit Text-Hash und empfohlenem Umfang.
- `Redaktion.json`: die selbst verfassten Szenen, Texte, Figuren und Zustandswechsel.
- `Pruefbericht.json`: technische Beschriftungsprüfung je Geschichte.
- `Importiert.json`: Kennungen der neu angelegten Studio-Geschichten.
- `Abschlusspruefung.json`: Gesamtvergleich mit dem laufenden Studio.

Die lokalen Artefakte können ohne Modellaufrufe neu gebaut und geprüft werden. Dieser Befehl erzeugt keine Bilder und ändert das Studio nicht:

```bash
python3 scripts/build_comic_selection_extension.py --folder examples/comics/erweiterung-200 --namespace comic-auswahl-200
```

Einzelne Definitionen lassen sich mit `scripts/import_comic_script.py DATEI --apply` importieren. Identische bereits vorhandene Skriptkennungen werden erkannt. Der Befehl setzt eine bereits freigegebene Quelle voraus und überschreibt keine existierende Geschichte.

Private Sicherungen des vorherigen Auswahl- und Auftragsstands sowie der Endprüfung liegen unter `/home/jee/docker-data/comic-automation/bildregie-redaktion/20261028-erweiterung-200/`.

## Alle 100 Geschichten

| Nr. | Geschichte | Kacheln | Lesefassung | Studio-Definition |
|---:|---|---:|---|---|
| 1 | Der Zähringer Ursprung – Silber aus dem Meiler | 10 | [Text](zaehringer-ursprung-10.txt) | [JSON](zaehringer-ursprung-10.json) |
| 2 | Das Riesenspielzeug – Kein Ding zum Spielen | 8 | [Text](riesenspielzeug-8.txt) | [JSON](riesenspielzeug-8.json) |
| 3 | Der Krötenstuhl – Der abgebrochene Versuch | 10 | [Text](kroetenstuhl-10.txt) | [JSON](kroetenstuhl-10.json) |
| 4 | Der Mühlenbär – Die Spur am Morgen | 10 | [Text](muehlenbaer-10.txt) | [JSON](muehlenbaer-10.json) |
| 5 | Chorkönig – Der erste Befehl | 10 | [Text](chorkoenig-10.txt) | [JSON](chorkoenig-10.json) |
| 6 | Sankt Ottilia – Ihr eigener Weg | 18 | [Text](ottilia-eigener-weg-18.txt) | [JSON](ottilia-eigener-weg-18.json) |
| 7 | Vater und Sohn – Das bewahrte Leben | 14 | [Text](vater-sohn-bruno-14.txt) | [JSON](vater-sohn-bruno-14.json) |
| 8 | Die Münsteruhr – Besitz ohne Können | 12 | [Text](muensteruhr-meister-12.txt) | [JSON](muensteruhr-meister-12.json) |
| 9 | Zürcher Brei – Ein Tag auf dem Wasser | 12 | [Text](zuercher-brei-12.txt) | [JSON](zuercher-brei-12.json) |
| 10 | Das Hündchen von Bretten – Treue ohne Dank | 10 | [Text](huendchen-bretten-10.txt) | [JSON](huendchen-bretten-10.json) |
| 11 | Trifels – Die Antwort hinter der Mauer | 12 | [Text](trifels-blondel-12.txt) | [JSON](trifels-blondel-12.json) |
| 12 | Der Rotbart zu Kaiserslautern – Warten im Berg | 10 | [Text](rotbart-kaiserslautern-10.txt) | [JSON](rotbart-kaiserslautern-10.json) |
| 13 | Die schiffenden Mönche – Der verratene Dienst | 10 | [Text](schiffende-moenche-10.txt) | [JSON](schiffende-moenche-10.json) |
| 14 | Die Schwabenschüssel – Vor dem Fest das Versprechen | 10 | [Text](schwabenschuessel-rechte-10.txt) | [JSON](schwabenschuessel-rechte-10.json) |
| 15 | Die Totenglocken zu Speyer – Wer bei den Verstoßenen bleibt | 14 | [Text](totenglocken-speyer-14.txt) | [JSON](totenglocken-speyer-14.json) |
| 16 | Wormser Wahrzeichen – Stein und Deutung | 6 | [Text](wormser-wahrzeichen-6.txt) | [JSON](wormser-wahrzeichen-6.json) |
| 17 | Die Königstochter vom Rhein – Zwei Spuren | 14 | [Text](koenigstochter-rhein-14.txt) | [JSON](koenigstochter-rhein-14.json) |
| 18 | Die Schwedensäule – Das verweigerte Geschenk | 10 | [Text](schwedensaeule-schwert-10.txt) | [JSON](schwedensaeule-schwert-10.json) |
| 19 | Siegenheim – Was auf dem Tisch fehlt | 10 | [Text](siegenheim-brot-10.txt) | [JSON](siegenheim-brot-10.json) |
| 20 | Jettenbühel – Die Grenze des Zukunftsblicks | 10 | [Text](jettenbuehel-10.txt) | [JSON](jettenbuehel-10.json) |
| 21 | St. Katharinens Handschuh – Die versäumte Erklärung | 16 | [Text](katharinen-handschuh-16.txt) | [JSON](katharinen-handschuh-16.json) |
| 22 | Des Rodensteiners Auszug – Krieg vor Liebe | 12 | [Text](rodensteiner-auszug-12.txt) | [JSON](rodensteiner-auszug-12.json) |
| 23 | Eginhart und Emma – Eine Spur im Schnee | 14 | [Text](eginhart-emma-schnee-14.txt) | [JSON](eginhart-emma-schnee-14.json) |
| 24 | Die Windecker – Der Preis einer Nuss | 10 | [Text](windecker-meise-10.txt) | [JSON](windecker-meise-10.json) |
| 25 | Thassilo in Lorsch – Die späte Erkenntnis | 12 | [Text](thassilo-lorsch-12.txt) | [JSON](thassilo-lorsch-12.json) |
| 26 | Der Heerwisch – Der gerufene Schrecken | 10 | [Text](heerwisch-10.txt) | [JSON](heerwisch-10.json) |
| 27 | Die Wiesenjungfrau – Kleine Gesten, große Hoffnung | 16 | [Text](wiesenjungfrau-niesen-16.txt) | [JSON](wiesenjungfrau-niesen-16.json) |
| 28 | Das versunkene Kloster – Der rote Faden | 14 | [Text](versunkenes-kloster-14.txt) | [JSON](versunkenes-kloster-14.json) |
| 29 | Der Lindwurm auf Frankenstein – Der Sieg am Brunnen | 12 | [Text](frankenstein-lindwurm-12.txt) | [JSON](frankenstein-lindwurm-12.json) |
| 30 | Das Frankensteiner Eselslehen – Der Preis der Demütigung | 10 | [Text](eselslehen-10.txt) | [JSON](eselslehen-10.json) |
| 31 | Das goldne Mainz – Was wirklich glänzt | 6 | [Text](goldne-mainz-6.txt) | [JSON](goldne-mainz-6.json) |
| 32 | Hatto, Heriger und Willigis – Drei Gesichter der Macht | 18 | [Text](hatto-heriger-willigis-18.txt) | [JSON](hatto-heriger-willigis-18.json) |
| 33 | Die Mainzer Kreuze – Was das Feuer nicht beendet | 12 | [Text](mainzer-kreuze-12.txt) | [JSON](mainzer-kreuze-12.json) |
| 34 | Heinrich Frauenlobs Begängnis – Der Wein danach | 12 | [Text](frauenlob-wein-12.txt) | [JSON](frauenlob-wein-12.json) |
| 35 | Die heilige Bilhilde – Das gelebte Leben | 16 | [Text](bilhilde-taufe-16.txt) | [JSON](bilhilde-taufe-16.json) |
| 36 | Der Franken Furt – Der Ausweg | 10 | [Text](franken-furt-10.txt) | [JSON](franken-furt-10.json) |
| 37 | Des Königs Weihnacht – Die fromme Maske | 14 | [Text](koenigs-weihnacht-14.txt) | [JSON](koenigs-weihnacht-14.json) |
| 38 | Vom Eschenheimer Turm – Neun Schüsse und ein Nein | 12 | [Text](eschenheimer-turm-12.txt) | [JSON](eschenheimer-turm-12.json) |
| 39 | Der Teufelsweg auf Falkenstein – Ein anderes Versprechen | 14 | [Text](teufelsweg-falkenstein-14.txt) | [JSON](teufelsweg-falkenstein-14.json) |
| 40 | Die Eppsteiner – Der Helfer bleibt zurück | 14 | [Text](eppsteiner-mannstein-14.txt) | [JSON](eppsteiner-mannstein-14.json) |
| 41 | Blutlinde – Was Herkunft zerstört | 16 | [Text](blutlinde-graroder-16.txt) | [JSON](blutlinde-graroder-16.json) |
| 42 | Räderberg – Noch einen Tag | 10 | [Text](raederberg-drei-tage-10.txt) | [JSON](raederberg-drei-tage-10.json) |
| 43 | Die Wisperstimme – Der Schatz im Turm | 12 | [Text](wisperstimme-12.txt) | [JSON](wisperstimme-12.json) |
| 44 | Die glühenden Kohlen – Wer den Wert geschaffen hat | 10 | [Text](gluehende-kohlen-10.txt) | [JSON](gluehende-kohlen-10.json) |
| 45 | Die Taube auf dem Pflug – Die überhörte Bitte | 12 | [Text](taube-pflug-12.txt) | [JSON](taube-pflug-12.json) |
| 46 | Der Affe zu Dhaun – Im Dickicht | 8 | [Text](affe-dhaun-8.txt) | [JSON](affe-dhaun-8.json) |
| 47 | Das Pfaffenkäppchen – Die fremde Rechnung | 14 | [Text](pfaffenkaeppchen-14.txt) | [JSON](pfaffenkaeppchen-14.json) |
| 48 | Der Stiefel voll Wein – Ein teurer Einsatz | 8 | [Text](stiefel-wein-8.txt) | [JSON](stiefel-wein-8.json) |
| 49 | Der wilde Jäger – Die letzte Grenze | 12 | [Text](wilder-jaeger-asyl-12.txt) | [JSON](wilder-jaeger-asyl-12.json) |
| 50 | Spanheims Gründung – Das verlorene Zeichen | 14 | [Text](spanheim-kaestchen-14.txt) | [JSON](spanheim-kaestchen-14.json) |
| 51 | Vom Ursprung des Moselweins – Mitgebrachte Reben | 6 | [Text](moselwein-ursprung-6.txt) | [JSON](moselwein-ursprung-6.json) |
| 52 | Der Heiligen Gräber – Eine Kapelle als Gedächtnis | 6 | [Text](heiligen-graeber-6.txt) | [JSON](heiligen-graeber-6.json) |
| 53 | Metz versagt den Tanz – Ein Brief als Falle | 14 | [Text](metz-list-14.txt) | [JSON](metz-list-14.json) |
| 54 | Der Teufelsbündner in Virdung – Das geerbte Gold | 14 | [Text](virdung-heckebeutel-14.txt) | [JSON](virdung-heckebeutel-14.json) |
| 55 | Die getreue Frau Florentina – Die unbekannte Befreierin | 18 | [Text](florentina-hemd-18.txt) | [JSON](florentina-hemd-18.json) |
| 56 | Triers Alter – Zeichen und Gewissheit | 8 | [Text](triers-alter-8.txt) | [JSON](triers-alter-8.json) |
| 57 | Sankt Arnulfs Ring – Das wiedergefundene Zeichen | 8 | [Text](arnulfs-ring-8.txt) | [JSON](arnulfs-ring-8.json) |
| 58 | Frevel wird bestraft – Zwei Warnungen | 10 | [Text](frevel-trier-10.txt) | [JSON](frevel-trier-10.json) |
| 59 | Die Märtyrergräber – Gegen das Verschwinden | 6 | [Text](martyrergraeber-trier-6.txt) | [JSON](martyrergraeber-trier-6.json) |
| 60 | Die heilige Genofeva – Nicht zurück ins Schloss | 18 | [Text](genofeva-wald-18.txt) | [JSON](genofeva-wald-18.json) |
| 61 | Die Weingötter am Rhein – Stein und Kufe | 10 | [Text](weingoetter-rhein-10.txt) | [JSON](weingoetter-rhein-10.json) |
| 62 | Die sieben Schwestern – Stein und Zustimmung | 10 | [Text](sieben-schwestern-10.txt) | [JSON](sieben-schwestern-10.json) |
| 63 | Lurlei – Was der Gesang verdeckt | 14 | [Text](lurlei-14.txt) | [JSON](lurlei-14.json) |
| 64 | Sankt Goars Wunder – Die unbequeme Probe | 12 | [Text](goars-wunder-12.txt) | [JSON](goars-wunder-12.json) |
| 65 | Die Brüder – Das umgedrehte Maß | 12 | [Text](brueder-blindes-erbe-12.txt) | [JSON](brueder-blindes-erbe-12.json) |
| 66 | Die wandelnde Nonne – Eine andere Gestalt | 14 | [Text](wandelnde-nonne-14.txt) | [JSON](wandelnde-nonne-14.json) |
| 67 | Die Frau von Stein – Der leere Platz | 8 | [Text](frau-von-stein-8.txt) | [JSON](frau-von-stein-8.json) |
| 68 | Der kühne Kurzbold – Ein anderer Maßstab | 14 | [Text](kurzbold-14.txt) | [JSON](kurzbold-14.json) |
| 69 | Die Luftbrücke – Ein Faden reicht zum Anfang | 12 | [Text](luftbruecke-faden-12.txt) | [JSON](luftbruecke-faden-12.json) |
| 70 | Die Gefangenen auf Altenahr – Das Geräusch im Loch | 10 | [Text](gefangene-altenahr-10.txt) | [JSON](gefangene-altenahr-10.json) |
| 71 | Vom Siebengebürg – Das nützliche Amt | 8 | [Text](siebengebirg-feuermann-8.txt) | [JSON](siebengebirg-feuermann-8.json) |
| 72 | Rolandseck – Einen Tag zu spät | 14 | [Text](rolandseck-nachricht-14.txt) | [JSON](rolandseck-nachricht-14.json) |
| 73 | Die Knappschaft im Lüderich – Der missachtete Boden | 12 | [Text](luederich-knappschaft-12.txt) | [JSON](luederich-knappschaft-12.json) |
| 74 | Die letzte Saat – Ein Vergleich für die Ewigkeit | 10 | [Text](letzte-saat-eicheln-10.txt) | [JSON](letzte-saat-eicheln-10.json) |
| 75 | Der Alte-Berg – Dienen statt herrschen | 14 | [Text](alte-berg-eberhard-14.txt) | [JSON](alte-berg-eberhard-14.json) |
| 76 | Der Klosteresel – Der gemeinsame Anfang | 8 | [Text](klosteresel-8.txt) | [JSON](klosteresel-8.json) |
| 77 | Der blühende Bischofstab – Das abgelegte Amt | 8 | [Text](bluehender-bischofstab-8.txt) | [JSON](bluehender-bischofstab-8.json) |
| 78 | Immenkapelle – Das kleine Wachsgebäude | 10 | [Text](immenkapelle-10.txt) | [JSON](immenkapelle-10.json) |
| 79 | Goldemar – Was man nicht sehen muss | 12 | [Text](goldemar-unsichtbar-12.txt) | [JSON](goldemar-unsichtbar-12.json) |
| 80 | Das heilige Köln – Gemeinsame Zeichen, eigener Wille | 8 | [Text](heiliges-koeln-8.txt) | [JSON](heiliges-koeln-8.json) |
| 81 | Der Bürger Marsilius – Der nützlichere Sieg | 14 | [Text](marsilius-rechte-14.txt) | [JSON](marsilius-rechte-14.json) |
| 82 | Die Kölner Dom-Sage – Der falsche Maßstab | 12 | [Text](koelner-dom-wette-12.txt) | [JSON](koelner-dom-wette-12.json) |
| 83 | Albertus Magnus – Ein Sommer im Winter | 10 | [Text](albertus-garten-10.txt) | [JSON](albertus-garten-10.json) |
| 84 | Herr Gryn und der Löwe – Die falsche Gastlichkeit | 12 | [Text](gryn-loewe-12.txt) | [JSON](gryn-loewe-12.json) |
| 85 | Die Pferde aus dem Bodenloch – Lasst sie herein | 14 | [Text](pferde-bodenloch-14.txt) | [JSON](pferde-bodenloch-14.json) |
| 86 | Umrittener Wald – Nicht für mich | 10 | [Text](umrittener-wald-10.txt) | [JSON](umrittener-wald-10.json) |
| 87 | Kaiser Karls Apfelschnitze – Zu spät geöffnet | 8 | [Text](karls-apfelschnitze-8.txt) | [JSON](karls-apfelschnitze-8.json) |
| 88 | Dom zu Aachen – Die erste Seele | 12 | [Text](aachener-dom-wolf-12.txt) | [JSON](aachener-dom-wolf-12.json) |
| 89 | Der Teufel im Ponellenturm – Wenn er kommt | 6 | [Text](ponellenturm-6.txt) | [JSON](ponellenturm-6.json) |
| 90 | Vom Loosberg über Aachen – Die alten Schuhe | 10 | [Text](loosberg-sand-10.txt) | [JSON](loosberg-sand-10.json) |
| 91 | Schlangenring – Wer darf Recht verlangen? | 10 | [Text](schlangenring-glocke-10.txt) | [JSON](schlangenring-glocke-10.json) |
| 92 | Kaiser Karl kehrt heim – Der unbesetzte Stuhl | 14 | [Text](karl-heimkehr-14.txt) | [JSON](karl-heimkehr-14.json) |
| 93 | Fastradas Liebeszauber – Wohin der Ring fällt | 12 | [Text](fastrada-ring-12.txt) | [JSON](fastrada-ring-12.json) |
| 94 | Karl des Großen Tod und Grab – Die gestörte Ruhe | 12 | [Text](karls-grab-12.txt) | [JSON](karls-grab-12.json) |
| 95 | Templerkirche zu Aachen – Was unter der Quelle klingt | 8 | [Text](templerkirche-aachen-8.txt) | [JSON](templerkirche-aachen-8.json) |
| 96 | Die Hinzlein zu Aachen – Wohin der Spuk zieht | 16 | [Text](hinzlein-aachen-16.txt) | [JSON](hinzlein-aachen-16.json) |
| 97 | Die Musikanten auf dem Pervisch – Der nachgemachte Lohn | 12 | [Text](musikanten-pervisch-12.txt) | [JSON](musikanten-pervisch-12.json) |
| 98 | Der fliegende Holländer – Die unbeendete Reise | 16 | [Text](fliegender-hollaender-falkenberg-16.txt) | [JSON](fliegender-hollaender-falkenberg-16.json) |
| 99 | Sankt Remaclus Fuß zu Spa – Das bleibende Zeichen | 8 | [Text](remaclus-fuss-8.txt) | [JSON](remaclus-fuss-8.json) |
| 100 | Die schlafenden Kinder – Die späte Hilfe | 12 | [Text](schlafende-kinder-12.txt) | [JSON](schlafende-kinder-12.json) |
