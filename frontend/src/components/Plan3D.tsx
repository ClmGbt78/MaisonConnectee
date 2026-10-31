import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Canvas } from "@react-three/fiber";
import { Html, OrbitControls } from "@react-three/drei";
import { Shape, Path, ExtrudeGeometry } from "three";
import { apiFetch } from "../api";
import "./Plan3D.css";

type PiecePlan = {
  id: string;
  nom: string;
  couleur: string;
  position_x: number;
  position_z: number;
  largeur: number;
  profondeur: number;
  hauteur: number;
  etage: number;
  ouvertures: Ouverture[];
};

type Ouverture = { id: number; type: "porte" | "fenetre"; mur: "nord" | "sud" | "est" | "ouest"; position: number; largeur: number; hauteur: number; hauteur_appui: number; sens_ouverture: "gauche" | "droite"; angle_ouverture: number };
type BrouillonOuverture = Omit<Ouverture, "id">;
type Brouillon = Pick<PiecePlan, "position_x" | "position_z" | "largeur" | "profondeur" | "hauteur" | "etage">;

function creerBrouillon(piece: PiecePlan | undefined): Brouillon | null {
  if (!piece) return null;
  return {
    position_x: piece.position_x,
    position_z: piece.position_z,
    largeur: piece.largeur,
    profondeur: piece.profondeur,
    hauteur: piece.hauteur,
    etage: piece.etage,
  };
}

