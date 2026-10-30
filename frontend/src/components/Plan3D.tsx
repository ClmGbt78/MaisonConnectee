import { useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import "./Plan3D.css";
type Etage = "rez-de-chaussee" | "etage";
function MaisonScene({ etage, transparence, nuit }: { etage: Etage; transparence: number; nuit: boolean }) {
  const hauteur = etage === "etage" ? 1.7 : 0.12;
  const baseY = etage === "etage" ? 2.25 : 0;
  const opacite = transparence / 100;
  const materiau = { color: nuit ? "#52647b" : "#d7e0e9", transparent: opacite < 1, opacity: opacite, roughness: 0.82 };
  const murs = [
    { p: [0, hauteur / 2, -2.9] as [number, number, number], s: [8, hauteur, 0.12] as [number, number, number] },
    { p: [-3.95, hauteur / 2, 0] as [number, number, number], s: [0.12, hauteur, 5.8] as [number, number, number] },
    { p: [3.95, hauteur / 2, 0] as [number, number, number], s: [0.12, hauteur, 5.8] as [number, number, number] },
    { p: [0, hauteur / 2, 2.9] as [number, number, number], s: [8, hauteur, 0.12] as [number, number, number] },
    { p: [0, hauteur / 2, 0] as [number, number, number], s: [0.12, hauteur, 5.8] as [number, number, number] },
    { p: [1.95, hauteur / 2, -0.95] as [number, number, number], s: [4, hauteur, 0.12] as [number, number, number] },
    { p: [-1.95, hauteur / 2, 1] as [number, number, number], s: [4, hauteur, 0.12] as [number, number, number] },
  ];
  return <group position={[0, baseY, 0]}>
    <mesh position={[0, -0.12, 0]} receiveShadow><boxGeometry args={[8.2, 0.22, 6.2]} /><meshStandardMaterial color={nuit ? "#172538" : "#9aa9b8"} /></mesh>
    <mesh position={[0, 0.015, 0]} receiveShadow><boxGeometry args={[7.9, 0.05, 5.9]} /><meshStandardMaterial color={nuit ? "#26384d" : "#d6cbb8"} /></mesh>
    {murs.map((mur, i) => <mesh key={i} position={mur.p} castShadow receiveShadow><boxGeometry args={mur.s} /><meshStandardMaterial {...materiau} /></mesh>)}
    <mesh position={[-2.7, 0.12, -1.9]}><boxGeometry args={[1.7, 0.18, 1.2]} /><meshStandardMaterial color="#4d8b83" /></mesh>
    <mesh position={[2.6, 0.12, 1.9]}><boxGeometry args={[1.8, 0.18, 1.25]} /><meshStandardMaterial color="#9b8065" /></mesh>
  </group>;
}
export default function Plan3D() {
  const [etage, setEtage] = useState<Etage>("rez-de-chaussee");
  const [transparence, setTransparence] = useState(82);
  const [ambiance, setAmbiance] = useState<"jour" | "nuit">("jour");
  const [reset, setReset] = useState(0);
  const nuit = ambiance === "nuit";
  return <div className={"plan3d-shell " + (nuit ? "plan3d-night" : "plan3d-day")}>
    <div className="plan3d-toolbar">
      <label>Étage affiché<select value={etage} onChange={e => setEtage(e.target.value as Etage)}><option value="rez-de-chaussee">Rez-de-chaussée</option><option value="etage">Étage (aperçu)</option></select></label>
      <label>Transparence des murs : {transparence}%<input type="range" min="15" max="100" value={transparence} onChange={e => setTransparence(Number(e.target.value))} /></label>
      <label>Ambiance<select value={ambiance} onChange={e => setAmbiance(e.target.value as "jour" | "nuit")}><option value="jour">Jour</option><option value="nuit">Nuit</option></select></label>
      <button type="button" onClick={() => setReset(v => v + 1)}>Réinitialiser la vue</button>
    </div>
    <div className="plan3d-canvas" role="img" aria-label="Maquette 3D schématique manipulable à la souris">
      <Canvas key={reset} shadows camera={{ position: [10, 8, 10], fov: 42 }}>
        <color attach="background" args={[nuit ? "#0b1423" : "#e8eef4"]} />
        <ambientLight intensity={nuit ? 0.35 : 1.15} />
        <directionalLight position={[6, 10, 5]} intensity={nuit ? 0.55 : 2.1} castShadow />
        <MaisonScene etage={etage} transparence={transparence} nuit={nuit} />
        <gridHelper args={[16, 16, nuit ? "#40536b" : "#a9b8c6", nuit ? "#24364b" : "#cbd5df"]} position={[0, -0.25, 0]} />
        <OrbitControls makeDefault enableDamping enablePan enableRotate enableZoom minDistance={5} maxDistance={24} maxPolarAngle={Math.PI / 2.03} target={[0, 0.6, 0]} />
      </Canvas>
      <div className="plan3d-hint">Glisser : tourner · Molette : zoomer · Clic droit : déplacer</div>
    </div>
    <p className="plan3d-disclaimer">Maquette de démonstration : les dimensions, cloisons et meubles ne représentent pas encore ton logement. La prochaine étape construira le plan réel à partir des pièces enregistrées.</p>
  </div>;
}