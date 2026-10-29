"""Découverte passive des ports série disponibles sur la machine locale."""


def lister_ports_disponibles() -> list[dict]:
    """Retourne les ports détectés sans ouvrir de connexion série."""
    try:
        from serial.tools import list_ports
    except ImportError as exc:
        raise RuntimeError(
            "La découverte des ports série nécessite pySerial. "
            "Installe-le avec : python -m pip install pyserial"
        ) from exc

    ports = []
    for port in list_ports.comports():
        ports.append({
            "port": port.device,
            "description": port.description,
            "fabricant": port.manufacturer,
            "identifiant_usb": (
                f"{port.vid:04X}:{port.pid:04X}"
                if port.vid is not None and port.pid is not None
                else None
            ),
        })
    return ports
