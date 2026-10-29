import { useEffect, useState } from "react";
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

type Appareil = {
  id: string;
  nom: string;
  piece: string;
  type: string;
  allume: boolean;
  capacites?: string[];
};

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
  const [erreurDomotique, setErreurDomotique] = useState(false);
  const [appareilsEnCours, setAppareilsEnCours] = useState<string[]>([]);
  const [nomNouvelAppareil, setNomNouvelAppareil] = useState("");
  const [pieceNouvelAppareil, setPieceNouvelAppareil] = useState("");
  const [typeNouvelAppareil, setTypeNouvelAppareil] = useState("lumiere");
  const [ajoutEnCours, setAjoutEnCours] = useState(false);
  const [messageDomotique, setMessageDomotique] = useState("");

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
