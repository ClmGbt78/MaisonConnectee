import { useCallback, useEffect, useMemo, useState } from "react";
import { apiFetch } from "../api";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import "./FonctionnalitesAvancees.css";

type Appareil = { id: string; nom: string; piece: string; type: string; allume: boolean; capacites?: string[]; etat_connexion?: string; fabricant?: string | null; modele?: string | null; reference_technique?: string | null; protocole?: string | null; adresse_materielle?: string | null; notes?: string | null };
type Mesure = { id: number; appareil_id: string; appareil_nom?: string; piece?: string; type_evenement: string; valeur: number | null; unite?: string; date_evenement: string };
type Condition = { appareil_id: string; operateur: string; seuil: number };
type Action = { appareil_id: string; allume: boolean; delai_secondes: number };
type Regle = { id: string; nom: string; active: boolean; logique: "ET" | "OU"; conditions: Condition[]; actions: Action[]; heure_debut: string | null; heure_fin: string | null; jours: number[] };

const jours = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];

export default function FonctionnalitesAvancees({ role }: { role: string }) {
  const [historique, setHistorique] = useState<Mesure[]>([]);
  const [appareils, setAppareils] = useState<Appareil[]>([]);
  const [pieces, setPieces] = useState<string[]>([]);
  const [regles, setRegles] = useState<Regle[]>([]);
  const [nom, setNom] = useState("");
  const [logique, setLogique] = useState<"ET" | "OU">("ET");
  const [conditions, setConditions] = useState<Condition[]>([{ appareil_id: "", operateur: "<", seuil: 25 }]);
  const [actions, setActions] = useState<Action[]>([{ appareil_id: "", allume: true, delai_secondes: 0 }]);
  const [heureDebut, setHeureDebut] = useState("");
  const [heureFin, setHeureFin] = useState("");
  const [joursActifs, setJoursActifs] = useState<number[]>([1,2,3,4,5,6,7]);
  const [edition, setEdition] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [erreur, setErreur] = useState("");
  const [temperatureCapteur, setTemperatureCapteur] = useState("");
  const [temperatureValeur, setTemperatureValeur] = useState("20");
  const [chargement, setChargement] = useState(false);
  const [periodeHistorique, setPeriodeHistorique] = useState<"jour"|"semaine"|"mois">("semaine");

  const charger = useCallback(async () => {
    const [h, a, r, p] = await Promise.all([
      apiFetch(`/api/domotique/historique?periode=${periodeHistorique}`),
      apiFetch("/api/domotique/inventaire"),
      apiFetch("/api/domotique/automatisations/avancees"),
      apiFetch("/api/domotique/pieces"),
    ]);
    if (h.ok) setHistorique(await h.json() as Mesure[]);
    if (a.ok) {
      const liste = await a.json() as Appareil[];
      setAppareils(liste);
      setTemperatureCapteur((old) => old || liste.find((item) => item.type === "capteur")?.id || "");
    }
    if (r.ok) setRegles(await r.json() as Regle[]);
    if (p.ok) setPieces((await p.json() as {nom:string}[]).map((item) => item.nom));
  }, [periodeHistorique]);

  useEffect(() => {
    let actif = true;
    void Promise.resolve().then(() => actif ? charger() : undefined).catch(() => { if (actif) setErreur("Impossible de charger les données avancées."); });
    return () => { actif = false; };
  }, [charger]);

  const capteurs = appareils.filter((item) => item.type === "capteur");
  const commandables = appareils.filter((item) => item.capacites?.includes("marche_arret"));
  const donneesTemperature = useMemo(() => historique.filter((item) => item.type_evenement === "temperature_mesuree").slice().reverse().map((item) => ({ date: new Date(item.date_evenement).toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }), temperature: item.valeur })), [historique]);
  const donneesLumieres = useMemo(() => historique.filter((item) => item.type_evenement === "activation_lumiere" || item.type_evenement === "extinction_lumiere").slice().reverse().map((item) => ({ date: new Date(item.date_evenement).toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }), activations: item.type_evenement === "activation_lumiere" ? 1 : 0 })), [historique]);

  const mesurerTemperature = async () => {
    if (!temperatureCapteur) return;
    setErreur(""); setMessage("");
    const response = await apiFetch(`/api/domotique/automatisations/capteurs/${encodeURIComponent(temperatureCapteur)}/mesure`, { method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({type_mesure:"temperature", valeur:Number(temperatureValeur)}) });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) { setErreur(data.detail || "Mesure impossible."); return; }
    setMessage("Mesure de température enregistrée."); await charger();
  };

  const sauvegarderRegle = async (event: React.FormEvent) => {
    event.preventDefault(); setChargement(true); setErreur(""); setMessage("");
    const payload = { nom: nom.trim(), logique, conditions, actions, heure_debut: heureDebut || null, heure_fin: heureFin || null, jours: joursActifs };
    try {
      const response = await apiFetch(edition ? `/api/domotique/automatisations/avancees/${edition}` : "/api/domotique/automatisations/avancees", { method: edition ? "PUT" : "POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Enregistrement impossible.");
      setRegles((old) => edition ? old.map((item) => item.id === edition ? data : item) : [...old, data]);
      reinitialiser(); setMessage("Automatisation avancée enregistrée.");
    } catch (e) { setErreur(e instanceof Error ? e.message : "Erreur d'enregistrement."); }
    finally { setChargement(false); }
  };

  const reinitialiser = () => { setEdition(null); setNom(""); setLogique("ET"); setConditions([{appareil_id:capteurs[0]?.id || "",operateur:"<",seuil:25}]); setActions([{appareil_id:commandables[0]?.id || "",allume:true,delai_secondes:0}]); setHeureDebut(""); setHeureFin(""); setJoursActifs([1,2,3,4,5,6,7]); };
  const editerRegle = (item: Regle) => { setEdition(item.id); setNom(item.nom); setLogique(item.logique); setConditions(item.conditions); setActions(item.actions); setHeureDebut(item.heure_debut || ""); setHeureFin(item.heure_fin || ""); setJoursActifs(item.jours); };
  const basculerRegle = async (item: Regle) => {
    const response = await apiFetch(`/api/domotique/automatisations/avancees/${item.id}`, {method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({active:!item.active})});
    if (response.ok) { const data = await response.json(); setRegles((old)=>old.map((r)=>r.id===item.id?data:r)); }
  };
  const supprimerRegle = async (item: Regle) => {
    if (!window.confirm(`Supprimer « ${item.nom} » ?`)) return;
    const response = await apiFetch(`/api/domotique/automatisations/avancees/${item.id}`,{method:"DELETE"});
    if (response.ok) setRegles((old)=>old.filter((r)=>r.id!==item.id));
  };

  const enregistrerInfos = async (appareil: Appareil, event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(["fabricant","modele","reference_technique","protocole","adresse_materielle","notes"].map((key)=>[key, String(form.get(key)||"").trim()||null]));
    const response = await apiFetch(`/api/domotique/inventaire/${encodeURIComponent(appareil.id)}`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
    if (!response.ok) { setErreur("Impossible d'enregistrer les informations techniques."); return; }
    setMessage("Inventaire mis à jour."); await charger();
  };
  const affecterPiece = async (appareil: Appareil, piece: string) => {
    const response = await apiFetch(`/api/domotique/appareils/${encodeURIComponent(appareil.id)}/piece`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({piece})});
    if (!response.ok) setErreur("Impossible de modifier la pièce."); else await charger();
  };
  const commandeRapide = async (appareil: Appareil) => {
    const response = await apiFetch(`/api/domotique/appareils/${encodeURIComponent(appareil.id)}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({allume:!appareil.allume})});
    if (response.ok) await charger(); else setErreur("Commande impossible.");
  };

  return <div className="advanced-page">
    <section className="advanced-panel">
      <div className="advanced-heading"><div><h2>Historique et statistiques</h2><p>Évolution des températures mesurées et événements lumineux.</p></div>
        <select value={periodeHistorique} onChange={(e)=>setPeriodeHistorique(e.target.value as "jour"|"semaine"|"mois")}><option value="jour">Jour</option><option value="semaine">Semaine</option><option value="mois">Mois</option></select>
      </div>
      <div className="advanced-charts">
        <article><h3>Températures (°C)</h3>{donneesTemperature.length ? <ResponsiveContainer width="100%" height={230}><LineChart data={donneesTemperature}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="date"/><YAxis/><Tooltip/><Line type="monotone" dataKey="temperature" name="Température" stroke="#f59e0b" dot={false}/></LineChart></ResponsiveContainer> : <p className="advanced-muted">Aucune mesure de température sur cette période.</p>}</article>
        <article><h3>Activations des lumières</h3>{donneesLumieres.length ? <ResponsiveContainer width="100%" height={230}><LineChart data={donneesLumieres}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="date"/><YAxis allowDecimals={false}/><Tooltip/><Line type="stepAfter" dataKey="activations" name="Activation" stroke="#38bdf8" dot={false}/></LineChart></ResponsiveContainer> : <p className="advanced-muted">Aucune activation enregistrée sur cette période.</p>}</article>
      </div>
      <div className="advanced-inline-form"><label>Capteur de température<select value={temperatureCapteur} onChange={(e)=>setTemperatureCapteur(e.target.value)}>{capteurs.map((c)=><option key={c.id} value={c.id}>{c.nom}</option>)}</select></label><label>Température (°C)<input type="number" min="-20" max="80" step="0.1" value={temperatureValeur} onChange={(e)=>setTemperatureValeur(e.target.value)}/></label><button type="button" onClick={()=>void mesurerTemperature()} disabled={!temperatureCapteur}>Enregistrer une mesure simulée</button></div>
      <p className="advanced-muted">Les températures sont des mesures de capteurs. L'interface permet d'enregistrer une mesure simulée tant qu'aucun capteur physique n'est configuré.</p>
      <div className="advanced-history-list">{historique.slice(0,12).map((item)=><div key={item.id}><span>{item.appareil_nom || item.appareil_id}</span><strong>{item.type_evenement === "activation_lumiere" ? "Allumage" : item.type_evenement === "extinction_lumiere" ? "Extinction" : item.type_evenement === "temperature_mesuree" ? `${item.valeur} °C` : item.type_evenement}</strong><time>{new Date(item.date_evenement).toLocaleString("fr-FR")}</time></div>)}</div>
    </section>

    <section className="advanced-panel">
      <h2>Automatisations avancées</h2><p>Combine plusieurs mesures de capteurs et déclenche plusieurs commandes, immédiatement ou après un délai.</p>
      <div className="advanced-rule-list">{regles.map((item)=><article key={item.id}><div><strong>{item.nom}</strong><span>{item.conditions.length} condition(s) · {item.actions.length} action(s) · {item.logique}</span><small>{item.heure_debut && item.heure_fin ? `Plage ${item.heure_debut}–${item.heure_fin}` : "Toute la journée"}</small></div><button type="button" onClick={()=>void basculerRegle(item)}>{item.active?"Désactiver":"Activer"}</button>{role==="admin" && <><button type="button" onClick={()=>editerRegle(item)}>Modifier</button><button type="button" onClick={()=>void supprimerRegle(item)}>Supprimer</button></>}</article>)}</div>
      {role==="admin" && <form className="advanced-form" onSubmit={(e)=>void sauvegarderRegle(e)}>
        <h3>{edition?"Modifier la règle":"Créer une règle avancée"}</h3>
        <label>Nom<input value={nom} onChange={(e)=>setNom(e.target.value)} required maxLength={80}/></label>
        <label>Logique des conditions<select value={logique} onChange={(e)=>setLogique(e.target.value as "ET"|"OU")}><option value="ET">Toutes les conditions (ET)</option><option value="OU">Au moins une condition (OU)</option></select></label>
        <div className="advanced-builder"><strong>Conditions</strong>{conditions.map((condition,index)=><div className="advanced-builder-row" key={index}><select aria-label="Capteur" value={condition.appareil_id} onChange={(e)=>setConditions((old)=>old.map((v,i)=>i===index?{...v,appareil_id:e.target.value}:v))}><option value="">Capteur…</option>{capteurs.map((a)=><option key={a.id} value={a.id}>{a.nom}</option>)}</select><select aria-label="Comparaison" value={condition.operateur} onChange={(e)=>setConditions((old)=>old.map((v,i)=>i===index?{...v,operateur:e.target.value}:v))}>{["<","<=",">",">=","=","!="].map((op)=><option key={op}>{op}</option>)}</select><input aria-label="Seuil" type="number" step="0.1" value={condition.seuil} onChange={(e)=>setConditions((old)=>old.map((v,i)=>i===index?{...v,seuil:Number(e.target.value)}:v))}/><button type="button" onClick={()=>setConditions((old)=>old.filter((_,i)=>i!==index))} disabled={conditions.length===1}>Retirer</button></div>)}<button type="button" onClick={()=>setConditions((old)=>[...old,{appareil_id:capteurs[0]?.id||"",operateur:"<",seuil:25}])}>Ajouter une condition</button></div>
        <div className="advanced-builder"><strong>Actions</strong>{actions.map((action,index)=><div className="advanced-builder-row" key={index}><select aria-label="Appareil" value={action.appareil_id} onChange={(e)=>setActions((old)=>old.map((v,i)=>i===index?{...v,appareil_id:e.target.value}:v))}><option value="">Appareil…</option>{commandables.map((a)=><option key={a.id} value={a.id}>{a.nom}</option>)}</select><select aria-label="État demandé" value={String(action.allume)} onChange={(e)=>setActions((old)=>old.map((v,i)=>i===index?{...v,allume:e.target.value==="true"}:v))}><option value="true">Allumer</option><option value="false">Éteindre</option></select><label>Délai (s)<input type="number" min="0" max="86400" value={action.delai_secondes} onChange={(e)=>setActions((old)=>old.map((v,i)=>i===index?{...v,delai_secondes:Number(e.target.value)}:v))}/></label><button type="button" onClick={()=>setActions((old)=>old.filter((_,i)=>i!==index))} disabled={actions.length===1}>Retirer</button></div>)}<button type="button" onClick={()=>setActions((old)=>[...old,{appareil_id:commandables[0]?.id||"",allume:true,delai_secondes:0}])}>Ajouter une action</button></div>
        <div className="advanced-builder-row"><label>Début<input type="time" value={heureDebut} onChange={(e)=>setHeureDebut(e.target.value)}/></label><label>Fin<input type="time" value={heureFin} onChange={(e)=>setHeureFin(e.target.value)}/></label></div>
        <div className="advanced-days">{jours.map((day,index)=><label key={day}><input type="checkbox" checked={joursActifs.includes(index+1)} onChange={(e)=>setJoursActifs((old)=>e.target.checked?[...old,index+1]:old.filter((v)=>v!==index+1))}/>{day}</label>)}</div>
        <button type="submit" disabled={chargement||!nom.trim()||!conditions.every((c)=>c.appareil_id)||!actions.every((a)=>a.appareil_id)||!joursActifs.length}>{chargement?"Enregistrement…":edition?"Enregistrer":"Créer l'automatisation"}</button>{edition&&<button type="button" onClick={reinitialiser}>Annuler</button>}
      </form>}
    </section>

    <section className="advanced-panel">
      <div className="advanced-heading"><div><h2>Inventaire des appareils</h2><p>État, caractéristiques techniques et affectation à une pièce.</p></div><span>{appareils.length} équipements</span></div>
      <div className="advanced-device-list">{appareils.map((item)=><article key={item.id}>
        <div className="advanced-device-title"><div><strong>{item.nom}</strong><span>{item.type} · {item.id}</span></div><span className={item.etat_connexion==="connecte"?"advanced-connected":"advanced-simulated"}>{item.etat_connexion==="connecte"?"Connecté":"Simulation / non vérifié"}</span></div>
        <div className="advanced-device-actions"><label>Pièce<select value={item.piece} disabled={role!=="admin"} onChange={(e)=>void affecterPiece(item,e.target.value)}>{[...new Set([...pieces,item.piece])].map((p)=><option key={p}>{p}</option>)}</select></label>{item.capacites?.includes("marche_arret")&&<button type="button" onClick={()=>void commandeRapide(item)}>{item.allume?"Éteindre":"Allumer"}</button>}</div>
        {role==="admin"&&<form className="advanced-tech-form" onSubmit={(e)=>void enregistrerInfos(item,e)}><label>Fabricant<input name="fabricant" defaultValue={item.fabricant||""}/></label><label>Modèle<input name="modele" defaultValue={item.modele||""}/></label><label>Référence<input name="reference_technique" defaultValue={item.reference_technique||""}/></label><label>Protocole<input name="protocole" defaultValue={item.protocole||""}/></label><label>Adresse matérielle<input name="adresse_materielle" defaultValue={item.adresse_materielle||""}/></label><label>Notes<input name="notes" defaultValue={item.notes||""}/></label><button type="submit">Enregistrer les informations</button></form>}
      </article>)}</div>
      <p className="advanced-muted">L'état de connexion est indiqué comme simulation / non vérifié tant qu'un pilote matériel ne fournit pas de véritable signal de présence. Aucune connexion physique n'est inventée.</p>
    </section>
    {(message||erreur)&&<p className={erreur?"advanced-error":"advanced-success"} role={erreur?"alert":"status"}>{erreur||message}</p>}
  </div>;
}
