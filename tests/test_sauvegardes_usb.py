from app.core.usb_backups import GestionnaireCopieUSB


def test_copier_sauvegarde_vers_cle_montee(tmp_path, monkeypatch):
    montage = tmp_path / "usb"
    montage.mkdir()
    source = tmp_path / "backups"
    sauvegarde = source / "20261031T120000000000Z"
    sauvegarde.mkdir(parents=True)
    (sauvegarde / "manifest.json").write_text('{"version": 1}', encoding="utf-8")
    (sauvegarde / "comptes.db").write_bytes(b"sqlite-test")

    monkeypatch.setattr("pathlib.Path.is_mount", lambda self: self == montage)
    gestionnaire = GestionnaireCopieUSB(montage, source)

    resultat = gestionnaire.copier_sauvegardes()

    copie = montage / "MaisonConnectee" / "backups" / sauvegarde.name
    assert resultat == {"copiees": 1, "ignorees": 0}
    assert (copie / "comptes.db").read_bytes() == b"sqlite-test"
    assert gestionnaire.copier_sauvegardes() == {"copiees": 0, "ignorees": 1}


def test_ne_pas_ecrire_si_cle_absente(tmp_path, monkeypatch):
    montage = tmp_path / "usb"
    montage.mkdir()
    monkeypatch.setattr("pathlib.Path.is_mount", lambda self: False)
    gestionnaire = GestionnaireCopieUSB(montage, tmp_path / "backups")

    import pytest
    with pytest.raises(RuntimeError, match="Clé USB absente"):
        gestionnaire.copier_sauvegardes()

    assert not (montage / "MaisonConnectee").exists()
