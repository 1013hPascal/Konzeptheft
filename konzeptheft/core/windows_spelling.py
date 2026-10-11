"""Rechtschreibprüfung von Windows (Spell Checking API, ab Windows 8), über ctypes.

Windows bringt für jede installierte Sprache eine Rechtschreibprüfung mit, dieselbe wie Edge und
andere Programme. So braucht das Konzeptheft keine zusätzliche Bibliothek und kein Wörterbuch.

Die Schnittstellen sind COM-Objekte. Ihre Methoden werden über die Tabelle der Funktionszeiger
aufgerufen; die Nummern folgen der Reihenfolge in spellcheck.h (0 bis 2 gehören IUnknown).
"""
from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import POINTER, byref, c_ulong, c_void_p, c_wchar_p
from dataclasses import dataclass

log = logging.getLogger(__name__)

S_OK, S_FALSE = 0, 1
CLSCTX_INPROC_SERVER = 1
COINIT_APARTMENTTHREADED = 2

# Aktionen, die Windows zu einem Fehler vorschlägt (CORRECTIVE_ACTION)
ACTION_NONE, ACTION_SUGGEST, ACTION_REPLACE, ACTION_DELETE = 0, 1, 2, 3


class GUID(ctypes.Structure):
    _fields_ = [("Data1", c_ulong), ("Data2", ctypes.c_ushort), ("Data3", ctypes.c_ushort),
                ("Data4", ctypes.c_ubyte * 8)]

    @classmethod
    def parse(cls, text: str) -> "GUID":
        guid = cls()
        ctypes.oledll.ole32.CLSIDFromString(c_wchar_p(text), byref(guid))
        return guid


CLSID_SPELL_CHECKER_FACTORY = "{7AB36653-1796-484B-BDFA-E74F1DB7C1DC}"
IID_SPELL_CHECKER_FACTORY = "{8E018A9D-2415-4677-BF08-794EA61F94BB}"


@dataclass(frozen=True)
class RawError:
    start: int
    length: int
    action: int
    replacement: str


class _Com:
    """Ein COM-Zeiger mit Aufruf über die Funktionstabelle."""

    def __init__(self, pointer: c_void_p) -> None:
        self.pointer = pointer

    def call(self, index: int, *args, argtypes: tuple = ()) -> int:
        vtable = ctypes.cast(self.pointer, POINTER(POINTER(c_void_p))).contents
        prototype = ctypes.WINFUNCTYPE(ctypes.HRESULT, c_void_p, *argtypes)
        return prototype(vtable[index])(self.pointer, *args)

    def release(self) -> None:
        if self.pointer:
            vtable = ctypes.cast(self.pointer, POINTER(POINTER(c_void_p))).contents
            ctypes.WINFUNCTYPE(c_ulong, c_void_p)(vtable[2])(self.pointer)
            self.pointer = c_void_p()

    def __del__(self) -> None:
        try:
            self.release()
        except Exception:                                  # noqa: BLE001 (beim Beenden egal)
            pass


def _take_string(pointer: c_wchar_p | c_void_p) -> str:
    """Von Windows angelegten Text lesen und freigeben."""
    address = pointer.value if isinstance(pointer, c_void_p) else ctypes.cast(pointer, c_void_p).value
    if not address:
        return ""
    text = ctypes.wstring_at(address)
    ctypes.windll.ole32.CoTaskMemFree(c_void_p(address))
    return text


def _strings(enum: _Com) -> list[str]:
    """Alle Einträge eines IEnumString."""
    result = []
    while True:
        item, fetched = c_void_p(), c_ulong()
        hr = enum.call(3, c_ulong(1), byref(item), byref(fetched),
                       argtypes=(c_ulong, POINTER(c_void_p), POINTER(c_ulong)))
        if hr != S_OK or not fetched.value:
            break
        result.append(_take_string(item))
    enum.release()
    return result


class WindowsSpellChecker:
    """Prüft Text in einer Sprache, zum Beispiel "de-DE". Wirft OSError, wenn Windows die Sprache
    oder die Schnittstelle nicht kennt."""

    def __init__(self, language: str = "de-DE") -> None:
        if sys.platform != "win32":
            raise OSError("Die Rechtschreibprüfung von Windows gibt es nur unter Windows.")
        ole32 = ctypes.oledll.ole32
        try:
            ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
        except OSError:
            pass                                           # schon anders eingerichtet: in Ordnung
        factory = c_void_p()
        ole32.CoCreateInstance(byref(GUID.parse(CLSID_SPELL_CHECKER_FACTORY)), None,
                               CLSCTX_INPROC_SERVER,
                               byref(GUID.parse(IID_SPELL_CHECKER_FACTORY)), byref(factory))
        self._factory = _Com(factory)
        supported = ctypes.c_int()
        self._factory.call(4, c_wchar_p(language), byref(supported),
                           argtypes=(c_wchar_p, POINTER(ctypes.c_int)))
        if not supported.value:
            raise OSError(f"Windows hat keine Rechtschreibprüfung für {language}.")
        checker = c_void_p()
        self._factory.call(5, c_wchar_p(language), byref(checker),
                           argtypes=(c_wchar_p, POINTER(c_void_p)))
        self._checker = _Com(checker)
        self.language = language

    def check(self, text: str) -> list[RawError]:
        """Fehler im Text mit Position und Länge (in UTF-16-Einheiten, für Deutsch dasselbe wie
        Zeichen)."""
        if not text.strip():
            return []
        enum_pointer = c_void_p()
        self._checker.call(4, c_wchar_p(text), byref(enum_pointer),
                           argtypes=(c_wchar_p, POINTER(c_void_p)))
        enum = _Com(enum_pointer)
        errors = []
        while True:
            error_pointer = c_void_p()
            hr = enum.call(3, byref(error_pointer), argtypes=(POINTER(c_void_p),))
            if hr != S_OK or not error_pointer.value:
                break
            error = _Com(error_pointer)
            start, length, action, replacement = c_ulong(), c_ulong(), ctypes.c_int(), c_void_p()
            error.call(3, byref(start), argtypes=(POINTER(c_ulong),))
            error.call(4, byref(length), argtypes=(POINTER(c_ulong),))
            error.call(5, byref(action), argtypes=(POINTER(ctypes.c_int),))
            error.call(6, byref(replacement), argtypes=(POINTER(c_void_p),))
            errors.append(RawError(start.value, length.value, action.value,
                                   _take_string(replacement)))
            error.release()
        enum.release()
        return errors

    def suggest(self, word: str) -> list[str]:
        if not word.strip():
            return []
        enum_pointer = c_void_p()
        hr = self._checker.call(5, c_wchar_p(word), byref(enum_pointer),
                                argtypes=(c_wchar_p, POINTER(c_void_p)))
        if hr not in (S_OK, S_FALSE) or not enum_pointer.value:
            return []
        return _strings(_Com(enum_pointer))
