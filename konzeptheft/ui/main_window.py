"""Hauptfenster: Menüleiste, Abschnittsliste und Textfeld nebeneinander.

Sehende sehen Liste und Text gleichzeitig (Konzept, offene Fragen). Tasten, die nur in der Liste
gelten (Entf, F2, Alt+N, Alt+Pfeil), und Tasten, die nur im Textfeld gelten (Alt+0 bis Alt+3),
hängen als Widget-Kürzel am jeweiligen Steuerelement. So löscht Entf im Text nur Zeichen.

Unterlisten: self.level ist die Kette der geöffneten Abschnitte, leer in der Hauptliste.
Pfeil rechts öffnet die Unterliste des markierten Abschnitts, Pfeil links geht zurück.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths, Qt, QTimer
from PySide6.QtGui import QAction, QFont, QKeySequence
from PySide6.QtWidgets import (QFileDialog, QLabel, QMainWindow, QSplitter, QVBoxLayout,
                               QWidget)

from konzeptheft import APP_NAME, __version__
from konzeptheft.core import storage
from konzeptheft.core.concept import MAX_SUBLEVELS, Concept, Section, heading_level, number_text
from konzeptheft.core.project import SUFFIX
from konzeptheft.core.spelling import MyWords, Spelling
from konzeptheft.core.storage import StorageError
from konzeptheft.ui.announcer import announce, announcer
from konzeptheft.ui.common import announce_focus, ask_buttons, ask_name, show_error
from konzeptheft.ui.editor import SectionEditor
from konzeptheft.ui.menus import AccessibleMenu
from konzeptheft.ui.pdf import save_pdf
from konzeptheft.ui.section_list import MAIN_NAME, NEW_ROW, SAVE_ROW, SectionList
from konzeptheft.ui.spelling_ui import ENABLED_KEY, SOUND_KEY, SPEAK_KEY, SpellSupport
from konzeptheft.ui.update_ui import Updater

log = logging.getLogger(__name__)

AUTOSAVE_MS = 60_000
DEFAULT_FONT_POINTS = 12
MIN_FONT_POINTS, MAX_FONT_POINTS = 8, 40

HELP_TEXT = """Konzeptheft, Tasten

In der Liste:
Pfeil hoch und runter: vorheriger und nächster Eintrag.
Pos1 und Ende: erster und letzter Abschnitt.
Enter auf einem Abschnitt: Text öffnen.
Enter auf Neuer Eintrag: neuer Abschnitt am Ende.
Enter auf Speichern: speichern.
Alt+N: neuer Abschnitt unter dem aktuellen.
Alt+Pfeil hoch und runter: Abschnitt verschieben.
F2: umbenennen.
Entf: löschen, mit seiner Unterliste.
Anwendungstaste oder Umschalt+F10: Kontextmenü.

Unterlisten:
Pfeil rechts: Unterliste des Abschnitts öffnen.
Pfeil links: zurück in die obere Liste.
In einer leeren Unterliste legt Alt+N oder Enter den ersten Untereintrag an.
Jedes .0 am Ende einer Nummer steht für eine Unterebene darunter.
Zum Beispiel 3.0: eine Unterliste. 3.0.0: Die Unterliste hat selbst wieder eine.
Es gibt höchstens vier Unterebenen.

Im Textfeld:
Escape: zurück in die Liste. Der Text wird übernommen.
Alt+1, Alt+2, Alt+3: Zeile wird Überschrift der Ebene 1, 2 oder 3.
Alt+0: Zeile wird wieder normaler Text.
Umschalt+Enter: neuer Absatz.

Überall:
Strg+N: neues Konzept.
Strg+O: öffnen.
Strg+S: speichern.
Strg+Umschalt+S: speichern unter.
Strg+E: als LaTeX exportieren.
Strg+Plus und Strg+Minus: Schrift größer und kleiner.
Strg+Umschalt+M: letzte Ansage wiederholen.

