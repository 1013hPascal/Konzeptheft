# Konzeptheft – Konzept

## 1\. Zweck

Das Konzeptheft ist ein Schreibprogramm für Konzepte, Ideen und Verbesserungsvorschläge.
Ein Konzept besteht aus mehreren benannten Abschnitten. Man springt mit der Tastatur direkt zu einem Abschnitt, statt wie in Word lange zu scrollen.

Zielgruppe: blinde Nutzer mit Screenreader (NVDA), aber auch für Sehende normal benutzbar.

Technik: Python mit PySide6. Aufbau und Bedienelemente orientieren sich am CodeCockpit.

## 2\. Grundprinzip

* Es gibt eine Liste von Abschnitten. Jeder Abschnitt hat eine Nummer, einen Namen und einen Text.
* In der Liste bewegt man sich mit den Pfeiltasten.
* Enter öffnet den Text des Abschnitts in einem mehrzeiligen Textfeld.
* Escape schließt das Textfeld und springt zurück in die Liste, auf genau den Abschnitt, aus dem man kam.
* Die Nummern vergibt das Programm automatisch und zählt nach jedem Einfügen, Verschieben oder Löschen neu durch.

## 3\. Aufbau des Fensters

* Oben: Menüleiste mit Datei (Neu, Öffnen, Speichern, Speichern unter, Beenden) und Bearbeiten.
* Darunter: die Abschnittsliste.
* Die ersten beiden Einträge der Liste sind immer feste Befehle:

  1. „Neuer Eintrag“: legt einen neuen Abschnitt am Ende an.
  2. „Speichern“: speichert das Konzept.
* Danach folgen die Abschnitte, zum Beispiel „1. Einleitung“, „2. Problem“, „3. Lösung“.
* Das Textfeld des geöffneten Abschnitts steht neben oder unter der Liste. Sehende sehen beides gleichzeitig.

## 4\. Bedienung in der Liste

* Pfeil hoch und Pfeil runter: zum vorherigen und nächsten Eintrag.
* Pos1 und Ende: zum ersten und letzten Abschnitt.
* Enter auf einem Abschnitt: öffnet dessen Textfeld.
* Enter auf „Neuer Eintrag“: fragt nach dem Namen und legt den Abschnitt am Ende an.
* Enter auf „Speichern“: speichert.
* Alt+N: neuer Abschnitt direkt unter dem aktuellen. Das Programm fragt zuerst nach dem Namen. Steht man auf Nummer 4 von 5, wird der neue Abschnitt Nummer 5, und der bisherige fünfte wird Nummer 6.
* Alt+Pfeil hoch: verschiebt den aktuellen Abschnitt eine Position nach oben.
* Alt+Pfeil runter: verschiebt den aktuellen Abschnitt eine Position nach unten.
* Entf: löscht den Abschnitt nach der Rückfrage „Abschnitt ‚Name‘ löschen? OK / Abbrechen“.
* F2: umbenennen.
* Kontextmenü (Anwendungstaste oder Shift+F10): Umbenennen, Neuer Abschnitt darunter, Nach oben, Nach unten, Löschen.

Ansage beim Bewegen in der Liste, zum Beispiel: „4 von 5, Lösung“.
Nach dem Verschieben, zum Beispiel: „Lösung, jetzt an Position 3“.

## 5\. Bedienung im Textfeld

* Normales mehrzeiliges Textfeld ohne Zeilengrenze.
* Escape: schließt das Textfeld und springt zurück in die Liste. Der Text wird dabei automatisch übernommen.
* Alt+1: macht die aktuelle Zeile zur Überschrift der Ebene 1.
* Alt+2 und Alt+3: Überschrift der Ebene 2 und 3.
* Alt+0: macht die Überschrift wieder zu normalem Text.
* Überschriften werden mit Markdown-Zeichen geschrieben (siehe Abschnitt 6). Der Screenreader liest so immer mit, dass es eine Überschrift ist. Zusätzlich sagt das Programm beim Setzen „Überschrift Ebene 1“ an.

## 6\. Speichern und Öffnen

* Strg+S oder der Listeneintrag „Speichern“ speichert.
* Beim ersten Speichern fragt das Programm nach Ordner und Dateinamen.
* Gespeichert wird immer in zwei Dateien mit gleichem Namen:

  * Eine Textdatei im Markdown-Format (.md). Diese Datei ist gleichzeitig die Projektdatei, die man wieder öffnen kann.
  * Eine PDF-Datei für andere Leser.
* Aufbau der Markdown-Datei:

  * Erste Zeile: „# Titel des Konzepts“
  * Jeder Abschnitt beginnt mit „## Name des Abschnitts“.
  * Überschriften im Text: Alt+1 ergibt „### “, Alt+2 ergibt „#### “, Alt+3 ergibt „##### “.
  * Beim Öffnen erkennt das Programm die Abschnitte an den „## “-Zeilen.
* Strg+O öffnet eine .md-Datei.
* Automatisches Speichern alle 60 Sekunden, sobald einmal ein Speicherort gewählt wurde.
* Beim Beenden mit ungespeicherten Änderungen kommt die Frage „Speichern? Ja / Nein / Abbrechen“.

## 7\. Barrierefreiheit

* Jedes Bedienelement hat einen sprechenden Namen für den Screenreader.
* Ansagen für Aktionen ohne Fokuswechsel, zum Beispiel „gespeichert“, „gelöscht“, „verschoben“.
* Alle Funktionen sind ohne Maus erreichbar.
* Rückfragen sind normale Dialoge mit OK und Abbrechen, Escape bedeutet immer Abbrechen.
* Gut lesbare, einstellbare Schriftgröße für Sehende.

## 8\. Ausbaustufen

1. Liste mit Abschnitten, Textfeld, Enter und Escape, Neu, Verschieben, Löschen, Umbenennen.
2. Speichern und Öffnen als Markdown, automatisches Speichern.
3. Überschriften mit Alt+1 bis Alt+3.
4. PDF-Ausgabe.

## 9\. Offene Fragen

* Soll das Textfeld neben der Liste stehen (Sehende sehen beides) oder die Liste ersetzen, solange es geöffnet ist?
* sehnde sehen beides.
* Soll es zusätzlich eine Ausgabe als reine .txt-Datei ohne Markdown-Zeichen geben?
* ja zum speichern, eine pdef erzeugen oder eine tex Datei ohne markdown. 
* 

