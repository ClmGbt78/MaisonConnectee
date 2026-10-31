import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "../api";

type Appareil = { id: string; nom: string; piece: string; type: string; allume: boolean };
type Piece = { id: string; nom: string; nombre_appareils: number };
type Automatisation = { id: string; nom: string; active: boolean; heure: string };
type Metrics = { cpu: { utilisation_pct: number }; ram: { utilisation_pct: number }; disque: { utilisation_pct: number } };
type WidgetId = "resume" | "appareils" | "pieces" | "automatisations" | "notifications" | "systeme";
type Widget = { id: WidgetId; size: "compact" | "wide" };
type Notification = { id: number; titre: string; message: string; priorite: string; cree_le: string; lu_le: string | null };

const widgetsDisponibles: { id: WidgetId; titre: string; description: string }[] = [
  { id: "resume", titre: "Vue d'ensemble", description: "Résumé des éléments de la maison" },
  { id: "appareils", titre: "Mes appareils", description: "État des équipements" },
  { id: "pieces", titre: "Mes pièces", description: "Pièces configurées" },
  { id: "automatisations", titre: "Automatisations", description: "Règles actives" },
  { id: "notifications", titre: "Notifications récentes", description: "Derniers événements" },
  { id: "systeme", titre: "Ressources système", description: "CPU, mémoire et stockage" },
];
const dispositionParDefaut: Widget[] = [
  { id: "resume", size: "wide" }, { id: "appareils", size: "wide" },
  { id: "pieces", size: "compact" }, { id: "automatisations", size: "compact" },
  { id: "notifications", size: "wide" },
];

type Props = {
  appareils: Appareil[];
  pieces: Piece[];
  automatisations: Automatisation[];
  metrics: Metrics | null;
  onNavigate: (page: string) => void;
};

