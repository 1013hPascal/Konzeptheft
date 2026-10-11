# Checkliste Konzeptheft, Stufen 1 bis 4

Bitte mit NVDA und Braillezeile durchgehen.
Tragen Sie [x] für OK oder [!] für ein Problem ein. Unter „Ergebnis:“ ist Platz für Notizen.
Start: start.bat im Ordner Konzeptheft.

## Liste

[ ] 1. Start
Tasten: start.bat.
Erwartet: Fokus in der Liste „Abschnitte“ auf „Neuer Eintrag, Alt+N“.
Ergebnis:

[ ] 2. Neuer Eintrag
Tasten: Enter auf „Neuer Eintrag“, Namen „Einleitung“ tippen, Enter. Danach „Problem“ und „Lösung“ ebenso.
Erwartet: Ansage „Einleitung angelegt, Position 1“. Fokus auf dem neuen Abschnitt.
Ergebnis:

[ ] 3. Bewegen
Tasten: Pfeil hoch und runter, Pos1, Ende.
Erwartet: Ansage zum Beispiel „2 Problem“, ohne „2 von 3“. Pos1 auf Abschnitt 1, Ende auf dem letzten.
Ergebnis:

[ ] 4. Alt+N
Tasten: auf „2 Problem“ Alt+N, Namen „Ursachen“, Enter.
Erwartet: „Ursachen angelegt, Position 3“. Danach steht „4 Lösung“.
Ergebnis:

[ ] 5. Verschieben
Tasten: Alt+Pfeil hoch auf „Lösung“.
Erwartet: „Lösung, jetzt an Position 3“. Fokus bleibt auf „Lösung“.
Ergebnis:

[ ] 6. Umbenennen
Tasten: F2, neuen Namen tippen, Enter.
Erwartet: Ansage „umbenannt in …“. Escape im Dialog ändert nichts.
Ergebnis:

[ ] 7. Löschen
Tasten: Entf. Erst Escape, dann noch einmal Entf und OK.
Erwartet: Frage „Abschnitt ‚Name‘ löschen?“. Escape lässt ihn stehen. Nach OK: „Name gelöscht“.
Ergebnis:

[ ] 8. Kontextmenü
Tasten: Anwendungstaste oder Umschalt+F10 auf einem Abschnitt.
Erwartet: Menü „Abschnitt“ mit Umbenennen, Neuer Abschnitt darunter, Nach oben, Nach unten, Löschen. Erster Eintrag wird angesagt.
Ergebnis:

## Textfeld

[ ] 9. Öffnen und zurück
Tasten: Enter auf einem Abschnitt, etwas tippen, Escape.
Erwartet: Fokus im Feld „Text von Name“. Nach Escape wieder in der Liste auf genau diesem Abschnitt.
Ergebnis:

[ ] 10. Enter am Zeilenende
Tasten: „Hallo“ tippen, Enter.
Erwartet: Braillezeile zeigt sofort die neue, leere Zeile. NVDA sagt „leer“.
Ergebnis:

[ ] 11. Buchstabe am Ende der oberen Zeile
Tasten: Pfeil hoch, Ende, einen Buchstaben tippen.
Erwartet: Der Buchstabe steht in der oberen Zeile, die Braillezeile bleibt in dieser Zeile.
Ergebnis:

[ ] 12. Leere Zeilen mit Pfeiltasten, Rücktaste und Entf
Tasten: Leerzeilen zwischen zwei Zeilen anlegen. Pfeil hoch und runter, Pfeil links und rechts, Rücktaste, Entf.
Erwartet: Wie im Editor. Leere Zeilen heißen „leer“. Pfeil rechts in einer leeren Zeile geht gleich in die nächste Zeile.
Ergebnis:

[ ] 13. Überschriften
Tasten: in einer Zeile Alt+1, Alt+2, Alt+3, Alt+0.
Erwartet: Ansage „Überschrift Ebene 1“ und so weiter, bei Alt+0 „Normaler Text“. Die Zeile beginnt mit „# “, „## “, „### “.
Ergebnis:

## Dateien

