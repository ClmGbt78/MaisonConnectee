import { useEffect, useState } from "react";
import Plan3D from "./components/Plan3D";
import "./App.css";
import { apiFetch, setAccessToken } from "./api";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

type SystemMetrics = {
  cpu: {
    utilisation_pct: number;
  };
  ram: {
    utilisation_pct: number;
    utilisee_gb: number;
    totale_gb: number;
  };
  disque: {
    utilisation_pct: number;
    utilise_gb: number;
    libre_gb: number;
    total_gb: number;
  };
  heure_utc: string;
};

type PieceMaison = { id: string; nom: string; description: string; couleur: string; nombre_appareils: number };

type Appareil = {
  id: string;
  nom: string;
  piece: string;
  type: string;
  allume: boolean;
  capacites?: string[];
  luminosite?: number | null;
  temperature_couleur?: number | null;
  couleur?: string | null;
};

type SceneLumineuse = {
  id: string;
  nom: string;
  luminosite: number;
  temperature_couleur: number;
  couleur: string;
};

type Automatisation = {
  id: string; nom: string; active: boolean; heure: string; jours: number[];
  scene_id: string; piece: string | null; extinction_minutes: number | null;
};
type Capteur = {
  id: string; nom: string; piece: string;
  mesure: { type_mesure: string; valeur: number; mise_a_jour: string } | null;
};

type PortSerie = {
  port: string;
  description: string;
  fabricant: string | null;
  identifiant_usb: string | null;
};

type ConfigurationSerieCapteur = {
  capteur_id: string;
  port: string;
  debit: number;
  protocole: string;
};
type AutomatisationConditionnelle = {
  id: string; nom: string; active: boolean; capteur_id: string; condition: string;
  seuil: number | null; duree_absence: number | null; scene_id: string | null; piece: string | null;
};

const JOURS_SEMAINE = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];

type HistoriqueIndicateur = {
  heure_utc: string;
  cpu_pct: number;
  ram_pct: number;
  disque_pct: number;
};

const modules = [
  {
    icon: "⌂",
    name: "Domotique",
    description: "Gestion de la maison",
    status: "En préparation",
    color: "blue",
  },
  {
    icon: "✧",
    name: "Assistant IA",
    description: "Votre assistant personnel",
    status: "Non configuré",
    color: "purple",
  },
  {
    icon: "◉",
    name: "Éclairage RGB",
    description: "Contrôle du PC et du clavier",
    status: "En préparation",
    color: "pink",
  },
];

type SystemStatus = {
  centrale: string;
  heure_utc: string;
  modules: {
    domotique: string;
    intelligence_artificielle: string;
    rgb: string;
  };
};

