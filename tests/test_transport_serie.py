import pytest

from app.domotique.adapters.transport_serie import (
    ConfigurationPortSerie,
    TransportSeriePySerial,
)


class PortSerieFactice:
    def __init__(self, **configuration):
        self.configuration = configuration
        self.is_open = True
        self.donnees_ecrites = []
        self.donnees_a_lire = b"\x01\x02"

    def open(self):
        self.is_open = True

    def close(self):
        self.is_open = False

    def read(self, size=1):
        resultat = self.donnees_a_lire[:size]
        self.donnees_a_lire = self.donnees_a_lire[size:]
        return resultat

    def write(self, data):
        self.donnees_ecrites.append(data)
        return len(data)


def test_configuration_serie_valide_les_parametres():
    with pytest.raises(ValueError):
        ConfigurationPortSerie("")
    with pytest.raises(ValueError):
        ConfigurationPortSerie("COM3", debit=0)
    with pytest.raises(ValueError):
        ConfigurationPortSerie("COM3", delai_lecture=-1)


def test_transport_serie_echange_des_octets_et_se_ferme():
    ports = []

    def creer_port(**configuration):
        port = PortSerieFactice(**configuration)
        ports.append(port)
        return port

    transport = TransportSeriePySerial(
        ConfigurationPortSerie("COM4", debit=115200, delai_lecture=0.5),
        fabrique_port=creer_port,
    )

    with transport:
        assert transport.est_ouvert
        assert transport.lire(2) == b"\x01\x02"
        assert transport.ecrire(b"PING") == 4
        assert ports[0].donnees_ecrites == [b"PING"]
        assert ports[0].configuration == {
            "port": "COM4", "baudrate": 115200, "timeout": 0.5
        }

    assert not transport.est_ouvert
    assert not ports[0].is_open


def test_transport_refuse_lecture_si_ferme_et_taille_invalide():
    transport = TransportSeriePySerial(
        ConfigurationPortSerie("COM3"),
        fabrique_port=PortSerieFactice,
    )
    with pytest.raises(RuntimeError):
        transport.lire()
    with pytest.raises(ValueError):
        transport.lire(0)
    with pytest.raises(TypeError):
        transport.ecrire("texte")