export default function Dashboard({ appareils, pieces, automatisations, metrics, onNavigate }: Props) {
  const [widgets, setWidgets] = useState<Widget[]>(dispositionParDefaut);
  const [configurationOuverte, setConfigurationOuverte] = useState(false);
  const [chargement, setChargement] = useState(true);
  const [enregistrement, setEnregistrement] = useState(false);
  const [erreur, setErreur] = useState("");
  const [message, setMessage] = useState("");
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [nonLues, setNonLues] = useState(0);
  const [widgetGlisse, setWidgetGlisse] = useState<WidgetId | null>(null);

  useEffect(() => {
    let actif = true;
    Promise.all([apiFetch("/api/dashboard/preferences"), apiFetch("/api/notifications?limite=5"), apiFetch("/api/notifications?non_lues=true&limite=200")])
      .then(async ([preferencesResponse, notificationsResponse, nonLuesResponse]) => {
        if (!preferencesResponse.ok) throw new Error("Impossible de charger la disposition du tableau de bord.");
        const preferences = await preferencesResponse.json();
        if (actif && Array.isArray(preferences.widgets)) setWidgets(preferences.widgets);
        if (notificationsResponse.ok) {
          const elements: Notification[] = await notificationsResponse.json();
          if (actif) {
            setNotifications(elements);
          }
        }
        if (nonLuesResponse.ok) {
          const elementsNonLus: Notification[] = await nonLuesResponse.json();
          if (actif) setNonLues(elementsNonLus.length);
        }
      })
      .catch((cause) => { if (actif) setErreur(cause instanceof Error ? cause.message : "Erreur de chargement."); })
      .finally(() => { if (actif) setChargement(false); });
    return () => { actif = false; };
  }, []);

  const appareilsAllumes = useMemo(() => appareils.filter((item) => item.allume).length, [appareils]);
  const automatisationsActives = useMemo(() => automatisations.filter((item) => item.active).length, [automatisations]);

  function modifierWidget(id: WidgetId, actif: boolean) {
    setWidgets((anciens) => {
      if (actif) return anciens.some((item) => item.id === id) ? anciens : [...anciens, { id, size: "compact" }];
      return anciens.filter((item) => item.id !== id);
    });
    setMessage("");
  }
  function deplacerWidget(source: WidgetId, cible: WidgetId) {
    setWidgets((anciens) => {
      const resultat = [...anciens];
      const indexSource = resultat.findIndex((item) => item.id === source);
      const indexCible = resultat.findIndex((item) => item.id === cible);
      if (indexSource < 0 || indexCible < 0) return anciens;
      const [element] = resultat.splice(indexSource, 1);
      resultat.splice(indexCible, 0, element);
      return resultat;
    });
  }
  function changerTaille(id: WidgetId) {
    setWidgets((anciens) => anciens.map((item) => item.id === id ? { ...item, size: item.size === "wide" ? "compact" : "wide" } : item));
  }
  async function enregistrer() {
    setEnregistrement(true); setErreur(""); setMessage("");
    try {
      const response = await apiFetch("/api/dashboard/preferences", {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ widgets }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Impossible d'enregistrer la disposition.");
      setWidgets(data.widgets); setMessage("Disposition enregistrée."); setConfigurationOuverte(false);
    } catch (cause) {
      setErreur(cause instanceof Error ? cause.message : "Erreur d'enregistrement.");
    } finally { setEnregistrement(false); }
  }

  function afficherWidget(widget: Widget) {
    switch (widget.id) {
      case "resume":
        return <div className="dashboard-summary-grid">
          <div><span>Appareils</span><strong>{appareils.length}</strong><small>{appareilsAllumes} allumé(s)</small></div>
          <div><span>Pièces</span><strong>{pieces.length}</strong><small>dans la maison</small></div>
          <div><span>Automatisations</span><strong>{automatisationsActives}</strong><small>active(s)</small></div>
          <div><span>Notifications</span><strong>{nonLues}</strong><small>non lue(s)</small></div>
        </div>;
      case "appareils":
        return <div className="dashboard-item-list">
          {appareils.slice(0, 6).map((item) => <div className="dashboard-list-row" key={item.id}>
            <span className="dashboard-list-icon">{item.type === "lumiere" ? "☼" : item.type === "capteur" ? "◉" : "ϟ"}</span>
            <span className="dashboard-list-main"><strong>{item.nom}</strong><small>{item.piece}</small></span>
            <span className={item.allume ? "dashboard-state is-on" : "dashboard-state"}>{item.allume ? "Allumé" : "Éteint"}</span>
          </div>)}
          {appareils.length === 0 && <p className="dashboard-empty">Aucun appareil enregistré.</p>}
          <button className="dashboard-text-button" onClick={() => onNavigate("domotique")}>Gérer les appareils →</button>
        </div>;
      case "pieces":
        return <div className="dashboard-room-grid">
          {pieces.slice(0, 8).map((piece) => <div className="dashboard-room" key={piece.id}><strong>{piece.nom}</strong><small>{piece.nombre_appareils} appareil(s)</small></div>)}
          {pieces.length === 0 && <p className="dashboard-empty">Aucune pièce enregistrée.</p>}
          <button className="dashboard-text-button" onClick={() => onNavigate("domotique")}>Gérer les pièces →</button>
        </div>;
      case "automatisations":
        return <div className="dashboard-item-list">
          {automatisations.slice(0, 5).map((item) => <div className="dashboard-list-row" key={item.id}>
            <span className="dashboard-list-icon">◷</span><span className="dashboard-list-main"><strong>{item.nom}</strong><small>{item.heure}</small></span>
            <span className={item.active ? "dashboard-state is-on" : "dashboard-state"}>{item.active ? "Active" : "Inactive"}</span>
          </div>)}
          {automatisations.length === 0 && <p className="dashboard-empty">Aucune automatisation programmée.</p>}
          <button className="dashboard-text-button" onClick={() => onNavigate("domotique")}>Gérer les automatisations →</button>
        </div>;
      case "notifications":
        return <div className="dashboard-item-list">
          {notifications.slice(0, 4).map((item) => <div className="dashboard-notification-row" key={item.id}>
            <span className={`notification-priority ${item.priorite}`} />
            <span className="dashboard-list-main"><strong>{item.titre}</strong><small>{item.message}</small></span>
            <small>{new Date(item.cree_le).toLocaleString("fr-FR")}</small>
          </div>)}
          {notifications.length === 0 && <p className="dashboard-empty">Aucune notification pour le moment.</p>}
          <button className="dashboard-text-button" onClick={() => onNavigate("notifications")}>Ouvrir le centre de notifications →</button>
        </div>;
      case "systeme":
        return <div className="dashboard-summary-grid">
          <div><span>Processeur</span><strong>{metrics ? `${Math.round(metrics.cpu.utilisation_pct)} %` : "—"}</strong><small>utilisation</small></div>
          <div><span>Mémoire</span><strong>{metrics ? `${Math.round(metrics.ram.utilisation_pct)} %` : "—"}</strong><small>utilisation</small></div>
          <div><span>Stockage</span><strong>{metrics ? `${Math.round(metrics.disque.utilisation_pct)} %` : "—"}</strong><small>utilisation</small></div>
        </div>;
    }
  }

  return <section className="dashboard-home">
    <div className="dashboard-welcome">
      <div><p className="eyebrow">VOTRE MAISON, EN UN SEUL ENDROIT</p><h2>Bienvenue chez vous.</h2><p>Retrouvez en un coup d'œil les informations importantes de votre maison.</p></div>
      <div className="dashboard-welcome-actions"><button onClick={() => onNavigate("domotique")}>Domotique</button><button onClick={() => onNavigate("plan3d")}>Plan 3D</button></div>
    </div>
    <div className="section-heading dashboard-section-heading">
      <div><h2>Mon tableau de bord</h2><p>Organisez les informations affichées selon vos besoins.</p></div>
      <button className="dashboard-configure-button" onClick={() => setConfigurationOuverte((value) => !value)}>{configurationOuverte ? "Fermer les réglages" : "Personnaliser"}</button>
    </div>
    {configurationOuverte && <div className="dashboard-config-panel">
      <div><h3>Widgets affichés</h3><p>Activez les cartes souhaitées, puis déplacez-les ou changez leur largeur.</p></div>
      <div className="dashboard-widget-options">{widgetsDisponibles.map((option) => <label key={option.id}>
        <input type="checkbox" checked={widgets.some((item) => item.id === option.id)} onChange={(event) => modifierWidget(option.id, event.target.checked)} />
        <span><strong>{option.titre}</strong><small>{option.description}</small></span>
      </label>)}</div>
      <div className="dashboard-config-actions"><button className="dashboard-save-button" onClick={() => void enregistrer()} disabled={enregistrement || chargement}>{enregistrement ? "Enregistrement…" : "Enregistrer ma disposition"}</button></div>
    </div>}
    {erreur && <p className="dashboard-error" role="alert">{erreur}</p>}
    {message && <p className="dashboard-success" role="status">{message}</p>}
    {chargement ? <p className="dashboard-empty">Chargement du tableau de bord…</p> : <div className="dashboard-widget-grid">
      {widgets.map((widget, index) => {
        const titre = widgetsDisponibles.find((item) => item.id === widget.id)?.titre ?? widget.id;
        return <article key={widget.id} className={`dashboard-widget ${widget.size === "wide" ? "size-wide" : "size-compact"}`}
          draggable onDragStart={() => setWidgetGlisse(widget.id)} onDragOver={(event) => event.preventDefault()}
          onDrop={() => { if (widgetGlisse && widgetGlisse !== widget.id) deplacerWidget(widgetGlisse, widget.id); setWidgetGlisse(null); }}
          onDragEnd={() => setWidgetGlisse(null)}>
          <header><h3>{titre}</h3><div className="dashboard-widget-tools">
            <button aria-label={`Déplacer ${titre} vers le haut`} disabled={index === 0} onClick={() => deplacerWidget(widget.id, widgets[index - 1].id)}>↑</button>
            <button aria-label={`Déplacer ${titre} vers le bas`} disabled={index === widgets.length - 1} onClick={() => deplacerWidget(widget.id, widgets[index + 1].id)}>↓</button>
            <button aria-label={`Changer la largeur de ${titre}`} onClick={() => changerTaille(widget.id)}>{widget.size === "wide" ? "½" : "↔"}</button>
          </div></header>
          {afficherWidget(widget)}
        </article>;
      })}
      {widgets.length === 0 && <p className="dashboard-empty">Aucun widget affiché. Utilisez « Personnaliser » pour en ajouter.</p>}
    </div>}
    <p className="dashboard-hint">Faites glisser les cartes pour les réorganiser. Les flèches permettent également de modifier leur ordre.</p>
  </section>;
}
