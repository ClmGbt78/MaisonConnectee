"""Transport série générique pour les futurs capteurs USB/COM.

Ce module ne définit aucun protocole de capteur : il transporte uniquement
des octets. Le pilote d'un capteur interprétera ensuite ces données.
"""

from dataclasses import dataclass
from typing import Callable, Protocol


class PortSerie(Protocol):
    is_open: bool

    def open(self) -> None: ...
    def close(self) -> None: ...
    def read(self, size: int = 1) -> bytes: ...
    def write(self, data: bytes) -> int: ...


@dataclass(frozen=True)
class ConfigurationPortSerie:
    port: str
    debit: int = 9600
    delai_lecture: float = 1.0

    def __post_init__(self) -> None:
        if not self.port.strip():
            raise ValueError("Le nom du port série est obligatoire.")
        if self.debit <= 0:
            raise ValueError("Le débit série doit être strictement positif.")
        if self.delai_lecture < 0:
            raise ValueError("Le délai de lecture ne peut pas être négatif.")


class TransportSeriePySerial:
    """Transport USB/série Windows, avec chargement optionnel de pySerial."""

    def __init__(
        self,
        configuration: ConfigurationPortSerie,
        fabrique_port: Callable[..., PortSerie] | None = None,
    ) -> None:
        self.configuration = configuration
        self._fabrique_port = fabrique_port
        self._port: PortSerie | None = None

    @property
    def est_ouvert(self) -> bool:
        return self._port is not None and self._port.is_open

    def ouvrir(self) -> None:
        if self.est_ouvert:
            return
        fabrique = self._fabrique_port
        if fabrique is None:
            try:
                import serial
            except ImportError as exc:
                raise RuntimeError(
                    "pySerial est requis pour utiliser un capteur série. "
                    "Installe-le avec : python -m pip install pyserial"
                ) from exc
            fabrique = serial.Serial

        port = fabrique(
            port=self.configuration.port,
            baudrate=self.configuration.debit,
            timeout=self.configuration.delai_lecture,
        )
        if not port.is_open:
            port.open()
        self._port = port

    def fermer(self) -> None:
        if self._port is not None:
            if self._port.is_open:
                self._port.close()
            self._port = None

    def lire(self, taille: int = 1) -> bytes:
        if taille <= 0:
            raise ValueError("La taille à lire doit être strictement positive.")
        return self._port_ouvert().read(taille)

    def ecrire(self, donnees: bytes) -> int:
        if not isinstance(donnees, bytes):
            raise TypeError("Les données série doivent être fournies en octets.")
        return self._port_ouvert().write(donnees)

    def _port_ouvert(self) -> PortSerie:
        if not self.est_ouvert:
            raise RuntimeError("Le port série n'est pas ouvert.")
        return self._port  # type: ignore[return-value]

    def __enter__(self) -> "TransportSeriePySerial":
        self.ouvrir()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.fermer()