function App() {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [utilisateurConnecte, setUtilisateurConnecte] = useState<{
    id: number;
    nom: string;
    email: string;
    role: string;
  } | null>(null);

  const [emailConnexion, setEmailConnexion] = useState("");
  const [motDePasseConnexion, setMotDePasseConnexion] = useState("");
  const [erreurConnexion, setErreurConnexion] = useState("");
  const [connexionEnCours, setConnexionEnCours] = useState(false);
  const [apiError, setApiError] = useState(false);
  const [pageActive, setPageActive] = useState("accueil");
  const [couleurRGB, setCouleurRGB] = useState("#845ef7");
  const [luminositeRGB, setLuminositeRGB] = useState(75);
  const [messageIA, setMessageIA] = useState("");
  const [messagesIA, setMessagesIA] = useState<
  { role: "user" | "assistant"; content: string }[]
  >([
    {
      role: "assistant",
      content:
        "Bonjour ! Je suis l'assistant de Maison Connectée. Je pourrai bientôt t'aider à comprendre et contrôler ta maison. Que souhaites-tu faire ?",
    },
  ]);

  const [modeRGBActif, setModeRGBActif] = useState("");
  const [chargementRGB, setChargementRGB] = useState(false);
  const [erreurRGB, setErreurRGB] = useState("");
  const appliquerModeRGB = async (mode: string) => {
    setChargementRGB(true);
    setErreurRGB("");

    try {
      const response = await apiFetch(
        `/api/rgb/mode/${mode}`,
        { method: "POST" }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Impossible de modifier l'éclairage");
      }

      setModeRGBActif(mode);
    } catch (error) {
      setErreurRGB(
        error instanceof Error ? error.message : "Erreur de connexion à l'API"
      );
    } finally {
      setChargementRGB(false);
    }
  };
  const [connexionRGB, setConnexionRGB] = useState<
    "verification" | "connecte" | "deconnecte"
    >("verification");
    useEffect(() => {
    let actif = true;

    const verifierConnexionRGB = async () => {
      try {
        const response = await apiFetch(
         "/api/rgb/modes"
        );

        if (!response.ok) {
          throw new Error("API indisponible");
        }

        if (actif) {
          setConnexionRGB("connecte");
        } 
      } catch {
        if (actif) {
          setConnexionRGB("deconnecte");
        }
      }
    };

    verifierConnexionRGB();

    return () => {
      actif = false;
    };
  }, []);


  useEffect(() => {
    if (!utilisateurConnecte) return;
    let active = true;

    async function loadSystemStatus() {
      try {
        const response = await apiFetch(
          "/api/systeme"
        );

        if (!response.ok) {
          throw new Error("Erreur de l'API");
        }

        const data: SystemStatus = await response.json();

        if (active) {
          setSystemStatus(data);
          setApiError(false);
        }
      } catch {
        if (active) {
          setApiError(true);
        }
      }
    }

    void loadSystemStatus();

    const interval = window.setInterval(() => {
      void loadSystemStatus();
    }, 10000);

    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [utilisateurConnecte]);

  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [metricsError, setMetricsError] = useState(false);
  const [historique, setHistorique] = useState<HistoriqueIndicateur[]>([]);
  const [erreurHistorique, setErreurHistorique] = useState(false);
  const [maintenant, setMaintenant] = useState<number | null>(null);
  const [periodeHistorique, setPeriodeHistorique] =
    useState<15 | 60 | 1440>(60);

  useEffect(() => {
    const intervalleHorloge = window.setInterval(() => {
      setMaintenant(Date.now());
    }, 5000);

    return () => {
      window.clearInterval(intervalleHorloge);
    };
  }, []);
  const historiqueGraphique = historique
    .filter((mesure) => {
      if (maintenant === null) {
        return false;
      }

      const heureMesure = new Date(mesure.heure_utc).getTime();
      const dureeMs = periodeHistorique * 60 * 1000;

      return heureMesure >= maintenant - dureeMs;
    })
    .map((mesure) => ({
      ...mesure,
      heure: new Date(mesure.heure_utc).toLocaleTimeString("fr-FR", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }),
    }));

  useEffect(() => {
    if (!utilisateurConnecte) return;
    let active = true;

    async function loadMetrics() {
      try {
        const response = await apiFetch(
          "/api/systeme/indicateurs"
        );

        if (!response.ok) {
          throw new Error("Impossible de récupérer les indicateurs");
        }

        const data: SystemMetrics = await response.json();

        if (active) {
          setMetrics(data);
          setMetricsError(false);
        }
      } catch {
        if (active) {
          setMetricsError(true);
        }
      }
    }

    void loadMetrics();

    const interval = window.setInterval(() => {
      void loadMetrics();
    }, 5000);

    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [utilisateurConnecte]);

  useEffect(() => {
    if (!utilisateurConnecte) return;
    let actif = true;

    async function chargerHistorique() {
      try {
        const response = await apiFetch(
          "/api/systeme/historique"
        );

        if (!response.ok) {
          throw new Error("Impossible de récupérer l'historique");
        }

        const data: HistoriqueIndicateur[] = await response.json();

        if (actif) {
          setHistorique(data);
          setErreurHistorique(false);
        }
      } catch {
        if (actif) {
          setErreurHistorique(true);
        }
      }
    }

    void chargerHistorique();

    const interval = window.setInterval(() => {
      void chargerHistorique();
    }, 5000);

    return () => {
      actif = false;
      window.clearInterval(interval);
    };
  }, [utilisateurConnecte]);

  const [appareils, setAppareils] = useState<Appareil[]>([]);
  const [pieces, setPieces] = useState<PieceMaison[]>([]);
  const [nomNouvellePiece, setNomNouvellePiece] = useState("");
  const [descriptionNouvellePiece, setDescriptionNouvellePiece] = useState("");
  const [couleurNouvellePiece, setCouleurNouvellePiece] = useState("#365B78");
  const [brouillonsPieces, setBrouillonsPieces] = useState<Record<string, { nom: string; description: string; couleur: string }>>({});
  const [pieceEnCours, setPieceEnCours] = useState<string | null>(null);
  const [erreurPieces, setErreurPieces] = useState("");
  const [erreurDomotique, setErreurDomotique] = useState(false);
  const [appareilsEnCours, setAppareilsEnCours] = useState<string[]>([]);
  const [nomNouvelAppareil, setNomNouvelAppareil] = useState("");
  const [pieceNouvelAppareil, setPieceNouvelAppareil] = useState("");
  const [typeNouvelAppareil, setTypeNouvelAppareil] = useState("lumiere");
  const [ajoutEnCours, setAjoutEnCours] = useState(false);
  const [messageDomotique, setMessageDomotique] = useState("");
  const [scenes, setScenes] = useState<SceneLumineuse[]>([]);
  const [nomScene, setNomScene] = useState("");
  const [luminositeScene, setLuminositeScene] = useState(70);
  const [temperatureScene, setTemperatureScene] = useState(3000);
  const [couleurScene, setCouleurScene] = useState("#FFB36B");
  const [sceneEnCours, setSceneEnCours] = useState(false);
  const [automatisations, setAutomatisations] = useState<Automatisation[]>([]);
  const [nomAutomatisation, setNomAutomatisation] = useState("");
  const [heureAutomatisation, setHeureAutomatisation] = useState("20:00");
  const [joursAutomatisation, setJoursAutomatisation] = useState<number[]>([1, 2, 3, 4, 5]);
  const [sceneAutomatisation, setSceneAutomatisation] = useState("");
  const [pieceAutomatisation, setPieceAutomatisation] = useState("");
  const [extinctionAutomatisation, setExtinctionAutomatisation] = useState("");
  const [automatisationEnCours, setAutomatisationEnCours] = useState(false);
  const [capteurs, setCapteurs] = useState<Capteur[]>([]);
  const [conditions, setConditions] = useState<AutomatisationConditionnelle[]>([]);
  const [portsSerie, setPortsSerie] = useState<PortSerie[]>([]);
  const [configurationsSerie, setConfigurationsSerie] = useState<ConfigurationSerieCapteur[]>([]);
  const [portsSerieErreur, setPortsSerieErreur] = useState("");
  const [configurationSerieEnCours, setConfigurationSerieEnCours] = useState<string | null>(null);
  const [portsSerieDisponibles, setPortsSerieDisponibles] = useState(true);
  const [portsSelectionnes, setPortsSelectionnes] = useState<Record<string, string>>({});
  const [debitsSelectionnes, setDebitsSelectionnes] = useState<Record<string, number>>({});
  const [nomCondition, setNomCondition] = useState("");
  const [capteurCondition, setCapteurCondition] = useState("");
  const [typeCondition, setTypeCondition] = useState("luminosite_inferieure");
  const [seuilCondition, setSeuilCondition] = useState(30);
  const [dureeAbsenceCondition, setDureeAbsenceCondition] = useState(15);
  const [sceneCondition, setSceneCondition] = useState("");
  const [pieceCondition, setPieceCondition] = useState("");

  async function chargerAppareils() {
    try {
      const response = await apiFetch(
        "/api/domotique/appareils"
      );

      if (!response.ok) {
        throw new Error("Erreur de récupération des appareils");
      }

      const data: Appareil[] = await response.json();
      setAppareils(data);
      setErreurDomotique(false);
    } catch {
      setErreurDomotique(true);
    }
  }

  async function chargerPieces() {
    try {
      const response = await apiFetch("/api/domotique/pieces");
      if (!response.ok) throw new Error("Impossible de charger les pièces.");
      const data: PieceMaison[] = await response.json();
      setPieces(data);
      setBrouillonsPieces((anciens) => {
        const suivants = { ...anciens };
        data.forEach((piece) => {
          if (!suivants[piece.id]) suivants[piece.id] = { nom: piece.nom, description: piece.description, couleur: piece.couleur };
        });
        Object.keys(suivants).forEach((id) => { if (!data.some((piece) => piece.id === id)) delete suivants[id]; });
        return suivants;
      });
      setErreurPieces("");
    } catch (erreur) {
      setErreurPieces(erreur instanceof Error ? erreur.message : "Erreur de chargement des pièces.");
    }
  }

  useEffect(() => {
    if (!utilisateurConnecte) return;
    const timeout = window.setTimeout(() => void chargerPieces(), 0);
    return () => window.clearTimeout(timeout);
  }, [utilisateurConnecte]);

  async function creerPiece(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPieceEnCours("nouvelle");
    setErreurPieces("");
    try {
      const response = await apiFetch("/api/domotique/pieces", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nom: nomNouvellePiece.trim(), description: descriptionNouvellePiece.trim(), couleur: couleurNouvellePiece }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Impossible de créer la pièce.");
      setPieces((items) => [...items, data].sort((a, b) => a.nom.localeCompare(b.nom, "fr")));
      setBrouillonsPieces((items) => ({ ...items, [data.id]: { nom: data.nom, description: data.description, couleur: data.couleur } }));
      setNomNouvellePiece("");
      setDescriptionNouvellePiece("");
      setMessageDomotique("Pièce créée.");
    } catch (erreur) {
      setErreurPieces(erreur instanceof Error ? erreur.message : "Erreur de création.");
    } finally { setPieceEnCours(null); }
  }

  async function enregistrerPiece(piece: PieceMaison) {
    const brouillon = brouillonsPieces[piece.id] ?? { nom: piece.nom, description: piece.description, couleur: piece.couleur };
    setPieceEnCours(piece.id);
    setErreurPieces("");
    try {
      const response = await apiFetch(`/api/domotique/pieces/${encodeURIComponent(piece.id)}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nom: brouillon.nom.trim(), description: brouillon.description.trim(), couleur: brouillon.couleur }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Impossible de modifier la pièce.");
      setPieces((items) => items.map((item) => item.id === piece.id ? data : item).sort((a, b) => a.nom.localeCompare(b.nom, "fr")));
      setBrouillonsPieces((items) => ({ ...items, [piece.id]: { nom: data.nom, description: data.description, couleur: data.couleur } }));
      await chargerAppareils();
      setMessageDomotique("Pièce mise à jour.");
    } catch (erreur) {
      setErreurPieces(erreur instanceof Error ? erreur.message : "Erreur de modification.");
    } finally { setPieceEnCours(null); }
  }

  async function supprimerPiece(piece: PieceMaison) {
    if (!window.confirm(`Supprimer la pièce « ${piece.nom} » ?`)) return;
    setPieceEnCours(piece.id);
    setErreurPieces("");
    try {
      const response = await apiFetch(`/api/domotique/pieces/${encodeURIComponent(piece.id)}`, { method: "DELETE" });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Impossible de supprimer la pièce.");
      }
      setPieces((items) => items.filter((item) => item.id !== piece.id));
      setMessageDomotique("Pièce supprimée.");
    } catch (erreur) {
      setErreurPieces(erreur instanceof Error ? erreur.message : "Erreur de suppression.");
    } finally { setPieceEnCours(null); }
  }

  useEffect(() => {
    if (!utilisateurConnecte) return;
    const chargementInitial = window.setTimeout(() => {
      void chargerAppareils();
    }, 0);

    const intervalle = window.setInterval(() => {
      void chargerAppareils();
    }, 3000);

    return () => {
      window.clearTimeout(chargementInitial);
      window.clearInterval(intervalle);
    };
  }, [utilisateurConnecte]);


  async function chargerScenes() {
    try {
      const response = await apiFetch("/api/domotique/scenes");
      if (!response.ok) throw new Error("Impossible de charger les scènes");
      setScenes(await response.json());
    } catch {
      setMessageDomotique("Impossible de charger les scènes lumineuses.");
    }
  }

  useEffect(() => {
    if (!utilisateurConnecte) return;
    const timeout = window.setTimeout(() => void chargerScenes(), 0);
    return () => window.clearTimeout(timeout);
  }, [utilisateurConnecte]);

  async function creerScene(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSceneEnCours(true);
    setMessageDomotique("");
    try {
      const response = await apiFetch("/api/domotique/scenes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nom: nomScene.trim(), luminosite: luminositeScene, temperature_couleur: temperatureScene, couleur: couleurScene }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Impossible d'enregistrer la scène.");
      setScenes((anciennes) => [...anciennes.filter((scene) => scene.id !== data.id), data]);
      setNomScene("");
      setMessageDomotique("Scène lumineuse enregistrée.");
    } catch (erreur) {
      setMessageDomotique(erreur instanceof Error ? erreur.message : "Erreur lors de l'enregistrement.");
    } finally { setSceneEnCours(false); }
  }

  async function appliquerScene(scene: SceneLumineuse) {
    setSceneEnCours(true);
    setMessageDomotique("");
    try {
      const response = await apiFetch(`/api/domotique/scenes/${encodeURIComponent(scene.id)}/appliquer`, { method: "POST" });
      const data: Appareil[] = await response.json();
      if (!response.ok) throw new Error((data as unknown as {detail?: string}).detail || "Impossible d'appliquer la scène.");
      setAppareils((anciennes) => anciennes.map((appareil) => data.find((maj) => maj.id === appareil.id) ?? appareil));
      setMessageDomotique(`Ambiance « ${scene.nom} » appliquée.`);
    } catch (erreur) {
      setMessageDomotique(erreur instanceof Error ? erreur.message : "Erreur lors de l'application de la scène.");
      void chargerAppareils();
    } finally { setSceneEnCours(false); }
  }

  async function supprimerScene(scene: SceneLumineuse) {
    if (!window.confirm(`Supprimer la scène « ${scene.nom} » ?`)) return;
    setSceneEnCours(true);
    try {
      const response = await apiFetch(`/api/domotique/scenes/${encodeURIComponent(scene.id)}`, { method: "DELETE" });
      if (!response.ok) { const data = await response.json(); throw new Error(data.detail || "Impossible de supprimer la scène."); }
      setScenes((anciennes) => anciennes.filter((element) => element.id !== scene.id));
      setMessageDomotique("Scène supprimée.");
    } catch (erreur) {
      setMessageDomotique(erreur instanceof Error ? erreur.message : "Erreur de suppression.");
    } finally { setSceneEnCours(false); }
  }

  async function chargerAutomatisations() {
    try {
      const response = await apiFetch("/api/domotique/automatisations");
      if (!response.ok) throw new Error("Chargement impossible");
      setAutomatisations(await response.json());
    } catch {
      setMessageDomotique("Impossible de charger les automatisations.");
    }
  }

  useEffect(() => {
    if (!utilisateurConnecte) return;
    const timeout = window.setTimeout(() => void chargerAutomatisations(), 0);
    return () => window.clearTimeout(timeout);
  }, [utilisateurConnecte]);

  async function creerAutomatisation(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!sceneAutomatisation || joursAutomatisation.length === 0) return;
    setAutomatisationEnCours(true);
    try {
      const response = await apiFetch("/api/domotique/automatisations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nom: nomAutomatisation.trim(), heure: heureAutomatisation,
          jours: joursAutomatisation, scene_id: sceneAutomatisation,
          piece: pieceAutomatisation || null,
          extinction_minutes: extinctionAutomatisation ? Number(extinctionAutomatisation) : null,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Création impossible.");
      setAutomatisations((items) => [...items, data].sort((a, b) => a.heure.localeCompare(b.heure)));
      setNomAutomatisation("");
      setMessageDomotique("Automatisation enregistrée.");
    } catch (erreur) {
      setMessageDomotique(erreur instanceof Error ? erreur.message : "Erreur de création.");
    } finally { setAutomatisationEnCours(false); }
  }

  async function basculerAutomatisation(item: Automatisation) {
    setAutomatisationEnCours(true);
    try {
      const response = await apiFetch(`/api/domotique/automatisations/${item.id}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active: !item.active }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Modification impossible.");
      setAutomatisations((items) => items.map((current) => current.id === item.id ? data : current));
    } catch (erreur) {
      setMessageDomotique(erreur instanceof Error ? erreur.message : "Erreur de modification.");
    } finally { setAutomatisationEnCours(false); }
  }

  async function supprimerAutomatisation(item: Automatisation) {
    if (!window.confirm(`Supprimer l'automatisation « ${item.nom} » ?`)) return;
    setAutomatisationEnCours(true);
    try {
      const response = await apiFetch(`/api/domotique/automatisations/${item.id}`, { method: "DELETE" });
      if (!response.ok) throw new Error("Suppression impossible.");
      setAutomatisations((items) => items.filter((current) => current.id !== item.id));
      setMessageDomotique("Automatisation supprimée.");
    } catch (erreur) {
      setMessageDomotique(erreur instanceof Error ? erreur.message : "Erreur de suppression.");
    } finally { setAutomatisationEnCours(false); }
  }

  async function chargerCapteursEtConditions() {
    try {
      const [capteursResponse, conditionsResponse] = await Promise.all([
        apiFetch("/api/domotique/automatisations/capteurs"),
        apiFetch("/api/domotique/automatisations/conditionnelles"),
      ]);
      if (!capteursResponse.ok || !conditionsResponse.ok) throw new Error("Chargement impossible");
      setCapteurs(await capteursResponse.json());
      setConditions(await conditionsResponse.json());
    } catch {
      setMessageDomotique("Impossible de charger les capteurs et automatisations conditionnelles.");
    }
  }

  useEffect(() => {
    if (!utilisateurConnecte) return;
    const timeout = window.setTimeout(() => void chargerCapteursEtConditions(), 0);
    const interval = window.setInterval(() => void chargerCapteursEtConditions(), 5000);
    return () => {
      window.clearTimeout(timeout);
      window.clearInterval(interval);
    };
  }, [utilisateurConnecte]);

  async function chargerConfigurationsSerie() {
    try {
      const [portsResponse, configurationsResponse] = await Promise.all([
        apiFetch("/api/domotique/automatisations/ports-serie"),
        apiFetch("/api/domotique/automatisations/capteurs/configurations-serie"),
      ]);
      if (!configurationsResponse.ok) throw new Error("Impossible de charger les associations série.");
      setConfigurationsSerie(await configurationsResponse.json());
      if (!portsResponse.ok) {
        const erreur = await portsResponse.json().catch(() => ({}));
        throw new Error(erreur.detail || "Impossible de détecter les ports série.");
      }
      const ports: PortSerie[] = await portsResponse.json();
      setPortsSerie(ports);
      setPortsSerieDisponibles(true);
      setPortsSerieErreur("");
    } catch (erreur) {
      setPortsSerieDisponibles(false);
      setPortsSerieErreur(erreur instanceof Error ? erreur.message : "Erreur de découverte des ports série.");
    }
  }

  useEffect(() => {
    if (!utilisateurConnecte) return;
    const timeout = window.setTimeout(() => void chargerConfigurationsSerie(), 0);
    const interval = window.setInterval(() => void chargerConfigurationsSerie(), 10000);
    return () => {
      window.clearTimeout(timeout);
      window.clearInterval(interval);
    };
  }, [utilisateurConnecte]);

  async function enregistrerConfigurationSerie(capteur: Capteur) {
    const port = portsSelectionnes[capteur.id] ?? configurationsSerie.find((item) => item.capteur_id === capteur.id)?.port ?? "";
    const debit = debitsSelectionnes[capteur.id] ?? configurationsSerie.find((item) => item.capteur_id === capteur.id)?.debit ?? 9600;
    if (!port) {
      setPortsSerieErreur("Sélectionne un port série pour ce capteur.");
      return;
    }
    setConfigurationSerieEnCours(capteur.id);
    setPortsSerieErreur("");
    try {
      const response = await apiFetch(`/api/domotique/automatisations/capteurs/${encodeURIComponent(capteur.id)}/configuration-serie`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ port, debit }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Enregistrement impossible.");
      setConfigurationsSerie((items) => [...items.filter((item) => item.capteur_id !== capteur.id), data]);
      setMessageDomotique(`Association ${data.port} enregistrée pour « ${capteur.nom} ».`);
    } catch (erreur) {
      setPortsSerieErreur(erreur instanceof Error ? erreur.message : "Erreur d'enregistrement.");
    } finally {
      setConfigurationSerieEnCours(null);
    }
  }

  async function supprimerConfigurationSerie(capteur: Capteur) {
    if (!window.confirm(`Retirer l'association série de « ${capteur.nom} » ?`)) return;
    setConfigurationSerieEnCours(capteur.id);
    setPortsSerieErreur("");
    try {
      const response = await apiFetch(`/api/domotique/automatisations/capteurs/${encodeURIComponent(capteur.id)}/configuration-serie`, { method: "DELETE" });
      if (!response.ok && response.status !== 204) {
        const data = await response.json();
        throw new Error(data.detail || "Suppression impossible.");
      }
      setConfigurationsSerie((items) => items.filter((item) => item.capteur_id !== capteur.id));
      setPortsSelectionnes((items) => { const next = { ...items }; delete next[capteur.id]; return next; });
      setDebitsSelectionnes((items) => { const next = { ...items }; delete next[capteur.id]; return next; });
      setMessageDomotique(`Association série retirée pour « ${capteur.nom} ».`);
    } catch (erreur) {
      setPortsSerieErreur(erreur instanceof Error ? erreur.message : "Erreur de suppression.");
    } finally {
      setConfigurationSerieEnCours(null);
    }
  }

  async function simulerCapteur(capteur: Capteur, type_mesure: "luminosite" | "presence", valeur: number) {
    try {
      const response = await apiFetch(`/api/domotique/automatisations/capteurs/${encodeURIComponent(capteur.id)}/mesure`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type_mesure, valeur }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Mise à jour du capteur impossible.");
      setCapteurs((items) => items.map((item) => item.id === capteur.id ? { ...item, mesure: data } : item));
      setMessageDomotique("Valeur de capteur simulée enregistrée.");
    } catch (erreur) {
      setMessageDomotique(erreur instanceof Error ? erreur.message : "Erreur de simulation.");
    }
  }

  async function creerConditionnelle(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAutomatisationEnCours(true);
    try {
      const response = await apiFetch("/api/domotique/automatisations/conditionnelles", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nom: nomCondition.trim(), capteur_id: capteurCondition, condition: typeCondition,
          seuil: typeCondition === "luminosite_inferieure" ? seuilCondition : null,
          duree_absence: typeCondition === "absence_prolongee" ? dureeAbsenceCondition : null,
          scene_id: typeCondition === "absence_prolongee" ? null : sceneCondition,
          piece: pieceCondition || null,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Création impossible.");
      setConditions((items) => [...items, data]);
      setNomCondition("");
      setMessageDomotique("Automatisation conditionnelle créée.");
    } catch (erreur) {
      setMessageDomotique(erreur instanceof Error ? erreur.message : "Erreur de création.");
    } finally { setAutomatisationEnCours(false); }
  }

  async function basculerConditionnelle(item: AutomatisationConditionnelle) {
    const response = await apiFetch(`/api/domotique/automatisations/conditionnelles/${item.id}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active: !item.active }),
    });
    const data = await response.json();
    if (response.ok) setConditions((items) => items.map((current) => current.id === item.id ? data : current));
    else setMessageDomotique(data.detail || "Modification impossible.");
  }

  async function supprimerConditionnelle(item: AutomatisationConditionnelle) {
    if (!window.confirm(`Supprimer la règle « ${item.nom} » ?`)) return;
    const response = await apiFetch(`/api/domotique/automatisations/conditionnelles/${item.id}`, { method: "DELETE" });
    if (response.ok) setConditions((items) => items.filter((current) => current.id !== item.id));
    else setMessageDomotique("Suppression impossible.");
  }

  async function basculerAppareil(appareil: Appareil) {
    if (appareilsEnCours.includes(appareil.id)) {
      return;
    }

    setAppareilsEnCours((anciens) => [...anciens, appareil.id]);

    try {
      const response = await apiFetch(
        `/api/domotique/appareils/${appareil.id}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            allume: !appareil.allume,
          }),
        }
      );

      if (!response.ok) {
        throw new Error("La commande a échoué");
      }

      const appareilMisAJour: Appareil = await response.json();

      setAppareils((anciens) =>
        anciens.map((element) =>
          element.id === appareilMisAJour.id
            ? appareilMisAJour
            : element
        )
      );

      setErreurDomotique(false);
    } catch {
      setErreurDomotique(true);
    } finally {
      setAppareilsEnCours((anciens) =>
        anciens.filter((id) => id !== appareil.id)
      );
    }
  }

  async function reglerLuminosite(appareil: Appareil, luminosite: number) {
    if (appareilsEnCours.includes(appareil.id)) return;
    setAppareilsEnCours((anciens) => [...anciens, appareil.id]);
    try {
      const response = await apiFetch(
        `/api/domotique/appareils/${encodeURIComponent(appareil.id)}/luminosite`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ luminosite }),
        }
      );
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Impossible de régler la luminosité.");
      const appareilMisAJour: Appareil = data;
      setAppareils((anciens) => anciens.map((element) =>
        element.id === appareilMisAJour.id ? appareilMisAJour : element
      ));
      setErreurDomotique(false);
    } catch (erreur) {
      setMessageDomotique(erreur instanceof Error ? erreur.message : "Erreur de réglage de la luminosité.");
      setErreurDomotique(true);
      void chargerAppareils();
    } finally {
      setAppareilsEnCours((anciens) => anciens.filter((id) => id !== appareil.id));
    }
  }

  async function reglerTemperatureCouleur(appareil: Appareil, temperature_couleur: number) {
    if (appareilsEnCours.includes(appareil.id)) return;
    setAppareilsEnCours((anciens) => [...anciens, appareil.id]);
    try {
      const response = await apiFetch(
        `/api/domotique/appareils/${encodeURIComponent(appareil.id)}/temperature-couleur`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ temperature_couleur }),
        }
      );
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Impossible de régler la température de couleur.");
      const appareilMisAJour: Appareil = data;
      setAppareils((anciens) => anciens.map((element) =>
        element.id === appareilMisAJour.id ? appareilMisAJour : element
      ));
      setErreurDomotique(false);
    } catch (erreur) {
      setMessageDomotique(erreur instanceof Error ? erreur.message : "Erreur de réglage de la température de couleur.");
      setErreurDomotique(true);
      void chargerAppareils();
    } finally {
      setAppareilsEnCours((anciens) => anciens.filter((id) => id !== appareil.id));
    }
  }


  async function reglerCouleur(appareil: Appareil, couleur: string) {
    if (appareilsEnCours.includes(appareil.id)) return;
    setAppareilsEnCours((anciens) => [...anciens, appareil.id]);
    try {
      const response = await apiFetch(
        `/api/domotique/appareils/${encodeURIComponent(appareil.id)}/couleur`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ couleur }),
        }
      );
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Impossible de régler la couleur.");
      const appareilMisAJour: Appareil = data;
      setAppareils((anciens) => anciens.map((element) =>
        element.id === appareilMisAJour.id ? appareilMisAJour : element
      ));
      setErreurDomotique(false);
    } catch (erreur) {
      setMessageDomotique(erreur instanceof Error ? erreur.message : "Erreur de réglage de la couleur.");
      setErreurDomotique(true);
      void chargerAppareils();
    } finally {
      setAppareilsEnCours((anciens) => anciens.filter((id) => id !== appareil.id));
    }
  }

  async function ajouterAppareil(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nom = nomNouvelAppareil.trim();
    const piece = pieceNouvelAppareil.trim();

    if (!nom || !piece) {
      setMessageDomotique("Le nom et la pièce sont obligatoires.");
      return;
    }

    const id = nom
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");

    if (!id) {
      setMessageDomotique("Choisis un nom d'appareil valide.");
      return;
    }

    setAjoutEnCours(true);
    setMessageDomotique("");

    try {
      const response = await apiFetch(
        "/api/domotique/appareils",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            id,
            nom,
            piece,
            type: typeNouvelAppareil,
          }),
        }
      );

      if (!response.ok) {
        const erreur = await response.json();
        throw new Error(
          erreur.detail || "Impossible d'ajouter cet appareil."
        );
      }

      await chargerAppareils();
      await chargerPieces();

      setNomNouvelAppareil("");
      setPieceNouvelAppareil("");
      setTypeNouvelAppareil("lumiere");
      setMessageDomotique("Appareil ajouté avec succès.");
    } catch (erreur) {
      setMessageDomotique(
        erreur instanceof Error
          ? erreur.message
          : "Une erreur est survenue pendant l'ajout."
      );
    } finally {
      setAjoutEnCours(false);
    }
  }


  async function supprimerAppareil(appareil: Appareil) {
    const confirmation = window.confirm(
      `Veux-tu vraiment supprimer « ${appareil.nom} » ?`
    );

    if (!confirmation) return;

    setMessageDomotique("");
    setAppareilsEnCours((anciens) => [...anciens, appareil.id]);

    try {
      const response = await apiFetch(
        `/api/domotique/appareils/${encodeURIComponent(appareil.id)}`,
        {
          method: "DELETE",
        }
      );

      if (!response.ok) {
        const erreur = await response.json().catch(() => null);
        throw new Error(
          erreur?.detail || "Impossible de supprimer cet appareil."
        );
      }

      setAppareils((anciens) =>
        anciens.filter((element) => element.id !== appareil.id)
      );
      await chargerPieces();

      setMessageDomotique(`« ${appareil.nom} » a été supprimé.`);
      setErreurDomotique(false);
    } catch (erreur) {
      setMessageDomotique(
        erreur instanceof Error
          ? erreur.message
          : "Une erreur est survenue pendant la suppression."
      );
    } finally {
      setAppareilsEnCours((anciens) =>
        anciens.filter((id) => id !== appareil.id)
      );
    }
  }

  const donneesSystemeObsoletes = apiError || metricsError;
  if (!utilisateurConnecte) {
    return (
      <main className="page-connexion">
        <form className="formulaire-connexion" onSubmit={connecter}>
          <h1>Maison Connectée</h1>
          <p>Connectez-vous à votre espace personnel.</p>

          <label htmlFor="email-connexion">Adresse e-mail</label>
          <input
            id="email-connexion"
            type="email"
            value={emailConnexion}
            onChange={(event) => setEmailConnexion(event.target.value)}
            required
          />

          <label htmlFor="mot-de-passe-connexion">Mot de passe</label>
          <input
            id="mot-de-passe-connexion"
            type="password"
            value={motDePasseConnexion}
            onChange={(event) => setMotDePasseConnexion(event.target.value)}
            required
          />

          {erreurConnexion && (
            <p className="erreur-connexion">{erreurConnexion}</p>
          )}

          <button type="submit" disabled={connexionEnCours}>
            {connexionEnCours ? "Connexion..." : "Se connecter"}
          </button>
        </form>
      </main>
    );
  }
  
  async function connecter(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
      setErreurConnexion("");
      setConnexionEnCours(true);

      try {
        const response = await apiFetch(
          "/api/comptes/connexion",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              email: emailConnexion.trim(),
              mot_de_passe: motDePasseConnexion,
            }),
          }
        );

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.detail || "Impossible de se connecter."
          );
        }

        setAccessToken(data.access_token);
        setUtilisateurConnecte(data.utilisateur);
        setMotDePasseConnexion("");
      } catch (erreur) {
        setErreurConnexion(
          erreur instanceof Error
            ? erreur.message
            : "Impossible de joindre le serveur."
        );
      } finally {
        setConnexionEnCours(false);
      }
  }

  function deconnecter() {
    setAccessToken(null);
    setUtilisateurConnecte(null);
    setEmailConnexion("");
    setMotDePasseConnexion("");
  }

  return (
    <main className="dashboard">
      {donneesSystemeObsoletes && (
        <div className="system-offline-banner" role="alert">
          <strong>⚠ Backend hors ligne ou données indisponibles</strong>

          <p>
            Les informations système ne sont plus actualisées.
            Les valeurs affichées peuvent être anciennes.
          </p>

          {metrics && (
            <p>
              Dernières données reçues :{" "}
              {new Date(metrics.heure_utc).toLocaleString("fr-FR")}
            </p>
         )}
        </div>
    )}
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">⌂</span>
          <span>Maison<span className="accent">Connectée</span></span>
        </div>

        <p className="menu-label">ESPACE PRINCIPAL</p>

        <nav>
          <a
            className={`nav-item ${pageActive === "accueil" ? "active" : ""}`}
            href="#accueil"
            onClick={(event) => {
              event.preventDefault();
              setPageActive("accueil");
            }}
          >
            ▦<span>Accueil</span>
          </a>

          <a
            className={`nav-item ${pageActive === "domotique" ? "active" : ""}`}
            href="#domotique"
            onClick={(event) => {
              event.preventDefault();
              setPageActive("domotique");
            }}
          >
            ⌂ <span>Domotique</span>
          </a>

          <a
            className={`nav-item ${pageActive === "plan3d" ? "active" : ""}`}
            href="#plan-3d"
            onClick={(event) => { event.preventDefault(); setPageActive("plan3d"); }}
          >
            ◫ <span>Plan 3D</span>
          </a>

          <a
            className={`nav-item ${pageActive === "assistant" ? "active" : ""}`}
            href="#assistant"
            onClick={(event) => {
              event.preventDefault();
              setPageActive("assistant");
            }}
          >
            ✧ <span>Assistant IA</span>
          </a>

          <a
            className={`nav-item ${pageActive === "rgb" ? "active" : ""}`}
            href="#rgb"
            onClick={(event) => {
              event.preventDefault();
              setPageActive("rgb");
            }}
          >
            ◉ <span>Éclairage RGB</span>
          </a>

          <a
            className={`nav-item ${pageActive === "systeme" ? "active" : ""}`}
            href="#systeme"
            onClick={(event) => {
              event.preventDefault();
              setPageActive("systeme");
            }}
          >
            ⚙ <span>Système</span>
          </a>
        </nav>

        <div className="sidebar-footer">
          <span className="status-dot" />
          <span>Centrale en développement</span>
        </div>
      </aside>

      <section className="main-content" id="accueil">
        <header className="topbar">
          <div>
            <p className="eyebrow">CENTRALE PERSONNELLE</p>
            <h1>
              {pageActive === "accueil"
                ? "Accueil"
                : pageActive === "domotique"
                  ? "Domotique"
                  : pageActive === "assistant"
                    ? "Assistant IA"
                    : pageActive === "rgb"
                      ? "Éclairage RGB"
                      : pageActive === "plan3d"
                        ? "Plan 3D"
                        : "Système"}
            </h1>
          </div>
          
      <div className="profile">
        <div
          className={`connection-status ${
            donneesSystemeObsoletes ? "offline" : "online"
          }`}
          role="status"
        >
          <span className="status-dot" />
          <span>
            {donneesSystemeObsoletes
              ? "Backend hors ligne"
              : "Backend connecté"}
          </span>
        </div>

  <div className="profile-avatar">MC</div>
  <div>
    <strong>{utilisateurConnecte.nom}</strong>
    <span>{utilisateurConnecte.email}</span>
  </div>
  <button type="button" className="logout-button" onClick={deconnecter}>
    Se déconnecter
  </button>
  </div>

        </header>

        {pageActive === "accueil" && (
        <>
        <section className="welcome">
          <div>
            <p className="eyebrow">VOTRE MAISON, EN UN SEUL ENDROIT</p>
            <h2>Bienvenue chez vous.</h2>
            <p className="welcome-description">
              Votre centrale se construit progressivement. Tous vos modules
              seront réunis ici.
            </p>
          </div>
          <div className="welcome-symbol">⌂</div>
        </section>

        <div className="section-heading">
          <div>
            <h2>Mes modules</h2>
            <p>Les fonctionnalités de votre centrale</p>
          </div>
          <span className="module-count">03 MODULES</span>
        </div>

        <section className="module-grid">
          {modules.map((module) => (
            <article className="module-card" key={module.name}>
              <div className={`module-icon ${module.color}`}>
                {module.icon}
              </div>
              <h3>{module.name}</h3>
              <p>{module.description}</p>
              <div className="module-bottom">
                <span className="status-dot" />
                <span>{module.status}</span>
              </div>
            </article>
          ))}
        </section>     
        </>
        )}

        {pageActive === "accueil" && (
          <section className="domotics-section">
            <div className="section-heading">
              <div>
                <h2>Mes appareils</h2>
                <p>Accès rapide à tes équipements</p>
              </div>
              <span className="module-count">
                {appareils.length} APPAREILS
              </span>
            </div>

            <div className="domotics-grid">
              {appareils.slice(0, 3).map((appareil) => (
                <article className="domotic-card" key={appareil.id}>
                  <div className="domotic-card-top">
                    <div className="domotic-icon">
                      {appareil.type === "lumiere"
                        ? "☼"
                        : appareil.type === "ventilation"
                          ? "✣"
                          : appareil.type === "capteur"
                            ? "◉"
                            : "ϟ"}
                    </div>

                    <span
                      className={
                        appareil.allume
                          ? "domotic-status on"
                          : "domotic-status"
                      }
                    >
                      {appareil.allume ? "Allumé" : "Éteint"}
                    </span>
                  </div>

                  <h3>{appareil.nom}</h3>
                  <p className="domotic-room">{appareil.piece}</p>

                  <div className="domotic-card-bottom">
                    <span>Alimentation</span>

                    <button
                      type="button"
                      className={
                        appareil.allume
                          ? "toggle-switch on"
                          : "toggle-switch"
                      }
                      role="switch"
                      aria-checked={appareil.allume}
                      aria-label={`Alimentation : ${appareil.nom}`}
                      disabled={appareilsEnCours.includes(appareil.id)}
                      onClick={() => void basculerAppareil(appareil)}
                    >
                      <span className="toggle-knob" />
                    </button>
                  </div>
                </article>
              ))}
            </div>

            {appareils.length === 0 && !erreurDomotique && (
             <p className="metric-detail">
                Aucun appareil disponible pour le moment.
                Tu peux en ajouter dans Domotique.
              </p>
            )}
          </section>
        )}

        {pageActive === "rgb" && (
          <section className="rgb-section">
            <div className="section-heading">
              <div>
                <h2>Éclairage RGB</h2>
                <p>Personnalise l'ambiance lumineuse de ta maison</p>
              </div>
              <span
                className={`module-count rgb-connection ${connexionRGB}`}
              >
                {connexionRGB === "verification" && "Vérification…"}
                {connexionRGB === "connecte" && "API RGB connectée"}
                {connexionRGB === "deconnecte" && "API RGB indisponible"}
              </span>
            </div>

            <div className="rgb-panel">
              <div
                className="rgb-preview"
                style={{
                  background: `radial-gradient(circle, ${couleurRGB}66 0%, ${couleurRGB}22 45%, transparent 75%)`,
                  borderColor: couleurRGB,
                }}
              >
                <div
                  className="rgb-light"
                  style={{
                    backgroundColor: couleurRGB,
                    boxShadow: `0 0 ${luminositeRGB}px ${couleurRGB}`,
                    opacity: luminositeRGB / 100,
                  }}
                />
                <p>APERÇU LUMINEUX</p>
                <strong>{couleurRGB.toUpperCase()}</strong>
              </div>

              <div className="rgb-controls">
                <div className="rgb-effects">
                  <p className="rgb-label">Effets de l'éclairage du PC</p>

                  {[
                    { mode: "rainbow", label: "Arc-en-ciel" },
                    { mode: "red_pulse", label: "Rouge pulsé" },
                    { mode: "spectrum_cycle", label: "Défilement des couleurs" },
                    {
                      mode: "spectrum_cycle_breathing",
                      label: "Défilement doux",
                    },
                  ].map((effet) => (
                    <button
                      key={effet.mode}
                      type="button"
                      className={
                        modeRGBActif === effet.mode ? "rgb-effect selected" : "rgb-effect"
                      }
                      disabled={chargementRGB}
                      aria-pressed={modeRGBActif === effet.mode}
                      onClick={() => appliquerModeRGB(effet.mode)}
                    >
                      {effet.label}
                    </button>
                  ))}

                  {chargementRGB && <p>Changement de l'éclairage…</p>}

                  {erreurRGB && (
                    <p role="alert" className="rgb-error">
                      {erreurRGB}
                    </p>
                  )}

                  {modeRGBActif && !erreurRGB && (
                    <p className="rgb-active-effect">
                      Effet actif : {
                        {
                          rainbow: "Arc-en-ciel",
                          red_pulse: "Rouge pulsé",
                          spectrum_cycle: "Défilement des couleurs",
                          spectrum_cycle_breathing: "Défilement doux",
                        }[modeRGBActif] || modeRGBActif
                      }
                    </p>
                  )}
                </div>

                <label htmlFor="couleur-rgb">Choisir une couleur</label>
                <div className="rgb-color-picker">
                  <input
                    id="couleur-rgb"
                    type="color"
                    value={couleurRGB}
                    onChange={(event) => setCouleurRGB(event.target.value)}
                  />
                  <span>{couleurRGB.toUpperCase()}</span>
                </div>

                <p className="rgb-label">Couleurs prédéfinies</p>
                <div className="rgb-presets">
                  {[
                    "#ff3b5c",
                    "#ff9f43",
                    "#ffe66d",
                    "#63e6be",
                    "#339af0",
                    "#845ef7",
                    "#f065d8",
                    "#ffffff",
                  ].map((couleur) => (
                    <button
                      key={couleur}
                      type="button"
                      className={`rgb-preset ${couleurRGB === couleur ? "selected" : ""}`}
                      style={{ backgroundColor: couleur }}
                      aria-label={`Choisir la couleur ${couleur}`}
                      aria-pressed={couleurRGB === couleur}
                      onClick={() => setCouleurRGB(couleur)}
                    />
                  ))}
                </div>

                <div className="rgb-brightness-heading">
                  <label htmlFor="luminosite-rgb">Luminosité</label>
                  <strong>{luminositeRGB}%</strong>
                </div>
                <input
                  id="luminosite-rgb"
                  className="rgb-brightness"
                  type="range"
                  min="0"
                  max="100"
                  value={luminositeRGB}
                  onChange={(event) => setLuminositeRGB(Number(event.target.value))}
                />

                <button
                  type="button"
                  className="rgb-off-button"
                  onClick={() => setLuminositeRGB(0)}
                >
                  Éteindre l'aperçu
                </button>
                <button
                  type="button"
                  className="rgb-on-button"
                  onClick={() => setLuminositeRGB(75)}
                >
                  Rallumer l'aperçu
                </button>
              </div>
            </div>
          </section>
        )}

        {pageActive === "assistant" && (
          <section className="assistant-section">
            <div className="section-heading">
              <div>
                <h2>Assistant Maison</h2>
                <p>Ton espace de discussion personnel</p>
              </div>
              <span className="module-count">ASSISTANT IA</span>
            </div>

            <div className="assistant-panel">
              <div className="assistant-header">
                <div className="assistant-avatar">✦</div>
                <div>
                  <h3>Assistant Maison</h3>
                  <p>Interface de démonstration</p>
                </div>
                <span className="assistant-status">
                  <span className="status-dot" />
                  Prêt
                </span>
              </div>

              <div className="assistant-messages" aria-live="polite">
                {messagesIA.map((message, index) => (
                  <div
                    key={index}
                    className={`assistant-message ${message.role === "user" ? "user-message" : "bot-message"}`}
                  >
                    {message.role === "assistant" && (
                      <div className="assistant-message-icon">✦</div>
                    )}
                    <p>{message.content}</p>
                  </div>
                ))}
              </div>

              <div className="assistant-suggestions">
                <button
                  type="button"
                  onClick={() =>
                    setMessageIA("Quels appareils sont disponibles ?")
                  }
                >
                  Voir mes appareils
                </button>
                <button
                  type="button"
                  onClick={() =>
                    setMessageIA("Comment fonctionne ma centrale ?")
                  }
                >
                  Aide sur ma centrale
                </button>
              </div>

              <form
                className="assistant-input-area"
                onSubmit={(event) => {
                  event.preventDefault();
                  const texte = messageIA.trim();
                  if (!texte) return;

                  setMessagesIA((anciens) => [
                    ...anciens,
                    { role: "user", content: texte },
                    {
                      role: "assistant",
                      content:
                        "Merci pour ton message ! L'interface fonctionne, mais le modèle d'IA n'est pas encore connecté. Cette réponse est automatique.",
                    },
                  ]);
                  setMessageIA("");
                }}
              >
                <input
                  type="text"
                  value={messageIA}
                  onChange={(event) => setMessageIA(event.target.value)}
                  placeholder="Écris ton message..."
                  aria-label="Ton message à l'assistant"
                />
                <button type="submit" disabled={!messageIA.trim()}>
                  Envoyer
                </button>
              </form>

              <p className="assistant-disclaimer">
                Mode démonstration : les réponses ne sont pas générées par une véritable IA.
              </p>
            </div>
          </section>
        )}

        {pageActive === "systeme" && (
        <>
        <section className="metrics-section">
          <div className="section-heading">
            <div>
              <h2>État du PC</h2>
              <p>Ressources système en temps réel</p>
            </div>
            <span className="module-count">ACTUALISATION 5 S</span>
          </div>

          {metricsError && (
            <p className="metrics-error">
              Impossible de récupérer les indicateurs. Vérifiez que l’API fonctionne.
            </p>
            )}

          <div className="metrics-grid">
            <MetricCard
              title="Processeur"
              icon="◉"
              value={metrics ? metrics.cpu.utilisation_pct : null}
              detail="Utilisation du CPU"
            />

            <MetricCard
              title="Mémoire vive"
              icon="▤"
              value={metrics ? metrics.ram.utilisation_pct : null}
              detail={
                metrics
                  ? `${metrics.ram.utilisee_gb} Go utilisés sur ${metrics.ram.totale_gb} Go`
                  : "Chargement des données…"
              }
            />

            <MetricCard
              title="Disque C:"
              icon="▱"
              value={metrics ? metrics.disque.utilisation_pct : null}
              detail={
                metrics
                  ? `${metrics.disque.utilise_gb} Go utilisés · ${metrics.disque.libre_gb} Go libres`
                  : "Chargement des données…"
              }
            />
          </div>
        </section>

        <section className="history-section" id="historique">       
          <div className="section-heading">
            <div>
              <p className="eyebrow">SURVEILLANCE DU SYSTÈME</p>
              <h2>Historique des ressources</h2>
            </div>

            <div className="history-controls">
              <div className="history-periods">
                <button
                  type="button"
                  className={periodeHistorique === 15 ? "active" : ""}
                  onClick={() => setPeriodeHistorique(15)}
                >
                  15 min
                </button>

                <button
                  type="button"
                  className={periodeHistorique === 60 ? "active" : ""}
                  onClick={() => setPeriodeHistorique(60)}
                >
                  1 h
                </button>

                <button
                  type="button"
                  className={periodeHistorique === 1440 ? "active" : ""}
                  onClick={() => setPeriodeHistorique(1440)}
                >
                  24 h
                </button>
              </div>

              <span className="history-count">
                {historiqueGraphique.length} mesures
              </span>
            </div>
          </div>

          {erreurHistorique && (
            <p className="history-error" role="alert">
              Impossible de charger l'historique.
            </p>
          )}

          {!erreurHistorique && historiqueGraphique.length === 0 && (
            <p className="history-empty">
              En attente des premières mesures...
            </p>
          )}

          {historiqueGraphique.length > 0 && (
            <div className="history-grid">
              <article className="history-card">
                <h3>Processeur (CPU)</h3>
              <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={historiqueGraphique}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="heure" stroke="#94a3b8" minTickGap={30} />
                    <YAxis domain={[0, 100]} unit="%" stroke="#94a3b8" />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="cpu_pct"
                      name="CPU"
                      stroke="#60a5fa"
                      dot={false}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </article>

              <article className="history-card">
                <h3>Mémoire vive (RAM)</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={historiqueGraphique}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="heure" stroke="#94a3b8" minTickGap={30} />
                    <YAxis domain={[0, 100]} unit="%" stroke="#94a3b8" />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="ram_pct"
                      name="RAM"
                      stroke="#22d3ee"
                      dot={false}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </article>

              <article className="history-card">
                <h3>Stockage du disque</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={historiqueGraphique}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="heure" stroke="#94a3b8" minTickGap={30} />
                    <YAxis domain={[0, 100]} unit="%" stroke="#94a3b8" />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="disque_pct"
                      name="Disque"
                      stroke="#fbbf24"
                      dot={false}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </article>
            </div>
          )}
        </section>
        </>
      )}

      {pageActive === "domotique" && (
        <section className="domotics-section" id="domotique">
          <div className="section-heading">
            <div>
              <h2>Ma domotique</h2>
              <p>Contrôle de mes appareils connectés</p>
            </div>
            <span className="module-count">
              {appareils.length} APPAREILS
            </span>
          </div>

          {erreurDomotique && (
            <p className="metrics-error">
              Impossible de communiquer avec la domotique. Vérifiez que l’API fonctionne.
            </p>
          )}


          <section className="scenes-panel rooms-panel">
            <div className="section-heading">
              <div><h2>Pièces de la maison</h2><p>Crée et personnalise les espaces qui composeront ton futur plan 3D</p></div>
              <span className="module-count">{pieces.length} PIÈCES</span>
            </div>
            {utilisateurConnecte.role === "admin" && (
              <form className="scene-form room-create-form" onSubmit={creerPiece}>
                <label htmlFor="nom-nouvelle-piece">Nom de la pièce</label>
                <input id="nom-nouvelle-piece" value={nomNouvellePiece} onChange={(event) => setNomNouvellePiece(event.target.value)} placeholder="Ex. : Cuisine" maxLength={60} required />
                <label htmlFor="description-nouvelle-piece">Description (facultative)</label>
                <input id="description-nouvelle-piece" value={descriptionNouvellePiece} onChange={(event) => setDescriptionNouvellePiece(event.target.value)} placeholder="Ex. : Cuisine ouverte sur le séjour" maxLength={240} />
                <label htmlFor="couleur-nouvelle-piece">Couleur de la pièce</label>
                <input id="couleur-nouvelle-piece" type="color" value={couleurNouvellePiece} onChange={(event) => setCouleurNouvellePiece(event.target.value.toUpperCase())} />
                <button type="submit" disabled={pieceEnCours !== null || !nomNouvellePiece.trim()}>Créer la pièce</button>
              </form>
            )}
            {erreurPieces && <p className="sensor-serial-error" role="alert">{erreurPieces}</p>}
            <div className="room-list">
              {pieces.map((piece) => {
                const brouillon = brouillonsPieces[piece.id] ?? { nom: piece.nom, description: piece.description, couleur: piece.couleur };
                return (
                  <form className="room-card" key={piece.id} onSubmit={(event) => { event.preventDefault(); void enregistrerPiece(piece); }}>
                    <span className="room-color" style={{ backgroundColor: brouillon.couleur }} />
                    <div className="room-fields">
                      {utilisateurConnecte.role === "admin" ? (
                        <>
                          <label>Nom<input value={brouillon.nom} maxLength={60} onChange={(event) => setBrouillonsPieces((items) => ({ ...items, [piece.id]: { ...brouillon, nom: event.target.value } }))} required /></label>
                          <label>Description<input value={brouillon.description} maxLength={240} onChange={(event) => setBrouillonsPieces((items) => ({ ...items, [piece.id]: { ...brouillon, description: event.target.value } }))} /></label>
                          <label>Couleur<input type="color" value={brouillon.couleur} onChange={(event) => setBrouillonsPieces((items) => ({ ...items, [piece.id]: { ...brouillon, couleur: event.target.value.toUpperCase() } }))} /></label>
                        </>
                      ) : (
                        <>
                          <strong>{piece.nom}</strong>
                          <span>{piece.description || "Aucune description"}</span>
                        </>
                      )}
                      <span>{piece.nombre_appareils} appareil{piece.nombre_appareils > 1 ? "s" : ""}</span>
                    </div>
                    {utilisateurConnecte.role === "admin" && (
                      <div className="room-actions">
                        <button type="submit" disabled={pieceEnCours !== null}>Enregistrer</button>
                        <button type="button" className="scene-delete" disabled={pieceEnCours !== null || piece.nombre_appareils > 0} title={piece.nombre_appareils > 0 ? "Déplace les appareils avant de supprimer cette pièce" : "Supprimer la pièce"} onClick={() => void supprimerPiece(piece)}>Supprimer</button>
                      </div>
                    )}
                  </form>
                );
              })}
              {pieces.length === 0 && <p className="metric-detail">Aucune pièce enregistrée.</p>}
            </div>
            <p className="metric-detail">Les pièces déjà présentes ont été reprises automatiquement depuis tes appareils. Renommer une pièce met également à jour les appareils qui lui sont associés. Une pièce contenant des appareils ne peut pas être supprimée.</p>
          </section>

          <section className="scenes-panel">
            <div className="section-heading">
              <div><h2>Scènes lumineuses</h2><p>Enregistre et applique tes ambiances à toutes les lumières</p></div>
              <span className="module-count">{scenes.length} SCÈNES</span>
            </div>
            <form className="scene-form" onSubmit={creerScene}>
              <label htmlFor="nom-scene">Nom de l'ambiance</label>
              <input id="nom-scene" value={nomScene} onChange={(event) => setNomScene(event.target.value)} placeholder="Ex. : Soirée détente" required maxLength={80} />
              <label htmlFor="luminosite-scene">Luminosité : {luminositeScene} %</label>
              <input id="luminosite-scene" type="range" min="0" max="100" value={luminositeScene} onChange={(event) => setLuminositeScene(Number(event.target.value))} />
              <label htmlFor="temperature-scene">Température : {temperatureScene} K</label>
              <input id="temperature-scene" type="range" min="2700" max="6500" step="100" value={temperatureScene} onChange={(event) => setTemperatureScene(Number(event.target.value))} />
              <label htmlFor="couleur-scene">Couleur RGB</label>
              <input id="couleur-scene" type="color" value={couleurScene} onChange={(event) => setCouleurScene(event.target.value.toUpperCase())} />
              <button type="submit" disabled={sceneEnCours || !nomScene.trim()}>{sceneEnCours ? "En cours…" : "Enregistrer la scène"}</button>
            </form>
            <div className="scene-list">
              {scenes.map((scene) => (
                <article className="scene-card" key={scene.id}>
                  <span className="scene-swatch" style={{ backgroundColor: scene.couleur }} />
                  <div className="scene-details"><strong>{scene.nom}</strong><span>{scene.luminosite} % · {scene.temperature_couleur} K · {scene.couleur}</span></div>
                  <button type="button" onClick={() => void appliquerScene(scene)} disabled={sceneEnCours}>Appliquer</button>
                  <button type="button" className="scene-delete" onClick={() => void supprimerScene(scene)} disabled={sceneEnCours} aria-label={`Supprimer ${scene.nom}`}>Supprimer</button>
                </article>
              ))}
              {scenes.length === 0 && <p className="metric-detail">Aucune scène enregistrée pour le moment.</p>}
            </div>
            {messageDomotique && <p role="status" className="scene-message">{messageDomotique}</p>}
          </section>

          <section className="scenes-panel automation-panel">
            <div className="section-heading">
              <div><h2>Automatisations horaires</h2><p>Déclenche une scène à l'heure choisie, pour toute la maison ou une pièce</p></div>
              <span className="module-count">{automatisations.length} RÈGLES</span>
            </div>
            <form className="scene-form" onSubmit={creerAutomatisation}>
              <label htmlFor="nom-automation">Nom de la règle</label>
              <input id="nom-automation" value={nomAutomatisation} onChange={(event) => setNomAutomatisation(event.target.value)} placeholder="Ex. : Ambiance du soir" required maxLength={80} />
              <label htmlFor="heure-automation">Heure de déclenchement (heure locale du PC)</label>
              <input id="heure-automation" type="time" value={heureAutomatisation} onChange={(event) => setHeureAutomatisation(event.target.value)} required />
              <label>Jours d'activation</label>
              <div className="automation-days">
                {JOURS_SEMAINE.map((jour, index) => (
                  <label key={jour}><input type="checkbox" checked={joursAutomatisation.includes(index + 1)} onChange={(event) => setJoursAutomatisation((jours) => event.target.checked ? [...jours, index + 1].sort() : jours.filter((value) => value !== index + 1))} />{jour}</label>
                ))}
              </div>
              <label htmlFor="scene-automation">Scène à appliquer</label>
              <select id="scene-automation" value={sceneAutomatisation} onChange={(event) => setSceneAutomatisation(event.target.value)} required>
                <option value="">Choisir une scène</option>
                {scenes.map((scene) => <option key={scene.id} value={scene.id}>{scene.nom}</option>)}
              </select>
              <label htmlFor="piece-automation">Pièce ciblée (facultatif)</label>
              <select id="piece-automation" value={pieceAutomatisation} onChange={(event) => setPieceAutomatisation(event.target.value)}>
                <option value="">Toutes les pièces</option>
                {[...new Set(appareils.filter((appareil) => appareil.type === "lumiere").map((appareil) => appareil.piece))].sort().map((piece) => <option key={piece} value={piece}>{piece}</option>)}
              </select>
              <label htmlFor="extinction-automation">Éteindre automatiquement après (minutes, facultatif)</label>
              <input id="extinction-automation" type="number" min="1" max="1440" value={extinctionAutomatisation} onChange={(event) => setExtinctionAutomatisation(event.target.value)} placeholder="Ex. : 90" />
              <button type="submit" disabled={automatisationEnCours || !nomAutomatisation.trim() || !sceneAutomatisation || joursAutomatisation.length === 0 || scenes.length === 0}>{automatisationEnCours ? "En cours…" : "Créer l'automatisation"}</button>
            </form>
            <div className="automation-list">
              {automatisations.map((item) => (
                <article className="scene-card" key={item.id}>
                  <div className="scene-details">
                    <strong>{item.nom} · {item.heure}</strong>
                    <span>{item.jours.map((jour) => JOURS_SEMAINE[jour - 1]).join(", ")} · {scenes.find((scene) => scene.id === item.scene_id)?.nom ?? "Scène"} · {item.piece || "Toutes les pièces"}{item.extinction_minutes ? ` · Extinction après ${item.extinction_minutes} min` : ""}</span>
                  </div>
                  <button type="button" className={item.active ? "" : "scene-delete"} onClick={() => void basculerAutomatisation(item)} disabled={automatisationEnCours}>{item.active ? "Activée" : "Désactivée"}</button>
                  <button type="button" className="scene-delete" onClick={() => void supprimerAutomatisation(item)} disabled={automatisationEnCours}>Supprimer</button>
                </article>
              ))}
              {automatisations.length === 0 && <p className="metric-detail">Aucune automatisation configurée.</p>}
            </div>
          </section>

          <section className="scenes-panel automation-panel">
            <div className="section-heading">
              <div><h2>Automatisations conditionnelles</h2><p>Déclenche une scène selon la luminosité ou la présence détectée</p></div>
              <span className="module-count">{conditions.length} RÈGLES</span>
            </div>
            <div className="sensor-simulation-list">
              <h3>Capteurs simulés</h3>
              {capteurs.map((capteur) => (
                <article className="scene-card" key={capteur.id}>
                  <div className="scene-details"><strong>{capteur.nom} · {capteur.piece}</strong>
                    <span>{capteur.mesure ? `${capteur.mesure.type_mesure} : ${capteur.mesure.valeur} · actualisé ${new Date(capteur.mesure.mise_a_jour).toLocaleTimeString("fr-FR")}` : "Aucune mesure reçue"}</span>
                  </div>
                  {capteur.id.includes("luminosite") ? (
                    <label className="sensor-control">Luminosité simulée
                      <input type="range" min="0" max="100" value={capteur.mesure?.valeur ?? 80} onChange={(event) => void simulerCapteur(capteur, "luminosite", Number(event.target.value))} />
                      <span>{capteur.mesure?.valeur ?? 80} %</span>
                    </label>
                  ) : (
                    <button type="button" onClick={() => void simulerCapteur(capteur, "presence", capteur.mesure?.valeur ? 0 : 1)}>
                      {capteur.mesure?.valeur ? "Simuler une absence" : "Simuler une présence"}
                    </button>
                  )}
                </article>
              ))}
              {capteurs.length === 0 && <p className="metric-detail">Ajoute un appareil de type capteur pour commencer.</p>}
            </div>
            <div className="sensor-serial-panel">
              <div className="sensor-serial-heading">
                <h3>Configuration des ports USB / série</h3>
                <button type="button" onClick={() => void chargerConfigurationsSerie()}>Actualiser les ports</button>
              </div>
              <p className="metric-detail">Associe chaque capteur logique à un port détecté et configure son débit. Cette étape n'ouvre aucun port et n'envoie aucune donnée.</p>
              {portsSerieErreur && <p className="sensor-serial-error" role="alert">{portsSerieErreur}</p>}
              {!portsSerieDisponibles && <p className="metric-detail">Vérifie que pySerial est installé dans l'environnement virtuel, puis actualise.</p>}
              {capteurs.map((capteur) => {
                const configuration = configurationsSerie.find((item) => item.capteur_id === capteur.id);
                const portsUtilises = new Set(configurationsSerie.filter((item) => item.capteur_id !== capteur.id).map((item) => item.port.toUpperCase()));
                const portCourant = portsSelectionnes[capteur.id] ?? configuration?.port ?? "";
                const debitCourant = debitsSelectionnes[capteur.id] ?? configuration?.debit ?? 9600;
                return (
                  <article className="sensor-serial-card" key={capteur.id}>
                    <div className="scene-details">
                      <strong>{capteur.nom} · {capteur.piece}</strong>
                      <span>{configuration ? `Associé à ${configuration.port} · ${configuration.debit} bauds · protocole à configurer` : "Aucun port associé"}</span>
                    </div>
                    <label>Port série
                      <select value={portCourant} onChange={(event) => setPortsSelectionnes((items) => ({ ...items, [capteur.id]: event.target.value }))} disabled={!portsSerieDisponibles || configurationSerieEnCours === capteur.id}>
                        <option value="">Choisir un port détecté</option>
                        {portsSerie.filter((port) => !portsUtilises.has(port.port.toUpperCase()) || port.port === configuration?.port).map((port) => (
                          <option key={port.port} value={port.port}>{port.port} · {port.description}</option>
                        ))}
                      </select>
                    </label>
                    <label>Débit (bauds)
                      <select value={debitCourant} onChange={(event) => setDebitsSelectionnes((items) => ({ ...items, [capteur.id]: Number(event.target.value) }))} disabled={configurationSerieEnCours === capteur.id}>
                        {[300, 1200, 2400, 4800, 9600, 14400, 19200, 38400, 57600, 115200, 230400, 460800, 921600].map((debit) => <option key={debit} value={debit}>{debit.toLocaleString("fr-FR")}</option>)}
                      </select>
                    </label>
                    <div className="sensor-serial-actions">
                      <button type="button" onClick={() => void enregistrerConfigurationSerie(capteur)} disabled={!portsSerieDisponibles || !portCourant || configurationSerieEnCours === capteur.id}>{configurationSerieEnCours === capteur.id ? "En cours…" : "Enregistrer"}</button>
                      {configuration && <button type="button" className="scene-delete" onClick={() => void supprimerConfigurationSerie(capteur)} disabled={configurationSerieEnCours === capteur.id}>Retirer</button>}
                    </div>
                  </article>
                );
              })}
              {portsSerieDisponibles && portsSerie.length === 0 && <p className="metric-detail">Aucun port série détecté sur cet ordinateur.</p>}
            </div>
            <form className="scene-form" onSubmit={creerConditionnelle}>
              <label htmlFor="nom-condition">Nom de la règle</label>
              <input id="nom-condition" value={nomCondition} onChange={(event) => setNomCondition(event.target.value)} placeholder="Ex. : Éclairage à la tombée du jour" required maxLength={80} />
              <label htmlFor="type-condition">Déclencheur</label>
              <select id="type-condition" value={typeCondition} onChange={(event) => setTypeCondition(event.target.value)}>
                <option value="luminosite_inferieure">Luminosité inférieure au seuil</option>
                <option value="presence_detectee">Présence détectée</option>
                <option value="absence_prolongee">Absence prolongée</option>
              </select>
              <label htmlFor="capteur-condition">Capteur</label>
              <select id="capteur-condition" value={capteurCondition} onChange={(event) => setCapteurCondition(event.target.value)} required>
                <option value="">Choisir un capteur</option>
                {capteurs.filter((capteur) => typeCondition === "luminosite_inferieure" ? capteur.id.includes("luminosite") : capteur.id.includes("presence")).map((capteur) => <option key={capteur.id} value={capteur.id}>{capteur.nom} · {capteur.piece}</option>)}
              </select>
              {typeCondition === "luminosite_inferieure" && <>
                <label htmlFor="seuil-condition">Seuil de luminosité (%)</label>
                <input id="seuil-condition" type="number" min="0" max="100" value={seuilCondition} onChange={(event) => setSeuilCondition(Number(event.target.value))} />
              </>}
              {typeCondition === "absence_prolongee" && <>
                <label htmlFor="duree-absence">Durée d'absence (minutes)</label>
                <input id="duree-absence" type="number" min="1" max="1440" value={dureeAbsenceCondition} onChange={(event) => setDureeAbsenceCondition(Number(event.target.value))} />
              </>}
              {typeCondition !== "absence_prolongee" && <>
                <label htmlFor="scene-condition">Scène à appliquer</label>
                <select id="scene-condition" value={sceneCondition} onChange={(event) => setSceneCondition(event.target.value)} required>
                  <option value="">Choisir une scène</option>
                  {scenes.map((scene) => <option key={scene.id} value={scene.id}>{scene.nom}</option>)}
                </select>
              </>}
              <label htmlFor="piece-condition">Pièce ciblée (facultatif)</label>
              <select id="piece-condition" value={pieceCondition} onChange={(event) => setPieceCondition(event.target.value)}>
                <option value="">Toutes les pièces</option>
                {[...new Set(appareils.filter((appareil) => appareil.type === "lumiere").map((appareil) => appareil.piece))].sort().map((piece) => <option key={piece} value={piece}>{piece}</option>)}
              </select>
              <button type="submit" disabled={automatisationEnCours || !nomCondition.trim() || !capteurCondition || (typeCondition !== "absence_prolongee" && (!sceneCondition || scenes.length === 0))}>Créer la règle conditionnelle</button>
            </form>
            <div className="automation-list">
              {conditions.map((item) => (
                <article className="scene-card" key={item.id}>
                  <div className="scene-details"><strong>{item.nom}</strong>
                    <span>{item.condition === "luminosite_inferieure" ? `Luminosité sous ${item.seuil}%` : item.condition === "presence_detectee" ? "Présence détectée" : `Absence de ${item.duree_absence} min`} · {capteurs.find((capteur) => capteur.id === item.capteur_id)?.nom ?? item.capteur_id} · {item.piece || "Toutes les pièces"}</span>
                  </div>
                  <button type="button" className={item.active ? "" : "scene-delete"} onClick={() => void basculerConditionnelle(item)}>{item.active ? "Activée" : "Désactivée"}</button>
                  <button type="button" className="scene-delete" onClick={() => void supprimerConditionnelle(item)}>Supprimer</button>
                </article>
              ))}
              {conditions.length === 0 && <p className="metric-detail">Aucune règle conditionnelle.</p>}
            </div>
          </section>

          {utilisateurConnecte.role === "admin" && (
            <form className="domotic-form" onSubmit={ajouterAppareil}>
              <h3>Ajouter un appareil</h3>

              <label htmlFor="nom-appareil">Nom de l'appareil</label>
              <input
                id="nom-appareil"
                type="text"
                value={nomNouvelAppareil}
                onChange={(event) => setNomNouvelAppareil(event.target.value)}
                placeholder="Ex. : Lampe cuisine"
                required
              />

              <label htmlFor="piece-appareil">Pièce</label>
              <input
                id="piece-appareil"
                type="text"
                value={pieceNouvelAppareil}
                onChange={(event) => setPieceNouvelAppareil(event.target.value)}
                placeholder="Ex. : Cuisine"
                required
              />

              <label htmlFor="type-appareil">Type d'appareil</label>
              <select
                id="type-appareil"
                value={typeNouvelAppareil}
                onChange={(event) => setTypeNouvelAppareil(event.target.value)}
              >
                <option value="lumiere">Lumière</option>
                <option value="ventilation">Ventilation</option>
                <option value="prise">Prise connectée</option>
                <option value="capteur">Capteur</option>
              </select>

              <button type="submit" disabled={ajoutEnCours}>
                {ajoutEnCours ? "Ajout en cours..." : "Ajouter l'appareil"}
              </button>

              {messageDomotique && (
                <p role="status">{messageDomotique}</p>
              )}
            </form>
          )}

          <div className="domotics-grid">
            {appareils.map((appareil) => (
              
            <article className="domotic-card" key={appareil.id}>
              <div className="domotic-card-top">
                <div className="domotic-icon">
                  {appareil.type === "lumiere"
                    ? "☼"
                    : appareil.type === "ventilation"
                      ? "✣"
                      : appareil.type === "capteur"
                        ? "◉"
                        : "ϟ"}
                </div>

                <span
                  className={
                    appareil.type !== "capteur" && appareil.allume
                      ? "domotic-status on"
                      : "domotic-status"
                  }
                >
                  {appareil.type === "capteur"
                    ? "Lecture seule"
                    : appareil.allume ? "Allumé" : "Éteint"}
                </span>
              </div>

              <h3>{appareil.nom}</h3>
              <p className="domotic-room">{appareil.piece}</p>

              {appareil.type === "lumiere" && appareil.capacites?.includes("luminosite") && (
                <>
                <div className="domotic-brightness">
                  <label htmlFor={`luminosite-${appareil.id}`}>
                    Luminosité : {appareil.luminosite ?? 100}%
                  </label>
                  <input
                    id={`luminosite-${appareil.id}`}
                    type="range"
                    min={0}
                    max={100}
                    step={1}
                    value={appareil.luminosite ?? 100}
                    disabled={appareilsEnCours.includes(appareil.id)}
                    aria-label={`Luminosité : ${appareil.nom}`}
                    onChange={(event) => {
                      const luminosite = Number(event.target.value);
                      setAppareils((anciens) => anciens.map((element) =>
                        element.id === appareil.id ? { ...element, luminosite } : element
                      ));
                    }}
                    onPointerUp={(event) =>
                      void reglerLuminosite(appareil, Number(event.currentTarget.value))
                    }
                    onKeyUp={(event) => {
                      if (event.key.startsWith("Arrow") || event.key === "Home" || event.key === "End") {
                        void reglerLuminosite(appareil, Number(event.currentTarget.value));
                      }
                    }}
                  />
                </div>
                <div className="domotic-temperature">
                  <label htmlFor={`temperature-${appareil.id}`}>
                    Température de couleur : {appareil.temperature_couleur ?? 4000} K
                  </label>
                  <input
                    id={`temperature-${appareil.id}`}
                    type="range"
                    min={2700}
                    max={6500}
                    step={100}
                    value={appareil.temperature_couleur ?? 4000}
                    disabled={appareilsEnCours.includes(appareil.id)}
                    aria-label={`Température de couleur : ${appareil.nom}`}
                    onChange={(event) => {
                      const temperature_couleur = Number(event.target.value);
                      setAppareils((anciens) => anciens.map((element) =>
                        element.id === appareil.id ? { ...element, temperature_couleur } : element
                      ));
                    }}
                    onPointerUp={(event) =>
                      void reglerTemperatureCouleur(appareil, Number(event.currentTarget.value))
                    }
                    onKeyUp={(event) => {
                      if (event.key.startsWith("Arrow") || event.key === "Home" || event.key === "End") {
                        void reglerTemperatureCouleur(appareil, Number(event.currentTarget.value));
                      }
                    }}
                  />
                  <div className="domotic-temperature-labels" aria-hidden="true">
                    <span>Chaud</span><span>Froid</span>
                  </div>
                </div>

                <div className="domotic-color">
                  <label htmlFor={`couleur-${appareil.id}`}>
                    Couleur RGB : {appareil.couleur ?? "#FFFFFF"}
                  </label>
                  <input
                    id={`couleur-${appareil.id}`}
                    type="color"
                    value={appareil.couleur ?? "#FFFFFF"}
                    disabled={appareilsEnCours.includes(appareil.id)}
                    aria-label={`Couleur RGB : ${appareil.nom}`}
                    onChange={(event) => {
                      const couleur = event.target.value.toUpperCase();
                      setAppareils((anciens) => anciens.map((element) =>
                        element.id === appareil.id ? { ...element, couleur } : element
                      ));
                    }}
                    onBlur={(event) => void reglerCouleur(appareil, event.currentTarget.value.toUpperCase())}
                  />
                </div>
                </>
              )}

              <div className="domotic-card-bottom">
                <span>{appareil.type === "capteur" ? "Capteur" : "Alimentation"}</span>

                {appareil.type !== "capteur" &&
                  (appareil.capacites?.includes("marche_arret") ?? true) && (
                    <button
                      type="button"
                      className={
                        appareil.allume
                          ? "toggle-switch on"
                          : "toggle-switch"
                      }
                      role="switch"
                      aria-checked={appareil.allume}
                      aria-label={`Alimentation : ${appareil.nom}`}
                      disabled={appareilsEnCours.includes(appareil.id)}
                      onClick={() => void basculerAppareil(appareil)}
                    >
                      <span className="toggle-knob" />
                    </button>
                  )}
              </div>

              {utilisateurConnecte.role === "admin" && (
                <button
                  type="button"
                  className="domotic-delete-button"
                disabled={appareilsEnCours.includes(appareil.id)}
                onClick={() => void supprimerAppareil(appareil)}
              >
                {appareilsEnCours.includes(appareil.id)
                  ? "Opération en cours..."
                  : "Supprimer"}
                </button>
              )}
            </article>

            ))}
          </div>

          {appareils.length === 0 && !erreurDomotique && (
            <p className="metric-detail">
              Chargement des appareils…
            </p>
          )}
        </section>
      )}

        {pageActive === "plan3d" && (
          <section className="plan3d-page">
            <div className="section-heading">
              <div><h2>Vue interactive de la maison</h2><p>Explore le volume, règle la caméra et prépare la construction de ton plan réel.</p></div>
              <span className="module-count">APERÇU 3D</span>
            </div>
            <Plan3D />
          </section>
        )}

        <section className="system-panel" id="systeme">
          <div>
            <div className="system-indicator">
              <span
                className="status-dot"
                style={{
                  background: apiError
                    ? "#ef7777"
                    : systemStatus
                      ? "#63d8a2"
                      : "#e8b86c",
                }}
              />
              {apiError
                ? "API déconnectée"
                : systemStatus
                  ? "API connectée"
                  : "Connexion en cours…"}
            </div>

            <h2>
              {systemStatus?.centrale ?? "Votre centrale prend forme"}
            </h2>

            <p>
              {systemStatus
                ? `Dernière heure UTC reçue : ${systemStatus.heure_utc}`
                : apiError
                  ? "Vérifiez que le serveur FastAPI fonctionne."
                  : "Récupération des données du système…"}
            </p>
          </div>

          <div className="system-badge">
            {systemStatus ? "V " + "0.1.0" : "API"}
          </div>
        </section>

        <footer className="footer">
          <span>Maison Connectée · Projet personnel</span>
          <span>Interface 0.1.0</span>
        </footer>
        </section>
    </main>
  );
}

type MetricCardProps = {
  title: string;
  icon: string;
  value: number | null;
  detail: string;
};

function MetricCard({ title, icon, value, detail }: MetricCardProps) {
  const progress =
    value === null ? 0 : Math.min(100, Math.max(0, value));

  return (
    <article className="metric-card">
      <div className="metric-card-top">
        <div className="metric-icon">{icon}</div>
        <span className="metric-live">
          <span className="status-dot" />
          {value === null ? "En attente" : "En direct"}
        </span>
      </div>

      <h3>{title}</h3>

      <div className="metric-value">
        {value === null ? "—" : `${value.toFixed(1)}%`}
      </div>

      <div
        className="metric-progress"
        role="progressbar"
        aria-label={title}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value ?? 0}
      >
        <div
          className="metric-progress-fill"
          style={{ width: `${progress}%` }}
        />
      </div>

      <p className="metric-detail">{detail}</p>
    </article>
  );
}

export default App;
