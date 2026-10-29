import sys
from types import ModuleType, SimpleNamespace

import pytest

from app.domotique.adapters.ports_serie import lister_ports_disponibles


def test_lister_ports_retourne_les_informations_sans_ouvrir_le_port(monkeypatch):
    port = SimpleNamespace(
        device="COM4",
        description="USB Serial Device",
        manufacturer="Fabricant",
        vid=0x1234,
        pid=0xABCD,
    )
    serial = ModuleType("serial")
    tools = ModuleType("serial.tools")
    list_ports = ModuleType("serial.tools.list_ports")
    list_ports.comports = lambda: [port]
    tools.list_ports = list_ports
    serial.tools = tools
    monkeypatch.setitem(sys.modules, "serial", serial)
    monkeypatch.setitem(sys.modules, "serial.tools", tools)
    monkeypatch.setitem(sys.modules, "serial.tools.list_ports", list_ports)

    assert lister_ports_disponibles() == [{
        "port": "COM4",
        "description": "USB Serial Device",
        "fabricant": "Fabricant",
        "identifiant_usb": "1234:ABCD",
    }]


def test_lister_ports_retourne_liste_vide_si_aucun_port(monkeypatch):
    serial = ModuleType("serial")
    tools = ModuleType("serial.tools")
    list_ports = ModuleType("serial.tools.list_ports")
    list_ports.comports = lambda: []
    tools.list_ports = list_ports
    serial.tools = tools
    monkeypatch.setitem(sys.modules, "serial", serial)
    monkeypatch.setitem(sys.modules, "serial.tools", tools)
    monkeypatch.setitem(sys.modules, "serial.tools.list_ports", list_ports)

    assert lister_ports_disponibles() == []
