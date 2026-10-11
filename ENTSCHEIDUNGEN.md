# Konzeptheft – Entscheidungen

Hier steht, wo das Programm das Konzept ergänzt oder auslegt. Jeweils mit Grund.

## Liste und Textfeld nebeneinander

Die Liste steht links, das Textfeld rechts. Sehende sehen beides.
Grund: Antwort im Konzept unter „Offene Fragen“.

## Unterlisten (Wunsch vom 08.10.2026)

Pfeil rechts öffnet die Unterliste des markierten Abschnitts, Pfeil links geht zurück.
Die Liste zeigt immer nur eine Ebene. „Neuer Eintrag“ und „Speichern“ gibt es nur in der Hauptliste.
Eine leere Unterliste zeigt „Kein Eintrag, Alt+N für ersten Untereintrag“. Enter auf dieser Zeile tut dasselbe wie Alt+N.
Für jede Unterebene unter einem Abschnitt kommt ein .0 an seine Nummer (Wunsch vom 08.10.2026). Beispiel mit drei Unterebenen: In der Hauptliste steht 1.0.0.0, eine Ebene tiefer 1.1.0.0, dann 1.1.1.0, ganz unten 1.1.1.1. Es kommen nur so viele Nullen dazu, wie es Unterebenen schon gibt.
Bleibt eine Unterliste leer, verschwindet das .0 beim Zurückgehen wieder. Grund: Es gibt dann keine Unterliste.
Höchstens vier Unterebenen. Die tiefste Nummer sieht so aus: 3.1.2.1.4.
Die Liste zeigt und sagt nur Nummer und Name, zum Beispiel „3 Lösung“ oder „3.0 Lösung“. Kein „3 von 5“ mehr und kein Punkt nach einer einzelnen Zahl (Wunsch vom 08.10.2026, weicht vom Konzept ab). Sagt NVDA trotzdem „3 von 5“, kommt das von der NVDA-Einstellung „Objektpositionsangaben ausgeben“.
Entf löscht einen Abschnitt mit seiner ganzen Unterliste. Die Rückfrage nennt die Anzahl der Untereinträge.
Escape im Textfeld springt in die Ebene des Abschnitts zurück, auch wenn die Liste inzwischen eine andere Ebene zeigt.

## Projektdatei .konzept im Ordner Dateien

Gespeichert wird jetzt als .konzept. Die Datei enthält die ganze Struktur mit allen Unterlisten (JSON, lesbar).
Grund: Markdown kann Abschnitte und Überschriften im Text nicht sicher auseinanderhalten, sobald es Unterebenen gibt.
Speichern und Öffnen schlagen den Ordner „Dateien“ im Programmordner vor (neben main.py, später neben der Exe).
Alte .md-Dateien lassen sich weiter öffnen. Beim ersten Speichern fragt das Programm dann nach einem Namen für die .konzept-Datei.

## PDF und Text

Beim Speichern entstehen neben der .konzept-Datei eine .pdf und eine .txt mit gleichem Namen.
Die Abschnitte werden Überschriften: Hauptliste Ebene 1, erste Unterliste Ebene 2 und so weiter bis Ebene 5.
Überschriften im Text eines Abschnitts (Alt+1 bis Alt+3) liegen eine Ebene darunter, höchstens Ebene 6.
Der Titel steht groß über allem, ist aber keine Überschrift. Sonst wären die Abschnitte nicht Ebene 1.
In der .txt gibt es keine Überschriften. Dort zeigt die Nummer die Ebene: 3., 3.1, 3.1.2. Ohne .0.

## LaTeX-Export (Wunsch vom 08.10.2026)

Eigener Menüpunkt: Datei, Als LaTeX exportieren, Strg+E. Die .tex entsteht nicht bei jedem Speichern.
Grund: Nicht jeder braucht LaTeX, und der Ordner Dateien bleibt übersichtlich.
Klasse scrartcl (KOMA-Script), weil sie für deutsche Texte gut passt. Kopf mit utf8, ngerman, T1, lmodern, microtype, csquotes, geometry, booktabs, tabularx, longtable, enumitem, graphicx, xcolor, amsmath, amssymb, siunitx und hyperref.
Abschnitte: Hauptliste \section bis vierte Unterebene \subparagraph. LaTeX nummeriert selbst und kommt auf dieselben Nummern.
Überschriften im Text werden Befehle mit Stern, also ohne Nummer. Sonst würden sich die Nummern der Abschnitte verschieben.
Zeilen eines Absatzes werden mit \\ getrennt, damit die Zeilenumbrüche erhalten bleiben.
Geprüft: Eine Beispieldatei mit allen fünf Ebenen und Sonderzeichen läuft mit pdflatex (MiKTeX) ohne Fehler und Warnungen durch.

## Überschriften im Textfeld

Im Textfeld steht Ebene 1 als „# “, Ebene 2 als „## “, Ebene 3 als „### “. So steht es auch in der .konzept-Datei.
Grund: Im Textfeld ist „# “ kürzer zu lesen.

## Leere Zeilen im Textfeld

Rückmeldung vom 07.10.2026: Nach Enter zeigte die Braillezeile noch die alte Zeile, bis man einen Buchstaben tippte.
Ursache: Qt meldet NVDA für eine leere Zeile die Zeile davor (Qt-Quelltext, UI Automation, ExpandToEnclosingUnit).
Lösung: In jeder leeren Zeile steht intern ein geschütztes Leerzeichen. NVDA sagt dafür „leer“. Der Cursor bleibt davor. Pfeil rechts springt wie in Word gleich in die nächste Zeile. Entf in einer leeren Zeile entfernt die Zeile.
Beim Speichern und Kopieren werden diese Zeichen entfernt.
Folge: Ein geschütztes Leerzeichen ganz am Anfang oder Ende einer Zeile wird entfernt. Mitten im Text bleibt es erhalten.
Dasselbe Problem haben vermutlich CodeCockpit, Tagebuch und Chatbot. Die Lösung steckt in PlainEdit in konzeptheft\ui\common.py und lässt sich übernehmen.

## Titel

Der Titel steht in der .konzept-Datei. Ist er leer, wird beim ersten Speichern der Dateiname zum Titel. Ändern: Bearbeiten, Titel ändern.

## Weitere Ergänzungen

- Beim Start öffnet das Programm das zuletzt benutzte Konzept.
- Alt+N auf „Neuer Eintrag“ oder „Speichern“ legt den Abschnitt an Position 1 an.
- Neuer Eintrag und Alt+N öffnen das Textfeld nicht. Man bleibt in der Liste und drückt Enter.
- Automatisches Speichern ist still. Es steht nur in der Statuszeile.
- Löschen fragt mit OK und Abbrechen. Vorgabe und Escape ist Abbrechen.
- Beim Beenden mit Änderungen: Ja, Nein, Abbrechen. Vorgabe ist Ja, Escape ist Abbrechen.
- Schriftgröße: Strg+Plus, Strg+Minus, Strg+0. Sie bleibt gespeichert.
- Strg+Umschalt+M wiederholt die letzte Ansage, wie im CodeCockpit.
- Text vor dem ersten Abschnitt in einer fremden .md-Datei kommt in einen Abschnitt „Ohne Überschrift“.
- Bis es eine eigene .venv gibt, startet start.bat mit der Umgebung des CodeCockpits.