Rechtschreibung:
Falsche Wörter sind rot unterstrichen. Ist ein Wort falsch getippt, kommt ein kurzer Ton.
Beim Wechsel in eine Zeile mit Fehlern sagt das Programm die falschen Wörter an.
Alt+R im Textfeld: Dialog für das Wort am Cursor.
Alt+Umschalt+R: Dialog für das ganze Konzept.
Im Dialog: Wort-Feld, Tab zu den Vorschlägen (Leertaste hakt einen an), Weiter,
In Wörterbuch übernehmen, Schließen und die Liste Meine Wörter.
Weiter übernimmt den angehakten Vorschlag oder das geänderte Wort, sonst geht es zum nächsten Fehler.
In Meine Wörter entfernt das Abwählen eines Wortes es beim Schließen oder bei Weiter.

Beim Speichern entstehen drei Dateien mit gleichem Namen, normalerweise im Ordner Dateien:
.konzept ist die Projektdatei mit allen Unterlisten, zum Wieder-Öffnen,
.pdf ist für andere Leser,
.txt ist reiner Text.
In PDF und Text werden die Abschnitte Überschriften: Hauptliste Ebene 1, erste Unterliste
Ebene 2 und so weiter.
Nach dem ersten Speichern wird jede Minute automatisch gespeichert."""


def program_folder() -> Path:
    """Ordner des Programms: neben der Exe oder über dem Paket konzeptheft."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


AUTO = object()                          # Rechtschreibprüfung von Windows selbst einrichten


def default_spelling(data_dir: Path) -> Spelling | None:
    """Rechtschreibprüfung von Windows für Deutsch, None wenn es sie nicht gibt."""
    from konzeptheft.core.windows_spelling import WindowsSpellChecker
    try:
        checker = WindowsSpellChecker("de-DE")
    except OSError as exc:
        log.warning("Keine Rechtschreibprüfung: %s", exc)
        return None
    return Spelling(checker, MyWords(data_dir / "meine-woerter.txt"))


def user_data_dir() -> Path:
    """Ordner für Meine Wörter: Konzeptheft unter %APPDATA%."""
    return Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))


