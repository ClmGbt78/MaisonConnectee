import { useCallback, useEffect, useMemo, useState } from "react";
import { apiFetch } from "../api";

type Notification = {
  id: number; titre: string; message: string; categorie: string;
  priorite: "info" | "success" | "warning" | "critical"; cree_le: string; lu_le: string | null;
};

export default function Notifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [filtre, setFiltre] = useState<"toutes" | "non_lues">("toutes");
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState("");
  const charger = useCallback(async () => {
    setErreur("");
    try {
      const response = await apiFetch("/api/notifications?limite=200");
      if (!response.ok) throw new Error("Impossible de charger les notifications.");
      setNotifications(await response.json());
    } catch (cause) {
      setErreur(cause instanceof Error ? cause.message : "Erreur de chargement.");
    } finally { setChargement(false); }
  }, []);
  useEffect(() => { void charger(); }, [charger]);
  const nonLues = useMemo(() => notifications.filter((item) => !item.lu_le).length, [notifications]);
  const visibles = filtre === "non_lues" ? notifications.filter((item) => !item.lu_le) : notifications;

  async function marquerCommeLue(id: number) {
    const response = await apiFetch(`/api/notifications/${id}/lue`, { method: "PATCH" });
    if (response.ok) {
      const maintenant = new Date().toISOString();
      setNotifications((items) => items.map((item) => item.id === id ? { ...item, lu_le: maintenant } : item));
    } else setErreur("Impossible de mettre cette notification à jour.");
  }
  async function marquerToutesCommeLues() {
    const response = await apiFetch("/api/notifications/lues", { method: "POST" });
    if (response.ok) {
      const maintenant = new Date().toISOString();
      setNotifications((items) => items.map((item) => ({ ...item, lu_le: item.lu_le ?? maintenant })));
    } else setErreur("Impossible de marquer les notifications comme lues.");
  }
  async function supprimer(id: number) {
    const response = await apiFetch(`/api/notifications/${id}`, { method: "DELETE" });
    if (response.ok) setNotifications((items) => items.filter((item) => item.id !== id));
    else setErreur("Impossible de supprimer cette notification.");
  }
  return <section className="notifications-page">
    <div className="section-heading">
      <div><h2>Centre de notifications</h2><p>Les événements importants de MaisonConnectée au même endroit.</p></div>
      <div className="notifications-actions"><button onClick={() => void charger()}>Actualiser</button><button onClick={() => void marquerToutesCommeLues()} disabled={nonLues === 0}>Tout marquer comme lu</button></div>
    </div>
    <div className="notifications-toolbar"><div className="notifications-filters">
      <button className={filtre === "toutes" ? "active" : ""} onClick={() => setFiltre("toutes")}>Toutes ({notifications.length})</button>
      <button className={filtre === "non_lues" ? "active" : ""} onClick={() => setFiltre("non_lues")}>Non lues ({nonLues})</button>
    </div><span>{nonLues} notification(s) non lue(s)</span></div>
    {erreur && <p className="notifications-error" role="alert">{erreur}</p>}
    {chargement ? <p className="notifications-empty">Chargement…</p> : visibles.length === 0 ? <div className="notifications-empty-state"><span>✓</span><h3>Tout est à jour</h3><p>Aucune notification {filtre === "non_lues" ? "non lue" : "pour le moment"}.</p></div> :
      <div className="notifications-list">{visibles.map((item) => <article key={item.id} className={`notification-card ${item.lu_le ? "is-read" : "is-unread"}`}>
        <span className={`notification-priority ${item.priorite}`} />
        <div className="notification-content"><div className="notification-title-row"><h3>{item.titre}</h3><span className={`notification-level ${item.priorite}`}>{item.priorite}</span></div><p>{item.message}</p><small>{new Date(item.cree_le).toLocaleString("fr-FR")} · {item.categorie}</small></div>
        <div className="notification-card-actions">{!item.lu_le && <button onClick={() => void marquerCommeLue(item.id)}>Marquer comme lue</button>}<button className="danger" onClick={() => void supprimer(item.id)}>Supprimer</button></div>
      </article>)}</div>}
  </section>;
}