function MurAvecOuvertures({ piece, pieces, mur, ouvertures, materiau, nuit, deplacer, validerDeplacement, peutModifier }: {
  piece: PiecePlan;
  pieces: PiecePlan[];
  mur: Ouverture["mur"];
  ouvertures: Ouverture[];
  materiau: { color: string; transparent: boolean; opacity: number; roughness: number; depthWrite: boolean };
  nuit: boolean;
  deplacer: (pieceId: string, ouvertureId: number, position: number) => void;
  validerDeplacement: (piece: PiecePlan, ouverture: Ouverture, position: number) => void;
  peutModifier: boolean;
}) {
  const longueur = mur === "nord" || mur === "sud" ? piece.largeur : piece.profondeur;
  const geometry = useMemo(() => {
    const forme = new Shape();
    forme.moveTo(-longueur / 2, 0);
    forme.lineTo(longueur / 2, 0);
    forme.lineTo(longueur / 2, piece.hauteur);
    forme.lineTo(-longueur / 2, piece.hauteur);
    forme.closePath();
    ouvertures.forEach((ouverture) => {
      const trou = new Path();
      const gauche = ouverture.position - ouverture.largeur / 2;
      const droite = ouverture.position + ouverture.largeur / 2;
      const bas = ouverture.hauteur_appui;
      const haut = bas + ouverture.hauteur;
      trou.moveTo(gauche, bas);
      trou.lineTo(gauche, haut);
      trou.lineTo(droite, haut);
      trou.lineTo(droite, bas);
      trou.closePath();
      forme.holes.push(trou);
    });
    return new ExtrudeGeometry(forme, { depth: 0.14, bevelEnabled: false, curveSegments: 8 });
  }, [longueur, piece.hauteur, ouvertures]);
  const rotation = mur === "est" ? Math.PI / 2 : mur === "ouest" ? -Math.PI / 2 : 0;
  const position: [number, number, number] = [
    mur === "est" ? piece.largeur / 2 : mur === "ouest" ? -piece.largeur / 2 : 0,
    0,
    mur === "sud" ? piece.profondeur / 2 : mur === "nord" ? -piece.profondeur / 2 : 0,
  ];
  return <group position={position} rotation={[0, rotation, 0]}>
    <mesh castShadow receiveShadow>
      <primitive object={geometry} attach="geometry" />
      <meshStandardMaterial {...materiau} side={2} />
    </mesh>
    {ouvertures.map((ouverture) => {
      const pieceOuverture = pieces.find((candidate) => candidate.ouvertures?.some((item) => item.id === ouverture.id)) ?? piece;
      const fenetre = ouverture.type === "fenetre";
      const positionMin = -longueur / 2 + ouverture.largeur / 2;
      const positionMax = longueur / 2 - ouverture.largeur / 2;
      const largeurCadre = 0.055;
      const profondeurCadre = 0.055;
      const hauteurCadre = 0.055;
      const largeurInterieure = Math.max(0.05, ouverture.largeur - largeurCadre * 2);
      const hauteurInterieure = Math.max(0.05, ouverture.hauteur - hauteurCadre * 2);
      const materiauCadre = nuit ? "#c3cedb" : "#f8fafc";
      return (
        <group key={ouverture.id} position={[ouverture.position, ouverture.hauteur_appui, 0.075]}>
          {peutModifier && <Html position={[0, ouverture.hauteur + 0.16, 0.12]} center transform distanceFactor={9} style={{ pointerEvents: "auto", width: "112px" }}>
            <input
              aria-label={`Déplacer ${fenetre ? "la fenêtre" : "la porte"} sur le mur`}
              title="Faire glisser pour déplacer sur le mur"
              type="range"
              min={positionMin}
              max={positionMax}
              step={0.05}
              value={Math.min(positionMax, Math.max(positionMin, ouverture.position))}
              onChange={(event) => deplacer(pieceOuverture.id, ouverture.id, Number(event.target.value))}
              onPointerUp={(event) => validerDeplacement(pieceOuverture, ouverture, Number((event.currentTarget as HTMLInputElement).value))}
              onKeyUp={(event) => {
                if (event.key.startsWith("Arrow")) validerDeplacement(pieceOuverture, ouverture, Number((event.currentTarget as HTMLInputElement).value));
              }}
              style={{ width: "112px", accentColor: "#38bdf8", cursor: "ew-resize" }}
            />
          </Html>}
          <mesh position={[-ouverture.largeur / 2 + largeurCadre / 2, ouverture.hauteur / 2, 0]} castShadow>
            <boxGeometry args={[largeurCadre, ouverture.hauteur, profondeurCadre]} />
            <meshStandardMaterial color={materiauCadre} roughness={0.55} />
          </mesh>
          <mesh position={[ouverture.largeur / 2 - largeurCadre / 2, ouverture.hauteur / 2, 0]} castShadow>
            <boxGeometry args={[largeurCadre, ouverture.hauteur, profondeurCadre]} />
            <meshStandardMaterial color={materiauCadre} roughness={0.55} />
          </mesh>
          <mesh position={[0, ouverture.hauteur - hauteurCadre / 2, 0]}>
            <boxGeometry args={[ouverture.largeur, hauteurCadre, profondeurCadre]} />
            <meshStandardMaterial color={materiauCadre} roughness={0.55} />
          </mesh>
          {fenetre ? (
            <>
              <mesh position={[0, ouverture.hauteur / 2, -0.006]}>
                <boxGeometry args={[largeurInterieure, hauteurInterieure, 0.025]} />
                <meshPhysicalMaterial color={nuit ? "#72a9d4" : "#9bd8f5"} transparent opacity={0.48} roughness={0.12} metalness={0.08} />
              </mesh>
              <mesh position={[0, ouverture.hauteur_appui === 0 ? 0.035 : 0, 0]}>
                <boxGeometry args={[ouverture.largeur, hauteurCadre, profondeurCadre]} />
                <meshStandardMaterial color={materiauCadre} roughness={0.55} />
              </mesh>
              <mesh position={[0, ouverture.hauteur / 2, 0.012]}>
                <boxGeometry args={[0.035, hauteurInterieure, 0.035]} />
                <meshStandardMaterial color={materiauCadre} roughness={0.55} />
              </mesh>
            </>
          ) : (
            <group position={[ouverture.sens_ouverture === "gauche" ? -ouverture.largeur / 2 + largeurCadre : ouverture.largeur / 2 - largeurCadre, 0, 0.025]} rotation={[0, (ouverture.sens_ouverture === "gauche" ? -1 : 1) * ouverture.angle_ouverture * Math.PI / 180, 0]} scale={[ouverture.sens_ouverture === "gauche" ? 1 : -1, 1, 1]}>
              <mesh position={[largeurInterieure / 2, ouverture.hauteur / 2, 0]} castShadow>
                <boxGeometry args={[largeurInterieure, hauteurInterieure, 0.035]} />
                <meshStandardMaterial color={nuit ? "#795b43" : "#9b704e"} roughness={0.72} />
              </mesh>
              <mesh position={[largeurInterieure * 0.72, ouverture.hauteur / 2, 0.021]}>
                <sphereGeometry args={[0.035, 10, 8]} />
                <meshStandardMaterial color={nuit ? "#d6dce4" : "#d2a84b"} metalness={0.65} roughness={0.3} />
              </mesh>
            </group>
          )}
        </group>
      );
    })}
  </group>;
}

