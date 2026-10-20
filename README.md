# Konzeptheft

Barrierefreies Schreibprogramm für Konzepte, Ideen und Verbesserungsvorschläge. Für Windows, gebaut für NVDA und Braillezeile, auch für Sehende gut benutzbar.

Ein Konzept besteht aus benannten Abschnitten. Statt wie in Word lange zu scrollen, springen Sie mit den Pfeiltasten direkt zum richtigen Abschnitt. Abschnitte lassen sich in bis zu vier Unterebenen verschachteln.

## Funktionen

- Abschnittsliste mit automatischer Nummerierung. Nach jedem Einfügen, Verschieben oder Löschen wird neu durchgezählt.
- Unterlisten bis zu vier Ebenen tief. Jedes .0 an einer Nummer zeigt eine Unterebene an: 3.0 hat eine Unterliste, 3.0.0 zwei Ebenen darunter.
- Textfeld für jeden Abschnitt. Liste und Text stehen nebeneinander.
- Überschriften im Text mit Alt+1 bis Alt+3.
- Speichern als Projektdatei (.konzept), die die ganze Struktur behält.
- Bei jedem Speichern entstehen dazu eine PDF und eine Textdatei für andere Leser. In der PDF werden die Abschnitte zu Überschriften: Hauptliste Ebene 1, erste Unterliste Ebene 2 und so weiter.
- Automatisches Speichern jede Minute, sobald ein Speicherort gewählt ist.
- Export als Word (.docx) mit echten Überschriften und Listen, mit Strg+Umschalt+E.
- Export als LaTeX (.tex) mit fertigem Kopf für deutsche Texte, mit Strg+E.
- Listen im Text mit „- “ oder „1. “ werden in Word, LaTeX und PDF zu echten Listen.
- Alte Markdown-Dateien (.md) lassen sich öffnen.
- Rechtschreibprüfung wie in Word: rote Wellenlinie, ein kurzer Ton beim Vertippen, Ansage der Fehler beim Lesen und ein Dialog zum Korrigieren (Alt+R und Alt+Umschalt+R).
- Sucht beim Start nach Updates und tauscht die Exe auf Wunsch selbst aus.
- Einstellbare Schriftgröße.

## Barrierefreiheit

- Alles ist mit der Tastatur bedienbar.
- Jedes Bedienelement hat einen kurzen Namen für den Screenreader.
- Aktionen wie Speichern, Löschen oder Verschieben werden angesagt, ohne den Fokus zu verschieben.
- Rückfragen haben die sichere Antwort als Vorgabe. Escape bricht immer ab.
- Leere Zeilen im Textfeld erscheinen auf der Braillezeile sofort als neue Zeile. Qt meldet sie sonst falsch.

## Bedienung

### In der Liste

- Pfeil hoch und runter: vorheriger und nächster Eintrag.
- Pos1 und Ende: erster und letzter Abschnitt.
- Enter auf einem Abschnitt: Text öffnen.
- Enter auf „Neuer Eintrag, Alt+N“: neuer Abschnitt am Ende.
- Enter auf „Speichern“: speichern.
- Alt+N: neuer Abschnitt unter dem aktuellen.
- Alt+Pfeil hoch und runter: Abschnitt verschieben.
- F2: umbenennen.
- Entf: löschen, mit seiner Unterliste.
- Pfeil rechts: Unterliste öffnen. In einer leeren Unterliste legt Alt+N den ersten Untereintrag an.
- Pfeil links: zurück in die obere Liste.
- Anwendungstaste oder Umschalt+F10: Kontextmenü.

### Im Textfeld

- Escape: zurück in die Liste, auf genau den Abschnitt, aus dem Sie kamen. Der Text wird übernommen.
- Alt+1, Alt+2, Alt+3: Die Zeile wird Überschrift der Ebene 1, 2 oder 3.
- Alt+0: Die Zeile wird wieder normaler Text.
- Listen: Zeile mit „- “ oder „* “ beginnen für Punkte, mit „1. “ für Nummern. Zwei Leerzeichen davor machen eine Ebene tiefer, bis zu vier Ebenen. Eine leere Zeile beendet die Liste.

### Überall

- Strg+N: neues Konzept.
- Strg+O: öffnen.
- Strg+S: speichern.
- Strg+Umschalt+S: speichern unter.
- Strg+Umschalt+E: als Word exportieren.
- Strg+E: als LaTeX exportieren.
- Alt+T: Titel des Konzepts ändern.
- Strg+Plus, Strg+Minus, Strg+0: Schrift größer, kleiner, normal.
- Strg+Umschalt+M: letzte Ansage wiederholen.
- F1: alle Tasten anzeigen.

