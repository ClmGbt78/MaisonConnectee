import hashlib
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class GestionnaireCopieUSB:
    """Copie les sauvegardes locales vers une clé USB explicitement montée."""

    def __init__(self, point_montage: Path, dossier_source: Path):
        self.point_montage = Path(point_montage)
        self.dossier_source = Path(dossier_source)

    @staticmethod
    def _empreinte(fichier: Path) -> str:
        empreinte = hashlib.sha256()
        with fichier.open("rb") as flux:
            for bloc in iter(lambda: flux.read(1024 * 1024), b""):
                empreinte.update(bloc)
        return empreinte.hexdigest()

    def copier_sauvegardes(self) -> dict:
        # Path.is_mount() évite d'écrire sur le répertoire vide du système
        # lorsque la clé USB n'est pas montée.
        if not self.point_montage.is_dir() or not self.point_montage.is_mount():
            raise RuntimeError(
                f"Clé USB absente : {self.point_montage} n'est pas un point de montage."
            )
        if not self.dossier_source.is_dir():
            return {"copiees": 0, "ignorees": 0}

        destination = self.point_montage / "MaisonConnectee" / "backups"
        destination.mkdir(parents=True, exist_ok=True)
        copiees = 0
        ignorees = 0

        for source in sorted(self.dossier_source.iterdir()):
            if not source.is_dir() or not source.name[:8].isdigit() or (source / "manifest.json").is_file() is False:
                continue
            cible = destination / source.name
            if cible.exists():
                ignorees += 1
                continue

            temporaire = destination / f".tmp-{source.name}"
            if temporaire.exists():
                shutil.rmtree(temporaire)
            try:
                shutil.copytree(source, temporaire)
                fichiers = [p for p in source.iterdir() if p.is_file()]
                if any(
                    not (temporaire / fichier.name).is_file()
                    or self._empreinte(fichier) != self._empreinte(temporaire / fichier.name)
                    for fichier in fichiers
                ):
                    raise OSError(f"Vérification SHA-256 échouée pour {source.name}.")
                temporaire.rename(cible)
                copiees += 1
            except Exception:
                shutil.rmtree(temporaire, ignore_errors=True)
                raise

        logger.info("Copie USB terminée : %s nouvelle(s) sauvegarde(s).", copiees)
        return {"copiees": copiees, "ignorees": ignorees}