function mursCoincidents(piece: PiecePlan, mur: Ouverture["mur"], pieces: PiecePlan[]) {
  const horizontal = mur === "nord" || mur === "sud";
  const bord = mur === "nord"
    ? piece.position_z - piece.profondeur / 2
    : mur === "sud"
      ? piece.position_z + piece.profondeur / 2
      : mur === "ouest"
        ? piece.position_x - piece.largeur / 2
        : piece.position_x + piece.largeur / 2;
  const debut = horizontal ? piece.position_x - piece.largeur / 2 : piece.position_z - piece.profondeur / 2;
  const fin = horizontal ? piece.position_x + piece.largeur / 2 : piece.position_z + piece.profondeur / 2;
  const epsilon = 0.015;
  return pieces.find((autre) => {
    if (autre.id === piece.id || autre.etage !== piece.etage || Math.abs(autre.hauteur - piece.hauteur) > epsilon) return false;
    const autreBord = mur === "nord"
      ? autre.position_z + autre.profondeur / 2
      : mur === "sud"
        ? autre.position_z - autre.profondeur / 2
        : mur === "ouest"
          ? autre.position_x + autre.largeur / 2
          : autre.position_x - autre.largeur / 2;
    const autreDebut = horizontal ? autre.position_x - autre.largeur / 2 : autre.position_z - autre.profondeur / 2;
    const autreFin = horizontal ? autre.position_x + autre.largeur / 2 : autre.position_z + autre.profondeur / 2;
    return Math.abs(bord - autreBord) <= epsilon
      && Math.abs(debut - autreDebut) <= epsilon
      && Math.abs(fin - autreFin) <= epsilon;
  });
}

function SolEtMurs({ piece, pieces, transparence, nuit, deplacer, validerDeplacement, peutModifier }: {
  piece: PiecePlan; pieces: PiecePlan[]; transparence: number; nuit: boolean; peutModifier: boolean;
  deplacer: (pieceId: string, ouvertureId: number, position: number) => void;
  validerDeplacement: (piece: PiecePlan, ouverture: Ouverture, position: number) => void;
}) {
  const opacite = transparence / 100;
  const materiauMur = { color: nuit ? "#8293aa" : "#e0e7ef", transparent: opacite < 1, opacity: opacite, roughness: 0.82, depthWrite: opacite >= 1 };
  const ouvertures = piece.ouvertures ?? [];
  return (
    <group position={[piece.position_x, piece.etage * 3.25, piece.position_z]}>
      <mesh position={[0, 0.025, 0]} receiveShadow>
        <boxGeometry args={[piece.largeur, 0.05, piece.profondeur]} />
        <meshStandardMaterial color={piece.couleur || "#b8c7d8"} roughness={0.9} />
      </mesh>
      {(["nord", "sud", "est", "ouest"] as const).map((mur) => {
        const voisin = mursCoincidents(piece, mur, pieces);
        if (voisin && piece.id.localeCompare(voisin.id) > 0) return null;
        const oppose: Record<Ouverture["mur"], Ouverture["mur"]> = { nord: "sud", sud: "nord", est: "ouest", ouest: "est" };
        const ouverturesMur = ouvertures.filter((ouverture) => ouverture.mur === mur);
        const ouverturesVoisin = voisin
          ? (voisin.ouvertures ?? []).filter((ouverture) => ouverture.mur === oppose[mur]).map((ouverture) => ({ ...ouverture, position: ouverture.position }))
          : [];
        return <MurAvecOuvertures key={mur} piece={piece} pieces={pieces} mur={mur} ouvertures={[...ouverturesMur, ...ouverturesVoisin]} materiau={materiauMur} nuit={nuit} deplacer={deplacer} validerDeplacement={validerDeplacement} peutModifier={peutModifier} />;
      })}
      <Html position={[0, 0.18, 0]} center distanceFactor={13} style={{ pointerEvents: "none", whiteSpace: "nowrap" }}>
        <span className="plan3d-room-label">{piece.nom}</span>
      </Html>
    </group>
  );
}

