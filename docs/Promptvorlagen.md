# Beschreibungen für MiniMax-H3-Tests

## 1. Stabilität einer Industrieszene

```text
Feste halbweite Kameraeinstellung im Kontrollraum einer modernen Luftzerlegungsanlage.
Zwei Ingenieure in üblicher Schutzkleidung prüfen eine Anzeige mit Prozessverläufen.
Die Kamera bleibt ruhig. Realistische Industrieatmosphäre, leises Lüftungsbrummen,
dezente Tastaturgeräusche, natürliche Hintergrundgeräusche ohne Sprache.
Keine Untertitel, Logos oder eingeblendeten Texte.
```

Damit lassen sich Personen, Bildschirme und industrielle Umgebungen bei ruhiger
Kamera prüfen. Der Verzicht auf Beschriftungen vermeidet Textartefakte. Auch die
Natürlichkeit der Umgebungsgeräusche lässt sich beurteilen.

## 2. Bewegung eines Geräts

```text
Nahaufnahme eines Edelstahl-Stellantriebs für ein kryogenes Ventil, das sich in
einer sauberen Industrieanlage langsam öffnet. Auf isolierten Rohrleitungen ist
Kondenswasser sichtbar. Die Kamera fährt langsam und kontrolliert.
Realistisches mechanisches Antriebsgeräusch und leise Anlagenlüftung.
Keine Menschen, Sprache, Texte oder Wasserzeichen.
```

Dabei die Kontinuität der mechanischen Bewegung, die Stabilität kleiner Bauteile
und die Synchronität zwischen Bewegung und Geräusch prüfen.

## 3. Wissenschaftliche Vorführung

```text
Auf einem sauberen Labortisch wird eine kleine Destillationskolonne vorgeführt.
Farbige Kontrollleuchten verändern sich allmählich, während eine forschende Person
einen Drehknopf verstellt. Feste Kamera, realistische Materialien, leise
Raumgeräusche und dezentes Gerätebrummen. Keine Dialoge, Untertitel oder Wasserzeichen.
```

## 4. Allgemeiner Aufbau

```text
[Kameratyp und Bildausschnitt] + [Umgebung] + [Motiv] + [Handlung]
+ [Kamerabewegung] + [Beleuchtung und Material] + [Umgebungsgeräusche]
+ [Einschränkungen]
```

Mögliche Einschränkungen:

```text
Keine Untertitel, eingeblendeten Texte, Wasserzeichen oder Logos.
Stabile Geometrie, realistische Bewegungen und zusammenhängender Ton.
```

## 5. Vorgehen beim Prüfen

- Zunächst nur eine wesentliche Handlung beschreiben.
- Komplexe Dialoge, schnelle Kamerafahrten und Interaktionen mehrerer Menschen nicht gleichzeitig verlangen.
- Für Vergleichsmessungen Beschreibung und Startwert (`seed`) beibehalten.
- Zuerst mit einer einfachen Beschreibung eine Ausgangsmessung erstellen.
- Erst nach einem stabilen Bild Dialoge und komplexere Tonkulissen testen.
