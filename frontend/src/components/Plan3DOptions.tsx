import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../api";
import "./Plan3DOptions.css";

type Piece = { id: string; nom: string };
type Appareil = { id: string; nom: string; piece: string; type: string; allume?: boolean };
type Cible = { id: string; allume: boolean };
type Finition = { materiau: string; couleur: string };
type Finitions = { piece_id: string; mur_interieur: Finition; mur_exterieur: Finition; sol: Finition; plafond: Finition };
type Scenario = { id: number; nom: string; description: string; portee: "maison" | "selection"; appareils: Cible[] };

const defaut: Finitions = {
  piece_id: "",
  mur_interieur: { materiau: "peinture", couleur: "#e0e7ef" },
  mur_exterieur: { materiau: "enduit", couleur: "#d6d3d1" },
  sol: { materiau: "carrelage", couleur: "#b8c7d8" },
  plafond: { materiau: "platre", couleur: "#f1f5f9" },
};
const materiaux = ["peinture", "papier_peint", "brique", "pierre", "bois", "enduit", "carrelage", "parquet", "beton", "moquette", "platre"];

export default function Plan3DOptions({ role, onFinitionChange }: { role: string; onFinitionChange: (pieceId: string, finitions: Finitions) => void }) {
  const [pieces, setPieces] = useState<Piece[]>([]);
  const [appareils, setAppareils] = useState<Appareil[]>([]);
  const [finitions, setFinitions] = useState<Finitions[]>([]);
  const [pieceId, setPieceId] = useState("");
  const [editionLocale, setEditionLocale] = useState<Finitions | null>(null);
  const edition = editionLocale ?? finitions.find((item) => item.piece_id === pieceId) ?? { ...defaut, piece_id: pieceId };
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [nom, setNom] = useState("");
  const [description, setDescription] = useState("");
  const [portee, setPortee] = useState<"maison" | "selection">("maison");
  const [cibles, setCibles] = useState<Cible[]>([]);
  const [scenarioEditionId, setScenarioEditionId] = useState<number | null>(null);
  const [erreur, setErreur] = useState("");
  const [message, setMessage] = useState("");

  const charger = useCallback(async () => {
    const [p, a, f, s] = await Promise.all([
      apiFetch("/api/domotique/plan-3d"),
      apiFetch("/api/domotique/appareils"),
      apiFetch("/api/domotique/plan-3d/finitions"),
      apiFetch("/api/domotique/plan-3d/scenarios"),
    ]);
    if (p.ok) {
      const data = await p.json() as Piece[];
      setPieces(data);
      if (data.length) setPieceId((old) => old || data[0].id);
    }
    if (a.ok) setAppareils((await a.json() as Appareil[]).filter((item) => item.type !== "capteur"));
    if (f.ok) {
      const data = await f.json() as Finitions[];
      setFinitions(data);
      data.forEach((item) => onFinitionChange(item.piece_id, item));
    }
    if (s.ok) setScenarios(await s.json() as Scenario[]);
  }, [onFinitionChange]);

  useEffect(() => {
    void charger().catch(() => setErreur("Impossible de charger les réglages 3D."));
  }, [charger]);

  const modifierFinition = (zone: keyof Omit<Finitions, "piece_id">, changement: Partial<Finition>) => {
    setEditionLocale((old) => {
      const base = old ?? edition;
      return { ...base, [zone]: { ...base[zone], ...changement } };
    });
  };

  const enregistrerFinitions = async () => {
    const response = await apiFetch(`/api/domotique/plan-3d/${pieceId}/finitions`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mur_interieur: edition.mur_interieur, mur_exterieur: edition.mur_exterieur, sol: edition.sol, plafond: edition.plafond }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) { setErreur(data.detail || "Enregistrement des finitions impossible."); return; }
    const valeur = data as Finitions;
    setFinitions((old) => [...old.filter((item) => item.piece_id !== pieceId), valeur]);
    setEditionLocale(valeur);
    onFinitionChange(pieceId, valeur);
    setMessage("Finitions enregistrées pour cette pièce.");
    setErreur("");
  };

  const basculerCible = (id: string, allume: boolean) => {
    setCibles((old) => [...old.filter((item) => item.id !== id), { id, allume }]);
  };

  const enregistrerScenario = async () => {
    const appareilsScenario = portee === "maison"
      ? appareils.map((item) => cibles.find((c) => c.id === item.id) ?? { id: item.id, allume: false })
      : cibles;
    const response = await apiFetch("/api/domotique/plan-3d/scenarios", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nom, description, portee, appareils: appareilsScenario }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) { setErreur(data.detail || "Création du scénario impossible."); return; }
    setScenarios((old) => [...old, data as Scenario]);
    setNom("");
    setDescription("");
    setCibles([]);
    setMessage("Scénario enregistré.");
    setErreur("");
  };

  const appliquer = async (scenario: Scenario) => {
    const response = await apiFetch(`/api/domotique/plan-3d/scenarios/${scenario.id}/appliquer`, { method: "POST" });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) { setErreur(data.detail || "Application du scénario impossible."); return; }
    setMessage(`Scénario appliqué : ${data.appliques?.length ?? 0} appareil(s) commandé(s), ${data.erreurs?.length ?? 0} erreur(s).`);
    setErreur(data.erreurs?.length ? data.erreurs.map((item: { appareil_id: string; detail: string }) => `${item.appareil_id} : ${item.detail}`).join(" · ") : "");
  };

  const editerScenario = (scenario: Scenario) => {
    setScenarioEditionId(scenario.id);
    setNom(scenario.nom);
    setDescription(scenario.description);
    setPortee(scenario.portee);
    setCibles(scenario.appareils);
  };

  const supprimer = async (scenario: Scenario) => {
    const response = await apiFetch(`/api/domotique/plan-3d/scenarios/${scenario.id}`, { method: "DELETE" });
    if (response.ok) setScenarios((old) => old.filter((item) => item.id !== scenario.id));
    else setErreur("Suppression du scénario impossible.");
  };

  return <section className="plan3d-options">
    <section className="plan3d-options-section">
      <h3>Finitions de la maison</h3>
      <p>Personnalise les matériaux et les couleurs pièce par pièce. Les murs intérieurs et extérieurs, le sol et le plafond disposent de réglages distincts.</p>
      <div className="plan3d-options-grid">
        <label>Pièce<select value={pieceId} onChange={(event) => { setPieceId(event.target.value); setEditionLocale(null); }}>
          {pieces.map((piece) => <option key={piece.id} value={piece.id}>{piece.nom}</option>)}
        </select></label>
        {(["mur_interieur", "mur_exterieur", "sol", "plafond"] as const).map((zone) => <div className="plan3d-finish-control" key={zone}>
          <strong>{{ mur_interieur: "Murs intérieurs", mur_exterieur: "Murs extérieurs", sol: "Sol", plafond: "Plafond" }[zone]}</strong>
          <label>Matériau<select value={edition[zone].materiau} onChange={(event) => modifierFinition(zone, { materiau: event.target.value })}>
            {materiaux.map((item) => <option key={item} value={item}>{item.replace("_", " ")}</option>)}
          </select></label>
          <label>Couleur<input type="color" value={edition[zone].couleur} onChange={(event) => modifierFinition(zone, { couleur: event.target.value })} /></label>
          <span className="plan3d-material-swatch" style={{ background: edition[zone].couleur }} />
        </div>)}
      </div>
      {role === "admin" && <button type="button" disabled={!pieceId} onClick={() => void enregistrerFinitions()}>Enregistrer les finitions</button>}
    </section>
    <section className="plan3d-options-section">
      <h3>Scénarios domotiques 3D</h3>
      <p>Choisis une portée globale pour toute la maison ou une sélection précise d'appareils. Les capteurs restent en lecture seule.</p>
      {scenarios.map((scenario) => <div className="plan3d-scenario-row" key={scenario.id}>
        <span><strong>{scenario.nom}</strong><small>{scenario.description || (scenario.portee === "maison" ? "Toute la maison" : `${scenario.appareils.length} appareil(s) sélectionné(s)`)}</small></span>
        <button type="button" onClick={() => void appliquer(scenario)}>Appliquer</button>
        {role === "admin" && <button type="button" onClick={() => void supprimer(scenario)}>Supprimer</button>}
      </div>)}
      {role === "admin" && <>
        <div className="plan3d-options-grid">
          <label>Nom du scénario<input value={nom} maxLength={80} onChange={(event) => setNom(event.target.value)} placeholder="Ex. Départ de la maison" /></label>
          <label>Description<input value={description} maxLength={240} onChange={(event) => setDescription(event.target.value)} placeholder="Description facultative" /></label>
          <label>Portée<select value={portee} onChange={(event) => setPortee(event.target.value as "maison" | "selection")}><option value="maison">Toute la maison</option><option value="selection">Appareils sélectionnés</option></select></label>
        </div>
        <div className="plan3d-device-list">{appareils.map((appareil) => <label key={appareil.id}>
          <input type="checkbox" checked={portee === "maison" || cibles.some((item) => item.id === appareil.id)} onChange={(event) => event.target.checked ? basculerCible(appareil.id, appareil.allume ?? true) : setCibles((old) => old.filter((item) => item.id !== appareil.id))} />
          {appareil.nom} · {appareil.piece}
          <select aria-label={`État de ${appareil.nom}`} value={String(cibles.find((item) => item.id === appareil.id)?.allume ?? false)} onChange={(event) => basculerCible(appareil.id, event.target.value === "true")}>
            <option value="true">Allumé</option><option value="false">Éteint</option>
          </select>
        </label>)}</div>
        <button type="button" disabled={!nom.trim() || (portee === "selection" && !cibles.length)} onClick={() => void enregistrerScenario()}>{scenarioEditionId === null ? "Créer le scénario" : "Enregistrer les modifications"}</button>
        {scenarioEditionId !== null && <button type="button" onClick={() => { setScenarioEditionId(null); setNom(""); setDescription(""); setCibles([]); }}>Annuler la modification</button>}
      </>}
    </section>
    {erreur && <p className="plan3d-error" role="alert">{erreur}</p>}
    {message && <p className="plan3d-success" role="status">{message}</p>}
  </section>;
}