export default function Plan3D({ role }: { role: string }) {
  const [pieces, setPieces] = useState<PiecePlan[]>([]);
  const [selection, setSelection] = useState("");
  const [brouillon, setBrouillon] = useState<Brouillon | null>(null);
  const [ouvertureBrouillon, setOuvertureBrouillon] = useState<BrouillonOuverture>({ type: "porte", mur: "nord", position: 0, largeur: 0.9, hauteur: 2.1, hauteur_appui: 0, sens_ouverture: "gauche", angle_ouverture: 90 });
  const [ouvertureEditionId, setOuvertureEditionId] = useState<number | null>(null);
  const [etageAffiche, setEtageAffiche] = useState("0");
  const [transparence, setTransparence] = useState(82);
  const [ambiance, setAmbiance] = useState<"jour" | "nuit">("jour");
  const [reset, setReset] = useState(0);
  const [chargement, setChargement] = useState(true);
  const [enregistrement, setEnregistrement] = useState(false);
  const [erreur, setErreur] = useState("");
  const [message, setMessage] = useState("");
  const nuit = ambiance === "nuit";
  const pieceSelectionnee = pieces.find((piece) => piece.id === selection) ?? null;
  const etages = useMemo(() => [...new Set(pieces.map((piece) => piece.etage))].sort((a, b) => a - b), [pieces]);

  const charger = useCallback(async () => {
    try {
      const response = await apiFetch("/api/domotique/plan-3d");
      if (!response.ok) throw new Error("Impossible de charger la géométrie des pièces.");
      const donnees: PiecePlan[] = await response.json();
      setPieces(donnees);
      const premierePiece = donnees[0];
      setSelection(premierePiece?.id ?? "");
      setBrouillon(creerBrouillon(premierePiece));
      setErreur("");
    } catch (error) {
      setErreur(error instanceof Error ? error.message : "Erreur de chargement du plan.");
    } finally {
      setChargement(false);
    }
  }, []);

  useEffect(() => {
    let actif = true;
    apiFetch("/api/domotique/plan-3d")
      .then(async (response) => {
        if (!response.ok) throw new Error("Impossible de charger la géométrie des pièces.");
        return await response.json() as PiecePlan[];
      })
      .then((donnees) => {
        if (!actif) return;
        setPieces(donnees);
        const premierePiece = donnees[0];
        setSelection(premierePiece?.id ?? "");
        setBrouillon(creerBrouillon(premierePiece));
        setErreur("");
      })
      .catch((error: unknown) => {
        if (!actif) return;
        setErreur(error instanceof Error ? error.message : "Erreur de chargement du plan.");
      })
      .finally(() => {
        if (actif) setChargement(false);
      });
    return () => { actif = false; };
  }, []);

  const modifier = (champ: keyof Brouillon, valeur: number) => {
    setBrouillon((ancien) => ancien ? { ...ancien, [champ]: valeur } : ancien);
    setMessage("");
  };

  const enregistrer = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!pieceSelectionnee || !brouillon) return;
    setEnregistrement(true);
    setErreur("");
    setMessage("");
    try {
      const response = await apiFetch(`/api/domotique/plan-3d/${pieceSelectionnee.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(brouillon),
      });
      const donnees = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(donnees.detail || "Impossible d'enregistrer cette pièce.");
      setPieces((anciennes) => anciennes.map((piece) => piece.id === donnees.id ? donnees : piece));
      setMessage("Dimensions et position enregistrées.");
    } catch (error) {
      setErreur(error instanceof Error ? error.message : "Erreur d'enregistrement.");
    } finally {
      setEnregistrement(false);
    }
  };

  const enregistrerOuverture = async () => {
    if (!pieceSelectionnee) return;
    setErreur("");
    try {
      const edition = ouvertureEditionId !== null;
      const url = `/api/domotique/plan-3d/${pieceSelectionnee.id}/ouvertures${edition ? `/${ouvertureEditionId}` : ""}`;
      const response = await apiFetch(url, { method: edition ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(ouvertureBrouillon) });
      const donnees = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(donnees.detail || "Impossible d'enregistrer cette ouverture.");
      setPieces((anciennes) => anciennes.map((piece) => piece.id === pieceSelectionnee.id ? { ...piece, ouvertures: edition ? (piece.ouvertures ?? []).map((item) => item.id === donnees.id ? donnees : item) : [...(piece.ouvertures ?? []), donnees] } : piece));
      setOuvertureEditionId(null);
      setOuvertureBrouillon({ type: "porte", mur: "nord", position: 0, largeur: 0.9, hauteur: 2.1, hauteur_appui: 0, sens_ouverture: "gauche", angle_ouverture: 90 });
      setMessage("Ouverture enregistrée.");
    } catch (error) { setErreur(error instanceof Error ? error.message : "Erreur d'enregistrement de l'ouverture."); }
  };

  const editerOuverture = (ouverture: Ouverture) => {
    setOuvertureEditionId(ouverture.id);
    setOuvertureBrouillon({ type: ouverture.type, mur: ouverture.mur, position: ouverture.position, largeur: ouverture.largeur, hauteur: ouverture.hauteur, hauteur_appui: ouverture.hauteur_appui, sens_ouverture: ouverture.sens_ouverture ?? "gauche", angle_ouverture: ouverture.angle_ouverture ?? 90 });
  };

  const supprimerOuverture = async (ouverture: Ouverture) => {
    if (!pieceSelectionnee) return;
    const response = await apiFetch(`/api/domotique/plan-3d/${pieceSelectionnee.id}/ouvertures/${ouverture.id}`, { method: "DELETE" });
    if (!response.ok) { setErreur("Impossible de supprimer cette ouverture."); return; }
    setPieces((anciennes) => anciennes.map((piece) => piece.id === pieceSelectionnee.id ? { ...piece, ouvertures: (piece.ouvertures ?? []).filter((item) => item.id !== ouverture.id) } : piece));
    if (ouvertureEditionId === ouverture.id) setOuvertureEditionId(null);
    setMessage("Ouverture supprimée.");
  };

  const deplacerOuverture = (pieceId: string, ouvertureId: number, position: number) => {
    setPieces((anciennes) => anciennes.map((piece) => piece.id === pieceId
      ? { ...piece, ouvertures: (piece.ouvertures ?? []).map((ouverture) => ouverture.id === ouvertureId ? { ...ouverture, position } : ouverture) }
      : piece));
  };

  const validerDeplacementOuverture = async (piece: PiecePlan, ouverture: Ouverture, position: number) => {
    const positionLimitee = Math.max(-(piece.largeur > 0 ? (ouverture.mur === "nord" || ouverture.mur === "sud" ? piece.largeur : piece.profondeur) : 0) / 2 + ouverture.largeur / 2,
      Math.min((ouverture.mur === "nord" || ouverture.mur === "sud" ? piece.largeur : piece.profondeur) / 2 - ouverture.largeur / 2, position));
    const miseAJour = { ...ouverture, position: positionLimitee };
    try {
      const response = await apiFetch(`/api/domotique/plan-3d/${piece.id}/ouvertures/${ouverture.id}`, {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(miseAJour),
      });
      const donnees = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(donnees.detail || "Déplacement impossible.");
      setPieces((anciennes) => anciennes.map((item) => item.id === piece.id
        ? { ...item, ouvertures: (item.ouvertures ?? []).map((ouvertureExistante) => ouvertureExistante.id === ouverture.id ? donnees : ouvertureExistante) }
        : item));
      setMessage("Position de l'ouverture enregistrée.");
      setErreur("");
    } catch (error) {
      setErreur(error instanceof Error ? error.message : "Erreur lors du déplacement.");
      void charger();
    }
  };

  const piecesVisibles = etageAffiche === "tous" ? pieces : pieces.filter((piece) => piece.etage === Number(etageAffiche));
  const planLargeur = Math.max(16, ...piecesVisibles.map((piece) => Math.abs(piece.position_x) + piece.largeur / 2 + 3), 16);
  const planProfondeur = Math.max(16, ...piecesVisibles.map((piece) => Math.abs(piece.position_z) + piece.profondeur / 2 + 3), 16);

  return (
    <div className={"plan3d-shell " + (nuit ? "plan3d-night" : "plan3d-day")}>
      <div className="plan3d-toolbar">
        <label>Étage affiché
          <select value={etageAffiche} onChange={(event) => setEtageAffiche(event.target.value)}>
            <option value="tous">Tous les étages</option>
            {etages.map((etage) => <option key={etage} value={etage}>{etage === 0 ? "Rez-de-chaussée" : `Étage ${etage}`}</option>)}
          </select>
        </label>
        <label>Transparence des murs : {transparence}%
          <input type="range" min="15" max="100" value={transparence} onChange={(event) => setTransparence(Number(event.target.value))} />
        </label>
        <label>Ambiance
          <select value={ambiance} onChange={(event) => setAmbiance(event.target.value as "jour" | "nuit")}><option value="jour">Jour</option><option value="nuit">Nuit</option></select>
        </label>
        <button type="button" onClick={() => setReset((value) => value + 1)}>Réinitialiser la vue</button>
        <button type="button" onClick={() => void charger()} disabled={chargement}>Actualiser</button>
      </div>

      {chargement && <p className="plan3d-status">Chargement des pièces…</p>}
      {erreur && <p className="plan3d-error" role="alert">{erreur}</p>}
      {!chargement && !erreur && pieces.length === 0 && <p className="plan3d-status">Crée d'abord tes pièces dans la page Domotique.</p>}

      {pieces.length > 0 && (
        <>
          <div className="plan3d-editor">
            {role === "admin" ? (
              <form className="plan3d-room-form" onSubmit={enregistrer}>
                <label>Pièce à modifier<select value={selection} onChange={(event) => { const id = event.target.value; setSelection(id); setBrouillon(creerBrouillon(pieces.find((piece) => piece.id === id))); }}>{pieces.map((piece) => <option key={piece.id} value={piece.id}>{piece.nom}</option>)}</select></label>
                {brouillon && <>
                  <label>Position X (m)<input type="number" min="-100" max="100" step="0.1" value={brouillon.position_x} onChange={(event) => modifier("position_x", Number(event.target.value))} /></label>
                  <label>Position Z (m)<input type="number" min="-100" max="100" step="0.1" value={brouillon.position_z} onChange={(event) => modifier("position_z", Number(event.target.value))} /></label>
                  <label>Largeur (m)<input type="number" min="1.5" max="30" step="0.1" value={brouillon.largeur} onChange={(event) => modifier("largeur", Number(event.target.value))} /></label>
                  <label>Profondeur (m)<input type="number" min="1.5" max="30" step="0.1" value={brouillon.profondeur} onChange={(event) => modifier("profondeur", Number(event.target.value))} /></label>
                  <label>Hauteur des murs (m)<input type="number" min="2" max="5" step="0.1" value={brouillon.hauteur} onChange={(event) => modifier("hauteur", Number(event.target.value))} /></label>
                  <label>Étage<select value={brouillon.etage} onChange={(event) => modifier("etage", Number(event.target.value))}>{[0, 1, 2, 3, 4, 5].map((etage) => <option key={etage} value={etage}>{etage === 0 ? "Rez-de-chaussée" : `Étage ${etage}`}</option>)}</select></label>
                  <button type="submit" disabled={enregistrement}>{enregistrement ? "Enregistrement…" : "Enregistrer la pièce"}</button>
                </>}
                <section className="plan3d-openings">
                  <h3>Portes et fenêtres</h3>
                  {(pieceSelectionnee?.ouvertures ?? []).map((ouverture) => <div className="plan3d-opening-row" key={ouverture.id}>
                    <span>{ouverture.type === "porte" ? "Porte" : "Fenêtre"} · {ouverture.mur} · {ouverture.largeur} × {ouverture.hauteur} m</span>
                    <button type="button" onClick={() => editerOuverture(ouverture)}>Modifier</button>
                    <button type="button" onClick={() => void supprimerOuverture(ouverture)}>Supprimer</button>
                  </div>)}
                  <div className="plan3d-opening-form">
                    <label>Type<select value={ouvertureBrouillon.type} onChange={(event) => { const type = event.target.value as BrouillonOuverture["type"]; setOuvertureBrouillon((ancien) => ({ ...ancien, type, hauteur: type === "porte" ? 2.1 : 1.2, hauteur_appui: type === "porte" ? 0 : 0.9, sens_ouverture: "gauche", angle_ouverture: 90 })); }}><option value="porte">Porte</option><option value="fenetre">Fenêtre</option></select></label>
                    <label>Mur<select value={ouvertureBrouillon.mur} onChange={(event) => setOuvertureBrouillon((ancien) => ({ ...ancien, mur: event.target.value as BrouillonOuverture["mur"] }))}><option value="nord">Nord</option><option value="sud">Sud</option><option value="est">Est</option><option value="ouest">Ouest</option></select></label>
                    <label>Position sur le mur (m)<input type="number" step="0.1" min="-15" max="15" value={ouvertureBrouillon.position} onChange={(event) => setOuvertureBrouillon((ancien) => ({ ...ancien, position: Number(event.target.value) }))} /></label>
                    <label>Largeur (m)<input type="number" min="0.4" max="8" step="0.1" value={ouvertureBrouillon.largeur} onChange={(event) => setOuvertureBrouillon((ancien) => ({ ...ancien, largeur: Number(event.target.value) }))} /></label>
                    <label>Hauteur (m)<input type="number" min="0.4" max="4" step="0.1" value={ouvertureBrouillon.hauteur} onChange={(event) => setOuvertureBrouillon((ancien) => ({ ...ancien, hauteur: Number(event.target.value) }))} /></label>
                    {ouvertureBrouillon.type === "porte" && <><label>Sens d'ouverture<select value={ouvertureBrouillon.sens_ouverture} onChange={(event) => setOuvertureBrouillon((ancien) => ({ ...ancien, sens_ouverture: event.target.value as "gauche" | "droite" }))}><option value="gauche">Gauche</option><option value="droite">Droite</option></select></label><label>Angle d'ouverture<select value={ouvertureBrouillon.angle_ouverture} onChange={(event) => setOuvertureBrouillon((ancien) => ({ ...ancien, angle_ouverture: Number(event.target.value) }))}><option value={0}>Fermée (0°)</option><option value={45}>45°</option><option value={90}>90°</option><option value={120}>120°</option><option value={150}>150°</option></select></label></>}
                    <label>Hauteur d'appui (m)<input type="number" min="0" max="3" step="0.1" disabled={ouvertureBrouillon.type === "porte"} value={ouvertureBrouillon.hauteur_appui} onChange={(event) => setOuvertureBrouillon((ancien) => ({ ...ancien, hauteur_appui: Number(event.target.value) }))} /></label>
                    <button type="button" onClick={() => void enregistrerOuverture()}>{ouvertureEditionId === null ? "Ajouter l'ouverture" : "Enregistrer l'ouverture"}</button>
                    {ouvertureEditionId !== null && <button type="button" onClick={() => { setOuvertureEditionId(null); setOuvertureBrouillon({ type: "porte", mur: "nord", position: 0, largeur: 0.9, hauteur: 2.1, hauteur_appui: 0, sens_ouverture: "gauche", angle_ouverture: 90 }); }}>Annuler</button>}
                  </div>
                </section>
              </form>
            ) : <p className="plan3d-status">Mode consultation : seul un administrateur peut modifier la géométrie.</p>}
          </div>
          {message && <p className="plan3d-success" role="status">{message}</p>}
          <div className="plan3d-canvas" role="img" aria-label="Plan 3D composé des pièces enregistrées">
            <Canvas key={reset} shadows camera={{ position: [planLargeur * 0.85, 12, planProfondeur * 0.85], fov: 42 }}>
              <color attach="background" args={[nuit ? "#0b1423" : "#e8eef4"]} />
              <ambientLight intensity={nuit ? 0.4 : 1.1} />
              <directionalLight position={[8, 14, 8]} intensity={nuit ? 0.7 : 2} castShadow />
              {piecesVisibles.map((piece) => <SolEtMurs key={piece.id} piece={piece} pieces={piecesVisibles} transparence={transparence} nuit={nuit} deplacer={deplacerOuverture} validerDeplacement={validerDeplacementOuverture} peutModifier={role === "admin"} />)}
              <gridHelper args={[Math.max(planLargeur, planProfondeur) * 2, Math.max(20, Math.ceil(Math.max(planLargeur, planProfondeur) * 2)), nuit ? "#40536b" : "#a9b8c6", nuit ? "#24364b" : "#cbd5df"]} position={[0, -0.04, 0]} />
              <OrbitControls makeDefault enableDamping enablePan enableRotate enableZoom minDistance={5} maxDistance={80} maxPolarAngle={Math.PI / 2.03} target={[0, 1, 0]} />
            </Canvas>
            <div className="plan3d-hint">Curseur sur une ouverture : déplacer le long du mur · Molette : zoomer · Clic droit : déplacer la vue</div>
          </div>
        </>
      )}
      <p className="plan3d-disclaimer">Les pièces sont affichées avec leurs dimensions et leur étage enregistrés. Les positions proposées au départ sont provisoires : ajuste-les pour reproduire ton logement. Les portes et fenêtres sont représentées avec leurs cadres, vantaux et vitrages schématiques ; les dimensions et positions doivent être ajustées pour reproduire le logement.</p>
    </div>
  );
}