class MainWindow(QMainWindow):
    def __init__(self, settings: QSettings | None = None,
                 base_folder: Path | None = None, spelling=AUTO,
                 exe_path: Path | None = None) -> None:
        super().__init__()
        self.settings = settings or QSettings(APP_NAME, APP_NAME)
        self.base_folder = base_folder or program_folder()
        self.concept = Concept()
        self.path: Path | None = None                  # Pfad der .konzept-Datei
        self.level: list[Section] = []                 # geöffnete Unterlisten, außen zuerst

        self.list = SectionList()
        self.editor = SectionEditor()
        self.editor_label = QLabel()
        self.editor_label.setBuddy(self.editor)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.editor_label)
        right_layout.addWidget(self.editor)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.list_label = QLabel()
        self.list_label.setBuddy(self.list)
        left_layout.addWidget(self.list_label)
        left_layout.addWidget(self.list)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setChildrenCollapsible(False)
        self.setCentralWidget(splitter)
        self.setTabOrder(self.list, self.editor)

        self.list.itemActivated.connect(lambda _item: self.activate_row())
        self.list.contextMenuRequested.connect(self.show_context_menu)
        self.list.openRequested.connect(self.open_sublist)
        self.list.closeRequested.connect(self.close_sublist)
        self.editor.closeRequested.connect(self.close_editor)
        self.editor.textChanged.connect(self._text_changed)

        self.spell = SpellSupport(self, default_spelling(user_data_dir()) if spelling is AUTO
                                  else spelling)
        self.updater = Updater(self, exe_path)
        self._build_actions()
        self._build_menus()
        announcer.target = self
        announcer.listeners.append(lambda message: self.statusBar().showMessage(message.text))

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(AUTOSAVE_MS)
        self.autosave_timer.timeout.connect(self.autosave)
        self.autosave_timer.start()

        self.apply_font_size(int(self.settings.value("font_points", DEFAULT_FONT_POINTS)))
        self.resize(1100, 720)
        self.refresh()

    # -- Aktionen und Menüs -------------------------------------------------------------------
    def _action(self, text: str, slot, shortcut: str | QKeySequence | None = None,
                widget: QWidget | None = None) -> QAction:
        """Aktion mit Kürzel. Mit widget gilt das Kürzel nur, wenn das Steuerelement den Fokus
        hat; im Menü steht es trotzdem."""
        action = QAction(text, self)
        if shortcut is not None:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(lambda _checked=False: slot())
        if widget is not None:
            action.setShortcutContext(Qt.ShortcutContext.WidgetShortcut)
            widget.addAction(action)
        return action

    def _toggle(self, text: str, key: str, changed) -> QAction:
        """Ein- und ausschaltbarer Menüeintrag. Vorgabe: an."""
        action = QAction(text, self)
        action.setCheckable(True)
        action.setChecked(str(self.settings.value(key, "true")).lower() == "true")
        action.toggled.connect(changed)
        action.toggled.connect(lambda on: announce(f"{text.replace('&', '')} "
                                                   + ("an" if on else "aus")))
        return action

    def _build_actions(self) -> None:
        self.act_new = self._action("&Neu", self.new_concept, QKeySequence.StandardKey.New)
        self.act_open = self._action("Ö&ffnen…", self.open_dialog, QKeySequence.StandardKey.Open)
        self.act_save = self._action("&Speichern", self.save, QKeySequence.StandardKey.Save)
        self.act_save_as = self._action("Speichern &unter…", self.save_as, "Ctrl+Shift+S")
        self.act_latex = self._action("Als &LaTeX exportieren…", self.export_latex, "Ctrl+E")
        self.act_quit = self._action("&Beenden", self.close)
        self.act_new_section = self._action("Neuer Abschnitt am &Ende…", self.add_section_at_end)
        self.act_insert = self._action("Neuer Abschnitt &darunter…", self.insert_section,
                                       "Alt+N", self.list)
        self.act_rename = self._action("&Umbenennen…", self.rename_section, "F2", self.list)
        self.act_up = self._action("Nach &oben", lambda: self.move_section(-1), "Alt+Up",
                                   self.list)
        self.act_down = self._action("Nach u&nten", lambda: self.move_section(1), "Alt+Down",
                                     self.list)
        self.act_delete = self._action("&Löschen…", self.delete_section, "Del", self.list)
        # Pfeil rechts und links behandelt die Liste selbst; hier stehen sie nur zum Nachlesen
        self.act_sub_open = self._action("Unterliste ö&ffnen\tPfeil rechts", self.open_sublist)
        self.act_sub_close = self._action("&Zurück zur oberen Liste\tPfeil links",
                                          self.close_sublist)
        self.act_title = self._action("&Titel ändern…", self.change_title)
        self.act_headings = [
            self._action(f"Überschrift Ebene &{level}", lambda lv=level: self.set_heading(lv),
                         f"Alt+{level}", self.editor) for level in (1, 2, 3)]
        self.act_plain = self._action("&Normaler Text", lambda: self.set_heading(0), "Alt+0",
                                      self.editor)
        self.act_bigger = self._action("Schrift &größer", lambda: self.change_font_size(1),
                                       QKeySequence.StandardKey.ZoomIn)
        self.act_smaller = self._action("Schrift &kleiner", lambda: self.change_font_size(-1),
                                        QKeySequence.StandardKey.ZoomOut)
        self.act_font_default = self._action("Schrift &normal",
                                             lambda: self.change_font_size(0), "Ctrl+0")
        self.act_repeat = self._action("Letzte &Ansage wiederholen", announcer.repeat_last,
                                       "Ctrl+Shift+M")
        self.act_help = self._action("&Tasten", self.show_help, "F1")
        self.act_about = self._action("Ü&ber Konzeptheft", self.show_about)
        self.act_spell_word = self._action("&Wort prüfen…", self.spell.check_word, "Alt+R")
        self.act_spell_all = self._action("&Ganzes Konzept prüfen…", self.spell.check_concept,
                                          "Alt+Shift+R")
        self.act_my_words = self._action("&Meine Wörter…", self.spell.edit_my_words)
        self.act_spell_flags = [
            self._toggle(text, key, lambda on, k=key: self.spell.set_flag(k, on))
            for text, key in (("Rechtschreib&prüfung an", ENABLED_KEY),
                              ("&Ton bei Tippfehlern", SOUND_KEY),
                              ("Fehler beim Lesen &ansagen", SPEAK_KEY))]
        self.act_update = self._action("Nach &Updates suchen…", self.updater.check_now)
        self.act_update_start = self._toggle("Beim Start nach Updates &suchen",
                                             "update/check_at_start",
                                             lambda on: setattr(self.updater, "check_at_start", on))
        # Diese Kürzel gelten im ganzen Fenster
        for action in (self.act_new, self.act_open, self.act_save, self.act_save_as,
                       self.act_latex,
                       self.act_bigger, self.act_smaller, self.act_font_default,
                       self.act_repeat, self.act_help, self.act_spell_word, self.act_spell_all):
            self.addAction(action)

    def _build_menus(self) -> None:
        bar = self.menuBar()
        file_menu = AccessibleMenu("&Datei", self)
        file_menu.addActions([self.act_new, self.act_open, self.act_save, self.act_save_as])
        file_menu.addSeparator()
        file_menu.addAction(self.act_latex)
        file_menu.addSeparator()
        file_menu.addAction(self.act_quit)
        edit_menu = AccessibleMenu("&Bearbeiten", self)
        edit_menu.addActions([self.act_new_section, self.act_insert, self.act_rename,
                              self.act_up, self.act_down, self.act_delete])
        edit_menu.addSeparator()
        edit_menu.addActions([self.act_sub_open, self.act_sub_close])
        edit_menu.addSeparator()
        edit_menu.addAction(self.act_title)
        format_menu = AccessibleMenu("&Format", self)
        format_menu.addActions([*self.act_headings, self.act_plain])
        view_menu = AccessibleMenu("&Ansicht", self)
        view_menu.addActions([self.act_bigger, self.act_smaller, self.act_font_default])
        view_menu.addSeparator()
        view_menu.addAction(self.act_repeat)
        help_menu = AccessibleMenu("&Hilfe", self)
        spell_menu = AccessibleMenu("Recht&schreibung", self)
        spell_menu.addActions([self.act_spell_word, self.act_spell_all, self.act_my_words])
        spell_menu.addSeparator()
        spell_menu.addActions(self.act_spell_flags)
        help_menu.addActions([self.act_help, self.act_update, self.act_update_start])
        help_menu.addSeparator()
        help_menu.addAction(self.act_about)
        for menu in (file_menu, edit_menu, format_menu, spell_menu, view_menu, help_menu):
            bar.addMenu(menu)

    def show_context_menu(self, position) -> None:
        menu = AccessibleMenu("Abschnitt", self)
        if self.list.section_index() is not None:
            menu.addActions([self.act_rename, self.act_insert, self.act_up, self.act_down,
                             self.act_delete, self.act_sub_open])
        elif not self.list.is_main:
            menu.addAction(self.act_insert)
        else:
            return
        if self.level:
            menu.addAction(self.act_sub_close)
        menu.exec(position)

    # -- Ebenen ---------------------------------------------------------------------------------
    @property
    def parent(self) -> Section | None:
        """Abschnitt, dessen Unterliste gerade offen ist. None in der Hauptliste."""
        return self.level[-1] if self.level else None

    @property
    def siblings(self) -> list[Section]:
        return self.concept.children_of(self.parent)

    def level_name(self) -> str:
        """Name der Liste für den Screenreader, zum Beispiel "Unterliste 3.0 Lösung"."""
        if self.parent is None:
            return MAIN_NAME
        numbers = self.concept.numbers_of(self.parent) or [0]
        return f"Unterliste {number_text(numbers, max(1, self.parent.sublevels()))} {self.parent.name}"

    def _ancestors(self, section: Section) -> list[Section]:
        chain = []
        parent = self.concept.parent_of(section)
        while parent is not None:
            chain.insert(0, parent)
            parent = self.concept.parent_of(parent)
        return chain

    def open_sublist(self) -> None:
        index = self.list.section_index()
        if index is None:
            announce("Kein Abschnitt markiert.")
            return
        if len(self.level) >= MAX_SUBLEVELS:
            announce("Keine weitere Unterliste möglich.")
            return
        section = self.siblings[index]
        self.level.append(section)
        self.refresh(0 if section.children else -1)
        self.list.setFocus()
        announce_focus(self.list)
        count = len(section.children)
        announce(f"{self.level_name()}, " + (f"{count} Einträge" if count > 1 else
                                             "1 Eintrag" if count else "leer"))

    def close_sublist(self) -> None:
        if not self.level:
            announce("Schon in der Hauptliste.")
            return
        section = self.level.pop()
        self.refresh(self.siblings.index(section))
        self.list.setFocus()
        announce_focus(self.list)

    # -- Anzeige ----------------------------------------------------------------------------
    def refresh(self, current: int | None = None) -> None:
        """Liste der aktuellen Ebene neu füllen. current wie in SectionList.show_level."""
        rows = [self.concept.label(s) for s in self.siblings]
        self.list.show_level(rows, self.parent is None, self.level_name(), current)
        self.list_label.setText(f"{self.level_name()}:")
        self.update_title()

    def update_title(self) -> None:
        name = self.concept.title or (self.path.stem if self.path else "Unbenannt")
        star = "*" if self.concept.modified else ""
        self.setWindowTitle(f"{star}{name} – {APP_NAME}")
        if self.editor.section is None:
            self.editor_label.setText("Text:")
        else:
            self.editor_label.setText(f"Text von {self.concept.label(self.editor.section)}:")

    def initial_focus(self) -> None:
        self.list.setFocus()

    # -- Liste --------------------------------------------------------------------------------
    def activate_row(self) -> None:
        if self.list.section_index() is not None:
            self.open_editor()
        elif not self.list.is_main:
            self.insert_section()                       # "Kein Eintrag": ersten anlegen
        elif self.list.currentRow() == NEW_ROW:
            self.add_section_at_end()
        elif self.list.currentRow() == SAVE_ROW:
            self.save()

    def _current_or_announce(self) -> int | None:
        index = self.list.section_index()
        if index is None:
            announce("Kein Abschnitt markiert.")
        return index

    def _created(self, index: int) -> None:
        section = self.siblings[index]
        self.refresh(index)
        self.list.setFocus()
        if self.parent is None:
            announce(f"{section.name} angelegt, Position {index + 1}")
        else:
            numbers = self.concept.numbers_of(section) or [0]
            announce(f"{section.name} angelegt, {number_text(numbers, 0)}")

    def add_section_at_end(self) -> None:
        name = ask_name(self, "Neuer Abschnitt", "&Name des Abschnitts:")
        if name is None:
            self.list.setFocus()
            return
        self._created(self.concept.add(name, self.parent))

    def insert_section(self) -> None:
        current = self.list.section_index()
        title = "Neuer Abschnitt" if self.parent is None else "Neuer Untereintrag"
        name = ask_name(self, title, "&Name des Abschnitts:")
        if name is None:
            self.list.setFocus()
            return
        self._created(self.concept.insert_after(-1 if current is None else current, name,
                                                self.parent))

    def rename_section(self) -> None:
        index = self._current_or_announce()
        if index is None:
            return
        section = self.siblings[index]
        name = ask_name(self, "Umbenennen", "&Neuer Name:", section.name)
        self.list.setFocus()
        if name is None or name == section.name:
            return
        self.concept.rename(section, name)
        if self.editor.section is section:
            self.editor.set_name(self.concept.label(section))
        self.refresh(index)
        announce(f"umbenannt in {section.name}")

    def move_section(self, delta: int) -> None:
        index = self._current_or_announce()
        if index is None:
            return
        target = self.concept.move(index, delta, self.parent)
        if target is None:
            announce("Schon ganz oben." if delta < 0 else "Schon ganz unten.")
            return
        self.refresh(target)
        self._rename_editor()
        announce(f"{self.siblings[target].name}, jetzt an Position {target + 1}")

    def delete_section(self) -> None:
        index = self._current_or_announce()
        if index is None:
            return
        section = self.siblings[index]
        below = section.count_all()
        extra = "" if not below else (" mit 1 Untereintrag" if below == 1
                                      else f" mit {below} Untereinträgen")
        choice = ask_buttons(self, "Löschen", f"Abschnitt „{section.name}“{extra} löschen?",
                             ["OK", "Abbrechen"], default=1, escape=1)
        self.list.setFocus()
        if choice != 0:
            return
        self.concept.remove(index, self.parent)
        if self.editor.section is not None and not self.concept.contains(self.editor.section):
            self.editor.close_section()
        self.refresh(min(index, len(self.siblings) - 1) if self.siblings else -1)
        self._rename_editor()
        announce(f"{section.name} gelöscht")

    def _rename_editor(self) -> None:
        """Nach Verschieben oder Löschen hat der geöffnete Abschnitt vielleicht eine neue Nummer."""
        if self.editor.section is not None:
            self.editor.set_name(self.concept.label(self.editor.section))
            self.update_title()

    def change_title(self) -> None:
        title = ask_name(self, "Titel", "&Titel des Konzepts:", self.concept.title)
        if title is not None:
            self.concept.title = title
            self.update_title()
            announce(f"Titel: {self.concept.title}")

    # -- Textfeld ---------------------------------------------------------------------------
    def open_editor(self) -> None:
        index = self._current_or_announce()
        if index is None:
            return
        section = self.siblings[index]
        if self.editor.section is not section:
            self.editor.open_section(section, self.concept.label(section))
        self.editor.setEnabled(True)
        self.update_title()
        self.editor.setFocus()
        self.spell.section_opened(section)

    def close_editor(self) -> None:
        """Escape im Textfeld: Text ist schon übernommen, zurück auf genau diesen Abschnitt,
        auch wenn die Liste inzwischen eine andere Ebene zeigt."""
        section = self.editor.section
        if section is not None and self.concept.contains(section):
            ancestors = self._ancestors(section)
            if ancestors != self.level:
                self.level = ancestors
                self.refresh()
            self.list.select_section(self.siblings.index(section))
        self.list.setFocus()

    def _text_changed(self) -> None:
        if self.editor.section is None:
            return
        was_modified = self.concept.modified
        self.concept.set_text(self.editor.section, self.editor.text())
        if self.concept.modified != was_modified:
            self.update_title()

    def set_heading(self, level: int) -> None:
        if self.editor.section is None:
            announce("Überschriften gehen nur im Textfeld.")
            return
        self.editor.set_heading(level)
        self.editor.setFocus()
        current = heading_level(self.editor.textCursor().block().text())
        announce(f"Überschrift Ebene {current}" if current else "Normaler Text")

    # -- Dateien ------------------------------------------------------------------------------
    def ask_save_changes(self) -> bool:
        """True, wenn es weitergehen darf. Ungespeicherte Änderungen: Ja / Nein / Abbrechen."""
        if not self.concept.modified:
            return True
        choice = ask_buttons(self, APP_NAME, "Änderungen speichern?",
                             ["Ja", "Nein", "Abbrechen"], default=0, escape=2)
        if choice == 0:
            return self.save()
        return choice == 1

    def new_concept(self) -> None:
        if not self.ask_save_changes():
            return
        self.set_concept(Concept(), None)
        announce("Neues Konzept")

    def set_concept(self, concept: Concept, path: Path | None) -> None:
        self.editor.close_section()
        self.concept = concept
        self.path = path
        self.level = []
        self.refresh(0 if len(concept) else -1)
        self.list.setFocus()

    def open_dialog(self) -> None:
        if not self.ask_save_changes():
            return
        chosen, _ = QFileDialog.getOpenFileName(
            self, "Konzept öffnen", self._start_folder(),
            f"Konzepte (*{SUFFIX});;Alte Markdown-Dateien (*.md);;Alle Dateien (*)")
        if chosen:
            self.open_file(Path(chosen))
        else:
            self.list.setFocus()

    def open_file(self, path: Path) -> bool:
        try:
            concept = storage.load(path)
        except StorageError as exc:
            show_error(self, "Öffnen", str(exc))
            return False
        # Eine alte .md-Datei wird beim ersten Speichern als .konzept gespeichert (mit Rückfrage)
        is_project = path.suffix.lower() == SUFFIX
        self.set_concept(concept, path if is_project else None)
        if is_project:
            self._remember(path)
        announce(f"{concept.title or path.stem} geöffnet, {len(concept)} Abschnitte")
        return True

    def save(self) -> bool:
        if self.path is None:
            return self.save_as()
        return self._write(self.path)

    def save_as(self) -> bool:
        suggestion = str(Path(self._start_folder()) / f"{self.concept.title or 'Konzept'}{SUFFIX}")
        chosen, _ = QFileDialog.getSaveFileName(self, "Speichern unter", suggestion,
                                                f"Konzepte (*{SUFFIX})")
        if not chosen:
            self.list.setFocus()
            return False
        path = storage.project_path(Path(chosen))
        if not self.concept.title:
            self.concept.title = path.stem
        self.path = path
        self._remember(path)
        return self._write(path)

    def _write(self, path: Path, quiet: bool = False) -> bool:
        """Schreibt .konzept, .txt und .pdf. Die Projektdatei kommt zuerst."""
        try:
            storage.save_project(path, self.concept)
        except StorageError as exc:
            if quiet:
                announce(f"Automatisch speichern fehlgeschlagen. {exc}", speak=False)
            else:
                show_error(self, "Speichern", str(exc))
            return False
        self.concept.modified = False
        self.update_title()
        problems = []
        for writer, target in ((storage.save_text, storage.text_path(path)),
                               (save_pdf, storage.pdf_path(path))):
            try:
                writer(target, self.concept)
            except StorageError as exc:
                problems.append(str(exc))
        if problems and not quiet:
            show_error(self, "Speichern", "Die Projektdatei ist gespeichert.\n" +
                       "\n".join(problems))
        if quiet:
            announce("automatisch gespeichert", speak=False)
        elif not problems:
            announce("gespeichert")
        return True

    def export_latex(self) -> bool:
        """LaTeX-Datei (.tex). Vorschlag: gleicher Name und Ordner wie die Projektdatei."""
        name = self.path.stem if self.path else (self.concept.title or "Konzept")
        suggestion = str(Path(self._start_folder()) / f"{name}.tex")
        chosen, _ = QFileDialog.getSaveFileName(self, "Als LaTeX exportieren", suggestion,
                                                "LaTeX (*.tex)")
        if not chosen:
            self.list.setFocus()
            return False
        target = storage.latex_path(Path(chosen))
        try:
            storage.save_latex(target, self.concept)
        except StorageError as exc:
            show_error(self, "Exportieren", str(exc))
            return False
        self.list.setFocus()
        announce(f"{target.name} exportiert")
        return True

    def autosave(self) -> None:
        """Alle 60 Sekunden, sobald ein Speicherort gewählt ist. Still: keine Ansage."""
        if self.path is not None and self.concept.modified:
            self._write(self.path, quiet=True)

    def _start_folder(self) -> str:
        """Ordner der offenen Datei, sonst der Ordner "Dateien" neben dem Programm."""
        if self.path is not None:
            return str(self.path.parent)
        try:
            return str(storage.data_folder(self.base_folder))
        except OSError:
            return str(Path.home() / "Documents")

    def _remember(self, path: Path) -> None:
        self.settings.setValue("last_file", str(path))

    def open_last_file(self) -> None:
        last = self.settings.value("last_file", "")
        if last and Path(last).is_file() and Path(last).suffix.lower() == SUFFIX:
            self.open_file(Path(last))

    def closeEvent(self, event) -> None:
        if self.ask_save_changes():
            self.autosave_timer.stop()
            self.updater.shutdown()
            event.accept()
        else:
            event.ignore()

    # -- Schrift und Hilfe ------------------------------------------------------------------
    def apply_font_size(self, points: int) -> None:
        points = max(MIN_FONT_POINTS, min(MAX_FONT_POINTS, points))
        self.font_points = points
        font = QFont(self.list.font())
        font.setPointSize(points)
        self.list.setFont(font)
        self.editor.setFont(font)
        self.settings.setValue("font_points", points)

    def change_font_size(self, step: int) -> None:
        self.apply_font_size(self.font_points + step if step else DEFAULT_FONT_POINTS)
        announce(f"Schrift {self.font_points} Punkt")

    def show_help(self) -> None:
        from konzeptheft.ui.text_dialog import TextDialog
        TextDialog("Tasten", HELP_TEXT, parent=self).exec()

    def show_about(self) -> None:
        from konzeptheft.ui.text_dialog import TextDialog
        TextDialog("Über Konzeptheft", f"{APP_NAME} {__version__}\nSchreibprogramm für Konzepte, "
                   "Ideen und Verbesserungsvorschläge.", parent=self).exec()