[ ] 14. Erstes Speichern
Tasten: Strg+S.
Erwartet: Speichern-Dialog von Windows im Ordner Dateien. Danach Ansage „gespeichert“. Im Ordner liegen .konzept, .pdf und .txt.
Ergebnis:

[ ] 15. PDF und TXT lesen
Tasten: PDF und TXT öffnen.
Erwartet: Titel, nummerierte Abschnitte, Überschriften im Text. In der TXT keine #-Zeichen. Leere Zeilen sind erhalten.
Ergebnis:

[ ] 16. Öffnen
Tasten: Strg+O, die .konzept-Datei wählen.
Erwartet: Ansage „Titel geöffnet, N Abschnitte“. Alle Abschnitte und Texte sind da.
Ergebnis:

[ ] 17. Beenden mit Änderungen
Tasten: etwas ändern, Alt+F4.
Erwartet: Frage „Änderungen speichern?“ mit Ja, Nein, Abbrechen. Escape bricht ab.
Ergebnis:

[ ] 18. Automatisch speichern
Tasten: nach dem ersten Speichern etwas ändern, über eine Minute warten.
Erwartet: Keine Ansage. Das Sternchen im Fenstertitel verschwindet.
Ergebnis:

[ ] 19. Schrift und Hilfe
Tasten: Strg+Plus, Strg+Minus, F1.
Erwartet: Ansage „Schrift 13 Punkt“. F1 zeigt die Tasten als Liste, Escape schließt.
Ergebnis:

## Unterlisten

[ ] 20. Unterliste öffnen
Tasten: auf „3 Lösung“ Pfeil rechts.
Erwartet: Ansage „Unterliste 3.0 Lösung, leer“. Einzige Zeile: „Kein Eintrag, Alt+N für ersten Untereintrag“.
Ergebnis:

[ ] 21. Erster Untereintrag
Tasten: Alt+N, Namen tippen, Enter. Dann noch einmal Alt+N.
Erwartet: „Name angelegt, 3.1“, danach 3.2. Der zweite steht unter dem ersten.
Ergebnis:

[ ] 22. Zurück
Tasten: Pfeil links.
Erwartet: Hauptliste, Fokus auf „3.0 Lösung“.
Ergebnis:

[ ] 23. Zweite Unterebene
Tasten: in die Unterliste von 3, auf 3.1 Pfeil rechts, Alt+N.
Erwartet: „Unterliste 3.1.0 …“, neuer Eintrag 3.1.1. Nach Pfeil links heißt der Eintrag 3.1.0. Noch einmal Pfeil links: Abschnitt 3 heißt jetzt 3.0.0.
Ergebnis:

[ ] 24. Grenze
Tasten: viermal Pfeil rechts und Alt+N, dann noch einmal Pfeil rechts.
Erwartet: „Keine weitere Unterliste möglich.“
Ergebnis:

[ ] 25. Löschen mit Unterliste
Tasten: Entf auf einem Abschnitt mit .0.
Erwartet: Frage nennt die Anzahl der Untereinträge. Escape lässt alles stehen.
Ergebnis:

[ ] 26. Struktur speichern und öffnen
Tasten: Strg+S, Strg+N, Strg+O, die Datei wählen.
Erwartet: Alle Unterlisten sind wieder da, mit gleichen Nummern und Texten.
Ergebnis:

[ ] 27. PDF mit Überschriften
Tasten: die PDF öffnen, in NVDA mit H und 1 bis 5 springen.
Erwartet: Abschnitte der Hauptliste sind Überschrift Ebene 1, die der ersten Unterliste Ebene 2 und so weiter.
Ergebnis:

## LaTeX

[ ] 28. Exportieren
Tasten: Strg+E, Namen bestätigen.
Erwartet: Speichern-Dialog mit Vorschlag „Name.tex“. Danach Ansage „Name.tex exportiert“. Fokus wieder in der Liste.
Ergebnis:

[ ] 29. Übersetzen
Tasten: die .tex mit pdflatex oder TeXworks übersetzen.
Erwartet: Keine Fehler. Inhaltsverzeichnis und Nummern wie im Konzeptheft.
Ergebnis:
