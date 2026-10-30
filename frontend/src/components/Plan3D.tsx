import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Canvas } from "@react-three/fiber";
import { Html, OrbitControls } from "@react-three/drei";
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
};

type Brouillon = Pick<PiecePlan, "position_x" | "position_z" | "largeur" | "profondeur" | "hauteur" | "etage">;

function SolEtMurs({ piece, transparence, nuit }: { piece: PiecePlan; transparence: number; nuit: boolean }) {
  const x = piece.position_x;
  const z = piece.position_z;
  const w = piece.largeur;
  const d = piece.profondeur;
  const h = piece.hauteur;
  const epaisseur = 0.14;
  const opacite = transparence / 100;
  const materiauMur = { color: nuit ? "#8293aa" : "#e0e7ef", transparent: opacite < 1, opacity: opacite, roughness: 0.82, depthWrite: opacite >= 1 };
  return (
    <group position={[x, piece.etage * 3.25, z]}>
      <mesh position={[0, 0.025, 0]} receiveShadow>
        <boxGeometry args={[w, 0.05, d]} />
        <meshStandardMaterial color={piece.couleur || "#b8c7d8"} roughness={0.9} />
      </mesh>
      <mesh position={[0, h / 2, -d / 2]} castShadow receiveShadow>
        <boxGeometry args={[w, h, epaisseur]} /><meshStandardMaterial {...materiauMur} />
      </mesh>
      <mesh position={[0, h / 2, d / 2]} castShadow receiveShadow>
        <boxGeometry args={[w, h, epaisseur]} /><meshStandardMaterial {...materiauMur} />
      </mesh>
      <mesh position={[-w / 2, h / 2, 0]} castShadow receiveShadow>
        <boxGeometry args={[epaisseur, h, d]} /><meshStandardMaterial {...materiauMur} />
      </mesh>
      <mesh position={[w / 2, h / 2, 0]} castShadow receiveShadow>
        <boxGeometry args={[epaisseur, h, d]} /><meshStandardMaterial {...materiauMur} />
      </mesh>
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

  const creerBrouillon = (piece: PiecePlan | undefined): Brouillon | null => piece ? ({
    position_x: piece.position_x,
    position_z: piece.position_z,
    largeur: piece.largeur,
    profondeur: piece.profondeur,
    hauteur: piece.hauteur,
    etage: piece.etage,
  }) : null;

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

  useEffect(() => { void charger(); }, [charger]);

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
              </form>
            ) : <p className="plan3d-status">Mode consultation : seul un administrateur peut modifier la géométrie.</p>}
          </div>
          {message && <p className="plan3d-success" role="status">{message}</p>}
          <div className="plan3d-canvas" role="img" aria-label="Plan 3D composé des pièces enregistrées">
            <Canvas key={reset} shadows camera={{ position: [planLargeur * 0.85, 12, planProfondeur * 0.85], fov: 42 }}>
              <color attach="background" args={[nuit ? "#0b1423" : "#e8eef4"]} />
              <ambientLight intensity={nuit ? 0.4 : 1.1} />
              <directionalLight position={[8, 14, 8]} intensity={nuit ? 0.7 : 2} castShadow />
              {piecesVisibles.map((piece) => <SolEtMurs key={piece.id} piece={piece} transparence={transparence} nuit={nuit} />)}
              <gridHelper args={[Math.max(planLargeur, planProfondeur) * 2, Math.max(20, Math.ceil(Math.max(planLargeur, planProfondeur) * 2)), nuit ? "#40536b" : "#a9b8c6", nuit ? "#24364b" : "#cbd5df"]} position={[0, -0.04, 0]} />
              <OrbitControls makeDefault enableDamping enablePan enableRotate enableZoom minDistance={5} maxDistance={80} maxPolarAngle={Math.PI / 2.03} target={[0, 1, 0]} />
            </Canvas>
            <div className="plan3d-hint">Glisser : tourner · Molette : zoomer · Clic droit : déplacer</div>
          </div>
        </>
      )}
      <p className="plan3d-disclaimer">Les pièces sont affichées avec leurs dimensions et leur étage enregistrés. Les positions proposées au départ sont provisoires : ajuste-les pour reproduire ton logement. Les murs sont actuellement représentés en périphérie de chaque pièce ; portes, fenêtres et murs mitoyens seront affinés dans une étape dédiée.</p>
    </div>
  );
}
