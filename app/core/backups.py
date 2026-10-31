import json
import logging
import re
import shutil
import sqlite3
import threading
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)
NOMS_BASES = ("comptes.db", "systeme_historique.db")
FORMAT_IDENTIFIANT = re.compile(r"^\d{8}T\d{12}Z$")


class GestionnaireSauvegardes:
    """Sauvegarde et restaure un ensemble cohérent de bases SQLite."""

    def __init__(
        self,
        chemins_bases: dict[str, Path],
        dossier_sauvegardes: Path,
        retention: int = 14,
    ):
        if set(chemins_bases) != set(NOMS_BASES):
            raise ValueError("Les deux bases attendues doivent être configurées.")
        if retention < 1:
            raise ValueError("La rétention doit être d'au moins une sauvegarde.")
        self.chemins_bases = {nom: Path(chemin) for nom, chemin in chemins_bases.items()}
        self.dossier_sauvegardes = Path(dossier_sauvegardes)
        self.retention = retention
        self._verrou = threading.RLock()

    @staticmethod
    def _copier_base(source: Path, destination: Path) -> None:
        if not source.is_file():
            raise FileNotFoundError(f"Base SQLite introuvable : {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(str(source))) as connexion_source:
            with closing(sqlite3.connect(str(destination))) as connexion_destination:
                connexion_source.backup(connexion_destination)
                resultat = connexion_destination.execute("PRAGMA integrity_check").fetchone()
                if not resultat or resultat[0] != "ok":
                    raise ValueError(f"La base SQLite {source.name} est invalide.")

    def creer_sauvegarde(self, appliquer_retention: bool = True) -> dict:
        with self._verrou:
            return self._creer_sauvegarde(appliquer_retention)

    def _creer_sauvegarde(self, appliquer_retention: bool) -> dict:
        self.dossier_sauvegardes.mkdir(parents=True, exist_ok=True)
        identifiant = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        dossier_temporaire = self.dossier_sauvegardes / f".tmp-{identifiant}"
        dossier_final = self.dossier_sauvegardes / identifiant
        dossier_temporaire.mkdir()
        try:
            tailles = {}
            for nom, source in self.chemins_bases.items():
                destination = dossier_temporaire / nom
                self._copier_base(source, destination)
                tailles[nom] = destination.stat().st_size

            manifeste = {
                "version": 1,
                "identifiant": identifiant,
                "cree_le": datetime.now(timezone.utc).isoformat(),
                "bases": list(NOMS_BASES),
                "tailles_octets": tailles,
            }
            (dossier_temporaire / "manifest.json").write_text(
                json.dumps(manifeste, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            dossier_temporaire.replace(dossier_final)
        except Exception:
            shutil.rmtree(dossier_temporaire, ignore_errors=True)
            raise

        if appliquer_retention:
            self._appliquer_retention()
        return self._decrire_sauvegarde(dossier_final, manifeste)

    def _lire_manifeste(self, identifiant: str) -> tuple[Path, dict]:
        if not FORMAT_IDENTIFIANT.fullmatch(identifiant):
            raise ValueError("Identifiant de sauvegarde invalide.")
        dossier = self.dossier_sauvegardes / identifiant
        manifeste_path = dossier / "manifest.json"
        try:
            manifeste = json.loads(manifeste_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as erreur:
            raise ValueError("Sauvegarde introuvable ou manifeste illisible.") from erreur
        if not isinstance(manifeste, dict):
            raise ValueError("Le manifeste de cette sauvegarde est invalide.")
        bases = manifeste.get("bases")
        tailles = manifeste.get("tailles_octets")
        if (
            manifeste.get("version") != 1
            or manifeste.get("identifiant") != identifiant
            or not isinstance(manifeste.get("cree_le"), str)
            or not isinstance(bases, list)
            or any(not isinstance(nom, str) for nom in bases)
            or set(bases) != set(NOMS_BASES)
            or not isinstance(tailles, dict)
            or set(tailles) != set(NOMS_BASES)
            or any(not isinstance(tailles[nom], int) or tailles[nom] < 0 for nom in NOMS_BASES)
        ):
            raise ValueError("Le manifeste de cette sauvegarde est invalide.")
        for nom in NOMS_BASES:
            fichier = dossier / nom
            if not fichier.is_file() or fichier.resolve().parent != dossier.resolve():
                raise ValueError(f"Fichier de sauvegarde manquant : {nom}")
        return dossier, manifeste

    @staticmethod
    def _decrire_sauvegarde(dossier: Path, manifeste: dict) -> dict:
        tailles = manifeste.get("tailles_octets", {})
        return {
            "identifiant": manifeste["identifiant"],
            "cree_le": manifeste["cree_le"],
            "tailles_octets": tailles,
            "taille_totale_octets": sum(tailles.values()),
        }

    def lister_sauvegardes(self) -> list[dict]:
        if not self.dossier_sauvegardes.exists():
            return []
        sauvegardes = []
        for dossier in self.dossier_sauvegardes.iterdir():
            if not dossier.is_dir() or not FORMAT_IDENTIFIANT.fullmatch(dossier.name):
                continue
            try:
                _, manifeste = self._lire_manifeste(dossier.name)
                sauvegardes.append(self._decrire_sauvegarde(dossier, manifeste))
            except ValueError:
                logger.warning("Sauvegarde ignorée car invalide : %s", dossier.name)
        return sorted(sauvegardes, key=lambda item: item["identifiant"], reverse=True)

    def _appliquer_retention(self) -> None:
        sauvegardes = self.lister_sauvegardes()
        for ancienne in sauvegardes[self.retention:]:
            dossier = self.dossier_sauvegardes / ancienne["identifiant"]
            shutil.rmtree(dossier)

    def restaurer(self, identifiant: str) -> dict:
        with self._verrou:
            return self._restaurer(identifiant)

    def _restaurer(self, identifiant: str) -> dict:
        dossier_source, _ = self._lire_manifeste(identifiant)
        # Toujours conserver l'état courant avant d'écraser une base.
        sauvegarde_securite = self.creer_sauvegarde(appliquer_retention=False)
        temporaires: dict[str, Path] = {}
        try:
            for nom in NOMS_BASES:
                cible = self.chemins_bases[nom]
                cible.parent.mkdir(parents=True, exist_ok=True)
                temporaire = cible.with_name(f".{cible.name}.{identifiant}.restore")
                if temporaire.exists():
                    temporaire.unlink()
                self._copier_base(dossier_source / nom, temporaire)
                temporaires[nom] = temporaire

            try:
                for nom in NOMS_BASES:
                    self._copier_base(temporaires[nom], self.chemins_bases[nom])
            except Exception:
                # En cas d'échec partiel, revenir à la sauvegarde de sécurité.
                dossier_securite, _ = self._lire_manifeste(sauvegarde_securite["identifiant"])
                for nom in NOMS_BASES:
                    self._copier_base(dossier_securite / nom, self.chemins_bases[nom])
                raise
        finally:
            for temporaire in temporaires.values():
                temporaire.unlink(missing_ok=True)

        self._appliquer_retention()
        return {
            "identifiant_restaure": identifiant,
            "sauvegarde_securite": sauvegarde_securite["identifiant"],
            "bases_restaurees": list(NOMS_BASES),
        }