### Rechtschreibung

- Falsche Wörter sind rot gewellt unterstrichen. Ist ein Wort fertig getippt und falsch, kommt ein kurzer Ton.
- Beim Wechsel in eine Zeile mit Fehlern sagt das Programm die falschen Wörter an, zum Beispiel „Fehler: Tset“. Bei Strg+Pfeil auf ein falsches Wort sagt es „Rechtschreibfehler“.
- Alt+R im Textfeld: Dialog für das Wort am Cursor.
- Alt+Umschalt+R: Dialog für alle Fehler im ganzen Konzept, Abschnitt für Abschnitt.
- Im Dialog: Feld mit dem Wort, mit Tab die Vorschläge (Leertaste hakt einen an), Weiter, In Wörterbuch übernehmen, Schließen und die Liste Meine Wörter.
- Weiter übernimmt den angehakten Vorschlag oder das im Feld geänderte Wort. Ist nichts geändert, geht es ohne Änderung zum nächsten Fehler.
- Meine Wörter: Alle übernommenen Wörter sind angehakt. Ein abgewähltes Wort wird bei Schließen oder Weiter aus der Liste gelöscht.
- Im Menü Rechtschreibung lassen sich Prüfung, Ton und Ansagen einzeln abschalten.

Die Prüfung nutzt die Rechtschreibprüfung von Windows. Dafür muss Deutsch als Sprache in Windows installiert sein.

## Dateien

Gespeichert wird normalerweise im Ordner „Dateien“ im Programmordner. Zu jedem Konzept gibt es drei Dateien mit gleichem Namen:

- .konzept: die Projektdatei. Diese Datei öffnen Sie wieder mit Strg+O.
- .pdf: zum Weitergeben, mit Überschriften für jede Ebene.
- .txt: reiner Text, die Nummern zeigen die Ebene.

Mit Strg+Umschalt+E entsteht auf Wunsch eine Word-Datei (.docx). Die Abschnitte sind dort echte Word-Überschriften (Überschrift 1, 2 und so weiter), so dass man in Word mit NVDA von Überschrift zu Überschrift springen kann. Listen sind echte Word-Listen.

Mit Strg+E entsteht auf Wunsch zusätzlich eine LaTeX-Datei (.tex). Sie lässt sich mit pdflatex oder lualatex übersetzen, zum Beispiel mit MiKTeX. Der Kopf lädt unter anderem utf8, babel (ngerman), T1-Schrift, csquotes, booktabs, tabularx, enumitem, amsmath, siunitx und hyperref. Die Abschnitte werden \section, \subsection, \subsubsection, \paragraph und \subparagraph, mit denselben Nummern wie im Konzeptheft. Listen werden itemize (Punkte) und enumerate (Nummern), auch verschachtelt. Dazu kommt ein Inhaltsverzeichnis.

## Updates

Die Exe sucht bei jedem Start im Hintergrund nach einer neuen Version auf GitHub. Gibt es eine, fragt sie nach. Die neue Version wird heruntergeladen, geprüft und beim Beenden eingesetzt. Die bisherige Exe kommt in die Sicherheitskopien unter %LOCALAPPDATA%\Konzeptheft. Der Ordner Dateien bleibt unberührt.
Sofort suchen: Hilfe, Nach Updates suchen. Abschalten: Hilfe, Beim Start nach Updates suchen.

## Systemanforderungen

Windows 10 oder 11, mit Deutsch als installierter Sprache für die Rechtschreibprüfung. Für den Quellcode: Python 3.11 oder neuer.

## Werkzeuge und Bibliotheken

- PySide6
- pytest und pytest-qt (nur für die Tests)

## Installation aus dem Quellcode

```
cd Konzeptheft
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Danach startet start.bat das Programm ohne Konsolenfenster. Gibt es keine eigene .venv, nimmt start.bat die Umgebung des CodeCockpits aus dem Nachbarordner.

## Tests

```
python -m pytest
```

## Weitere Unterlagen

- Konzept Konzeptheft.md: das ursprüngliche Konzept.
- ENTSCHEIDUNGEN.md: wo und warum das Programm vom Konzept abweicht oder es ergänzt.
- checklisten\stufe-1-bis-4.md: Prüfliste für NVDA und Braillezeile.

## Änderungen

### 1.1.0 (20.10.2026)

- Export mit Word und pdf

### 1.0.5 (13.10.2026)

- README und Konfiguration aktualisiert

### 1.0.4 (13.10.2026)

- Version 1.0.4
- Exe-Einstellungen
