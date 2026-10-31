import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Canvas } from "@react-three/fiber";
import { Html, Line, OrbitControls, RoundedBox } from "@react-three/drei";
import { Shape, Path, ExtrudeGeometry } from "three";
import { apiFetch } from "../api";
import Plan3DOptions from "./Plan3DOptions";
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
  meubles: Meuble[];
  installations: ElementInstallation[];
};

type Ouverture = { id: number; type: "porte" | "fenetre"; mur: "nord" | "sud" | "est" | "ouest"; position: number; largeur: number; hauteur: number; hauteur_appui: number; sens_ouverture: "gauche" | "droite"; angle_ouverture: number };
type ElementInstallation = { id: number; type: "prise" | "interrupteur" | "appareil"; position_x: number; position_z: number; hauteur: number; orientation: "nord" | "sud" | "est" | "ouest"; circuit: string; appareil_id: string | null };
type AppareilDomotique = { id: string; nom: string; piece: string; type: string; allume?: boolean; capacites?: string[] };
type Meuble = { id: number; type: "canape" | "fauteuil" | "table" | "lit" | "armoire" | "cuisine"; position_x: number; position_z: number; largeur: number; profondeur: number; hauteur: number; rotation: number };
type LumiereDomotique = { id: string; nom: string; piece: string; type: string; allume: boolean; luminosite?: number | null; temperature_couleur?: number | null; couleur?: string | null };
type FinitionSurface = { materiau: string; couleur: string };
type FinitionsPiece = { piece_id: string; mur_interieur: FinitionSurface; mur_exterieur: FinitionSurface; sol: FinitionSurface; plafond: FinitionSurface };
type BrouillonOuverture = Omit<Ouverture, "id">;
type Brouillon = Pick<PiecePlan, "position_x" | "position_z" | "largeur" | "profondeur" | "hauteur" | "etage">;

function ObjetMeuble3D({ meuble, piece, peutModifier, deplacer, selectionne, selectionner, pasGrille }: { meuble: Meuble; piece: PiecePlan; peutModifier: boolean; deplacer: (meuble: Meuble, x: number, z: number, final: boolean) => void; selectionne: boolean; selectionner: (id: number) => void; pasGrille: number }) {
  const couleurs: Record<Meuble["type"], string> = {
    canape: "#557b91", fauteuil: "#638b9d", table: "#9b704e",
    lit: "#b7c7d8", armoire: "#8b7059", cuisine: "#aeb8c2",
  };
  const couleur = couleurs[meuble.type];
  const decalage = useRef({ x: 0, z: 0 });
  const glisse = useRef(false);
  const positionner = (event: { point: { x: number; z: number } }, final: boolean) => {
    const rotation = meuble.rotation * Math.PI / 180;
    const largeurTournee = Math.abs(Math.cos(rotation)) * meuble.largeur + Math.abs(Math.sin(rotation)) * meuble.profondeur;
    const profondeurTournee = Math.abs(Math.sin(rotation)) * meuble.largeur + Math.abs(Math.cos(rotation)) * meuble.profondeur;
    const x = Math.max(-piece.largeur / 2 + largeurTournee / 2, Math.min(piece.largeur / 2 - largeurTournee / 2, event.point.x - piece.position_x - decalage.current.x));
    const z = Math.max(-piece.profondeur / 2 + profondeurTournee / 2, Math.min(piece.profondeur / 2 - profondeurTournee / 2, event.point.z - piece.position_z - decalage.current.z));
    const xAligne = pasGrille > 0 ? Math.round(x / pasGrille) * pasGrille : x;
    const zAligne = pasGrille > 0 ? Math.round(z / pasGrille) * pasGrille : z;
    const xFinal = Math.max(-piece.largeur / 2 + largeurTournee / 2, Math.min(piece.largeur / 2 - largeurTournee / 2, xAligne));
    const zFinal = Math.max(-piece.profondeur / 2 + profondeurTournee / 2, Math.min(piece.profondeur / 2 - profondeurTournee / 2, zAligne));
    deplacer(meuble, Number(xFinal.toFixed(2)), Number(zFinal.toFixed(2)), final);
  };
  const materiau = (color: string) => <meshStandardMaterial color={color} roughness={meuble.type === "table" || meuble.type === "armoire" || meuble.type === "cuisine" ? 0.38 : 0.88} metalness={meuble.type === "cuisine" ? 0.18 : 0.02} />;
  return <group position={[meuble.position_x, 0.06, meuble.position_z]} rotation={[0, meuble.rotation * Math.PI / 180, 0]}
    onPointerDown={peutModifier ? (event) => { event.stopPropagation(); selectionner(meuble.id); glisse.current = true; decalage.current = { x: event.point.x - piece.position_x - meuble.position_x, z: event.point.z - piece.position_z - meuble.position_z }; (event.target as EventTarget & { setPointerCapture?: (pointerId: number) => void }).setPointerCapture?.(event.pointerId); } : undefined}
    onPointerMove={peutModifier ? (event) => { if (glisse.current) { event.stopPropagation(); positionner(event, false); } } : undefined}
    onPointerUp={peutModifier ? (event) => { if (glisse.current) { event.stopPropagation(); glisse.current = false; positionner(event, true); } } : undefined}
    onPointerCancel={() => { glisse.current = false; }}>
    <RoundedBox position={[0, meuble.hauteur / 2, 0]} args={[meuble.largeur, meuble.hauteur, meuble.profondeur]} radius={Math.min(0.045, meuble.hauteur * 0.08)} smoothness={3} castShadow receiveShadow>{materiau(couleur)}</RoundedBox>
    {selectionne && <mesh position={[0, meuble.hauteur / 2, 0]}><boxGeometry args={[meuble.largeur + 0.055, meuble.hauteur + 0.055, meuble.profondeur + 0.055]} /><meshBasicMaterial color="#38bdf8" wireframe transparent opacity={0.9} depthTest={false} /></mesh>}
    {meuble.type === "canape" && <>
      <mesh position={[0, meuble.hauteur * 0.76, -meuble.profondeur * 0.38]} castShadow><boxGeometry args={[meuble.largeur * 0.92, meuble.hauteur * 0.42, meuble.profondeur * 0.18]} />{materiau("#405f73")}</mesh>
      {[-1, 1].map((cote) => <mesh key={cote} position={[cote * meuble.largeur * 0.43, meuble.hauteur * 0.56, 0]}><boxGeometry args={[meuble.largeur * 0.12, meuble.hauteur * 0.48, meuble.profondeur]} />{materiau("#405f73")}</mesh>)}
      <RoundedBox position={[0, meuble.hauteur * 0.57, 0.08]} args={[meuble.largeur * 0.68, meuble.hauteur * 0.16, meuble.profondeur * 0.48]} radius={0.055} smoothness={3} castShadow>{materiau("#7896a8")}</RoundedBox>
    </>}
    {meuble.type === "fauteuil" && <>
      <mesh position={[0, meuble.hauteur * 0.78, -meuble.profondeur * 0.38]}><boxGeometry args={[meuble.largeur * 0.88, meuble.hauteur * 0.4, meuble.profondeur * 0.18]} />{materiau("#405f73")}</mesh>
      {[-1, 1].map((c) => <mesh key={c} position={[c * meuble.largeur * 0.43, meuble.hauteur * 0.55, 0]}><boxGeometry args={[meuble.largeur * 0.14, meuble.hauteur * 0.45, meuble.profondeur]} />{materiau("#405f73")}</mesh>)}
    </>}
    {meuble.type === "lit" && <>
      <mesh position={[0, meuble.hauteur * 0.9, -meuble.profondeur * 0.42]}><boxGeometry args={[meuble.largeur, meuble.hauteur * 0.2, 0.1]} />{materiau("#8b7059")}</mesh>
      {[-1, 1].map((c) => <mesh key={c} position={[c * meuble.largeur * 0.23, meuble.hauteur * 1.08, meuble.profondeur * 0.28]}><boxGeometry args={[meuble.largeur * 0.32, meuble.hauteur * 0.12, meuble.profondeur * 0.2]} />{materiau("#f4f6f8")}</mesh>)}
      <RoundedBox position={[0, meuble.hauteur * 1.02, 0.05]} args={[meuble.largeur * 0.92, meuble.hauteur * 0.12, meuble.profondeur * 0.72]} radius={0.045} smoothness={4} castShadow>{materiau("#e7edf2")}</RoundedBox>
    </>}
    {meuble.type === "table" && <>
      {[-1, 1].flatMap((x) => [-1, 1].map((z) => <mesh key={x + ":" + z} position={[x * meuble.largeur * 0.42, meuble.hauteur * 0.25, z * meuble.profondeur * 0.38]}><boxGeometry args={[0.07, meuble.hauteur * 0.5, 0.07]} />{materiau("#765338")}</mesh>))}
      <mesh position={[0, meuble.hauteur * 0.94, 0]}><boxGeometry args={[meuble.largeur * 0.98, 0.08, meuble.profondeur * 0.98]} />{materiau("#c39a70")}</mesh>
    </>}
    {meuble.type === "armoire" && <>
      {[-1, 1].map((c) => <group key={c} position={[c * meuble.largeur * 0.25, meuble.hauteur * 0.5, meuble.profondeur / 2 + 0.012]}>
        <mesh><boxGeometry args={[meuble.largeur * 0.48, meuble.hauteur * 0.94, 0.035]} />{materiau("#a88b70")}</mesh>
        <mesh position={[c * meuble.largeur * 0.16, 0, 0.025]}><sphereGeometry args={[0.025, 10, 8]} />{materiau("#d5b56d")}</mesh>
      </group>)}
    </>}
    {meuble.type === "cuisine" && <>
      <mesh position={[0, meuble.hauteur * 0.92, 0]}><boxGeometry args={[meuble.largeur * 1.04, meuble.hauteur * 0.12, meuble.profondeur * 1.06]} />{materiau("#e4e8eb")}</mesh>
      {[-1, 1].map((c) => <group key={c} position={[c * meuble.largeur * 0.25, meuble.hauteur * 0.46, meuble.profondeur / 2 + 0.018]}>
        <mesh><boxGeometry args={[meuble.largeur * 0.48, meuble.hauteur * 0.78, 0.035]} />{materiau("#d7dde2")}</mesh>
        <mesh position={[0, meuble.hauteur * 0.2, 0.03]}><boxGeometry args={[meuble.largeur * 0.12, 0.018, 0.018]} />{materiau("#687888")}</mesh>
        <mesh position={[0, -meuble.hauteur * 0.12, 0.03]}><boxGeometry args={[meuble.largeur * 0.12, 0.018, 0.018]} />{materiau("#687888")}</mesh>
      </group>)}
      <mesh position={[0, meuble.hauteur * 0.98, -meuble.profondeur * 0.18]}><boxGeometry args={[meuble.largeur * 0.42, 0.018, meuble.profondeur * 0.42]} />{materiau("#697987")}</mesh>
    </>}
  </group>;
}
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

function MurAvecOuvertures({ piece, pieces, mur, ouvertures, materiau, nuit, deplacer, validerDeplacement, peutModifier, finition }: {
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
      <meshStandardMaterial attach="material-0" {...materiau} color={finition?.mur_interieur.couleur ?? materiau.color} side={2} />\n      <meshStandardMaterial attach="material-1" {...materiau} color={finition?.mur_exterieur.couleur ?? materiau.color} side={2} />
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

function LuminairePiece3D({ lumieres, nuit }: { lumieres: LumiereDomotique[]; nuit: boolean }) {
  return <group>{lumieres.map((lumiere, index) => {
    const couleur = lumiere.couleur || (lumiere.temperature_couleur && lumiere.temperature_couleur < 3500 ? "#ffbd78" : "#e6f2ff");
    const intensite = lumiere.allume ? Math.max(0.08, (lumiere.luminosite ?? 100) / 100) * 1.7 : 0;
    return <group key={lumiere.id} position={[(index % 2 ? 0.65 : -0.65), 2.48, (index < 2 ? -0.55 : 0.55)]}>
      <mesh><sphereGeometry args={[0.09, 16, 12]} /><meshStandardMaterial color={lumiere.allume ? couleur : "#64748b"} emissive={lumiere.allume ? couleur : "#000000"} emissiveIntensity={lumiere.allume ? 1.8 : 0} /></mesh>
      {lumiere.allume && <pointLight color={couleur} intensity={intensite} distance={Math.max(3.5, Math.min(7, 2.5 + (lumiere.luminosite ?? 100) / 25))} decay={2} />}
      <Html position={[0, 0.2, 0]} center distanceFactor={12} style={{ pointerEvents: "none", whiteSpace: "nowrap" }}><span className={nuit ? "plan3d-light-label plan3d-light-label-night" : "plan3d-light-label"}>{lumiere.nom}</span></Html>
    </group>;
  })}</group>;
}

function InstallationPiece3D({ elements, appareils, nuit, commander }: { elements: ElementInstallation[]; appareils: AppareilDomotique[]; nuit: boolean; commander: (appareil: AppareilDomotique) => void }) {
  const circuits = elements.reduce<Record<string, ElementInstallation[]>>((groupes, element) => {
    (groupes[element.circuit] ??= []).push(element);
    return groupes;
  }, {});
  return <group>
    {Object.entries(circuits).filter(([, membres]) => membres.length > 1).map(([circuit, membres]) => <Line key={circuit} points={membres.map((element) => [element.position_x, 0.09, element.position_z] as [number, number, number])} color={nuit ? "#eab308" : "#b7791f"} lineWidth={1.5} dashed dashSize={0.12} gapSize={0.08} />)}
    {elements.map((element) => {
    const appareil = appareils.find((item) => item.id === element.appareil_id);
    const couleur = element.type === "prise" ? "#e5e7eb" : element.type === "interrupteur" ? "#fbbf24" : appareil?.allume ? "#34d399" : "#64748b";
    return <group key={element.id} position={[element.position_x, element.hauteur, element.position_z]} rotation={[0, element.orientation === "est" ? Math.PI / 2 : element.orientation === "ouest" ? -Math.PI / 2 : element.orientation === "sud" ? Math.PI : 0, 0]}
      onClick={(event) => { if (appareil) { event.stopPropagation(); commander(appareil); } }}>
      <mesh castShadow><boxGeometry args={[element.type === "appareil" ? 0.22 : 0.14, element.type === "prise" ? 0.13 : 0.2, 0.055]} /><meshStandardMaterial color={couleur} roughness={0.45} metalness={0.12} /></mesh>
      {element.type === "prise" && <><mesh position={[-0.035, 0, 0.031]}><sphereGeometry args={[0.012, 8, 6]} /><meshStandardMaterial color="#334155" /></mesh><mesh position={[0.035, 0, 0.031]}><sphereGeometry args={[0.012, 8, 6]} /><meshStandardMaterial color="#334155" /></mesh></>}
      {element.type === "interrupteur" && <mesh position={[0, 0, 0.034]}><boxGeometry args={[0.045, 0.075, 0.012]} /><meshStandardMaterial color="#f8fafc" /></mesh>}
      <Html position={[0, 0.18, 0]} center distanceFactor={11} style={{ pointerEvents: "none", whiteSpace: "nowrap" }}><span className={nuit ? "plan3d-install-label plan3d-install-label-night" : "plan3d-install-label"}>{appareil?.nom ?? (element.type === "prise" ? "Prise" : element.type === "interrupteur" ? "Interrupteur" : "Équipement")} · {element.circuit}</span></Html>
    </group>;
  })}</group>;
}

function SolEtMurs({ piece, pieces, transparence, nuit, deplacer, validerDeplacement, peutModifier, deplacerMeuble, selectionMeuble, selectionnerMeuble, pasGrille, lumieres, appareils, commander, finition }: {
  piece: PiecePlan; pieces: PiecePlan[]; transparence: number; nuit: boolean; peutModifier: boolean; finition?: FinitionsPiece;
  deplacer: (pieceId: string, ouvertureId: number, position: number) => void;
  validerDeplacement: (piece: PiecePlan, ouverture: Ouverture, position: number) => void;
  deplacerMeuble: (meuble: Meuble, x: number, z: number, final: boolean) => void;
  selectionMeuble: number | null; selectionnerMeuble: (id: number) => void; pasGrille: number; lumieres: LumiereDomotique[]; appareils: AppareilDomotique[]; commander: (appareil: AppareilDomotique) => void;
}) {
  const opacite = transparence / 100;
  const materiauMur = { color: nuit ? "#8293aa" : "#e0e7ef", transparent: opacite < 1, opacity: opacite, roughness: 0.82, depthWrite: opacite >= 1 };
  const ouvertures = piece.ouvertures ?? [];
  return (
    <group position={[piece.position_x, piece.etage * 3.25, piece.position_z]}>
      {(piece.meubles ?? []).map((meuble) => <ObjetMeuble3D key={meuble.id} meuble={meuble} piece={piece} peutModifier={peutModifier} deplacer={deplacerMeuble} selectionne={selectionMeuble === meuble.id} selectionner={selectionnerMeuble} pasGrille={pasGrille} />)}
      <LuminairePiece3D lumieres={lumieres.filter((lumiere) => lumiere.piece.trim().toLocaleLowerCase() === piece.nom.trim().toLocaleLowerCase())} nuit={nuit} />
      <InstallationPiece3D elements={piece.installations ?? []} appareils={appareils} nuit={nuit} commander={commander} />
      <mesh position={[0, 0.025, 0]} receiveShadow>
        <boxGeometry args={[piece.largeur, 0.05, piece.profondeur]} />
        <meshStandardMaterial color={finition?.sol.couleur ?? piece.couleur ?? "#b8c7d8"} roughness={0.9} />\n      <mesh position={[0, piece.hauteur - 0.025, 0]} rotation={[Math.PI / 2, 0, 0]}><planeGeometry args={[piece.largeur, piece.profondeur]} /><meshStandardMaterial color={finition?.plafond.couleur ?? "#f1f5f9"} transparent opacity={0.12} side={2} depthWrite={false} /></mesh>
      </mesh>
      <gridHelper args={[Math.max(piece.largeur, piece.profondeur), Math.max(2, Math.round(Math.max(piece.largeur, piece.profondeur) * 2)), nuit ? "#46566d" : "#9aa9b8", nuit ? "#35465c" : "#c2ccd6"]} position={[0, 0.053, 0]} />
      {(["nord", "sud", "est", "ouest"] as const).map((mur) => {
        const voisin = mursCoincidents(piece, mur, pieces);
        if (voisin && piece.id.localeCompare(voisin.id) > 0) return null;
        const oppose: Record<Ouverture["mur"], Ouverture["mur"]> = { nord: "sud", sud: "nord", est: "ouest", ouest: "est" };
        const ouverturesMur = ouvertures.filter((ouverture) => ouverture.mur === mur);
        const ouverturesVoisin = voisin
          ? (voisin.ouvertures ?? []).filter((ouverture) => ouverture.mur === oppose[mur]).map((ouverture) => ({ ...ouverture, position: ouverture.position }))
          : [];
        return <MurAvecOuvertures key={mur} piece={piece} pieces={pieces} mur={mur} ouvertures={[...ouverturesMur, ...ouverturesVoisin]} materiau={materiauMur} nuit={nuit} deplacer={deplacer} validerDeplacement={validerDeplacement} peutModifier={peutModifier} finition={finition} />;
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
  const [selectionMeuble, setSelectionMeuble] = useState<number | null>(null);
  const [pasGrille, setPasGrille] = useState(0.1);
  const [lumieres, setLumieres] = useState<LumiereDomotique[]>([]);\n  const [finitions, setFinitions] = useState<Record<string, FinitionsPiece>>({});
  const [appareils, setAppareils] = useState<AppareilDomotique[]>([]);
  const [typeInstallation, setTypeInstallation] = useState<ElementInstallation["type"]>("prise");
  const [appareilInstallation, setAppareilInstallation] = useState("");
  const [circuitInstallation, setCircuitInstallation] = useState("Circuit général");
  const [brouillon, setBrouillon] = useState<Brouillon | null>(null);
  const [ouvertureBrouillon, setOuvertureBrouillon] = useState<BrouillonOuverture>({ type: "porte", mur: "nord", position: 0, largeur: 0.9, hauteur: 2.1, hauteur_appui: 0, sens_ouverture: "gauche", angle_ouverture: 90 });
  const [ouvertureEditionId, setOuvertureEditionId] = useState<number | null>(null);
  const [typeMeuble, setTypeMeuble] = useState<Meuble["type"]>("canape");
  const [etageAffiche, setEtageAffiche] = useState("0");
  const [transparence, setTransparence] = useState(82);
  const [ambiance, setAmbiance] = useState<"jour" | "nuit">("jour");
  const [reset, setReset] = useState(0);
  const [chargement, setChargement] = useState(true);
  const [enregistrement, setEnregistrement] = useState(false);
  const [erreur, setErreur] = useState("");
  const [message, setMessage] = useState("");
  const nuit = ambiance === "nuit";\n  const recevoirFinition = (pieceId: string, valeur: FinitionsPiece) => setFinitions((old) => ({ ...old, [pieceId]: valeur }));
  const pieceSelectionnee = pieces.find((piece) => piece.id === selection) ?? null;
  const etages = useMemo(() => [...new Set(pieces.map((piece) => piece.etage))].sort((a, b) => a - b), [pieces]);

  const chargerLumieres = useCallback(async () => {
    try {
      const response = await apiFetch("/api/domotique/appareils?type=lumiere");
      if (!response.ok) return;
      setLumieres(await response.json() as LumiereDomotique[]);
    } catch { /* Le plan reste consultable si le service domotique est indisponible. */ }
  }, []);

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
    apiFetch("/api/domotique/appareils")
      .then(async (response) => response.ok ? await response.json() as AppareilDomotique[] : [])
      .then((donnees) => { if (actif) { setAppareils(donnees); setLumieres(donnees.filter((item) => item.type === "lumiere").map((item) => ({ ...item, allume: item.allume ?? false })) as LumiereDomotique[]); } })
      .catch(() => { /* Appareils facultatifs dans la vue 3D. */ });
    return () => { actif = false; };
  }, []);

  const ajouterInstallation = async () => {
    if (!pieceSelectionnee) return;
    const payload = { type: typeInstallation, position_x: Math.max(-pieceSelectionnee.largeur / 2 + 0.15, Math.min(pieceSelectionnee.largeur / 2 - 0.15, -pieceSelectionnee.largeur / 2 + 0.3 + (pieceSelectionnee.installations?.length ?? 0) % 5 * 0.45)), position_z: -pieceSelectionnee.profondeur / 2 + 0.12, orientation: "nord", circuit: circuitInstallation, appareil_id: typeInstallation === "appareil" ? appareilInstallation || null : null };
    try {
      const response = await apiFetch(`/api/domotique/plan-3d/${pieceSelectionnee.id}/installations`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Impossible d'ajouter cet élément.");
      setPieces((old) => old.map((piece) => piece.id === pieceSelectionnee.id ? { ...piece, installations: [...(piece.installations ?? []), data] } : piece));
      setMessage("Élément électrique ajouté.");
    } catch (error) { setErreur(error instanceof Error ? error.message : "Erreur d'ajout."); }
  };

  const modifierInstallation = async (element: ElementInstallation, changements: Partial<ElementInstallation>) => {
    if (!pieceSelectionnee) return;
    const payload = { ...element, ...changements };
    const response = await apiFetch(`/api/domotique/plan-3d/${pieceSelectionnee.id}/installations/${element.id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) { setErreur(data.detail || "Modification de l'installation impossible."); return; }
    setPieces((old) => old.map((piece) => piece.id === pieceSelectionnee.id ? { ...piece, installations: piece.installations.map((item) => item.id === element.id ? data : item) } : piece));
    setErreur("");
  };

  const commanderAppareil = async (appareil: AppareilDomotique) => {
    if (appareil.type === "capteur") { setMessage(`${appareil.nom} est consultable en lecture seule.`); return; }
    try {
      const response = await apiFetch(`/api/domotique/appareils/${encodeURIComponent(appareil.id)}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ allume: !appareil.allume }) });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Commande refusée.");
      setAppareils((old) => old.map((item) => item.id === appareil.id ? { ...item, ...data } : item));
      setLumieres((old) => old.map((item) => item.id === appareil.id ? { ...item, ...data } : item));
      setMessage(`${appareil.nom} : ${data.allume ? "allumé" : "éteint"}.`);
      setErreur("");
    } catch (error) { setErreur(error instanceof Error ? error.message : "Commande impossible."); }
  };

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

  const ajouterMeuble = async () => {
    if (!pieceSelectionnee) return;
    const presets: Record<Meuble["type"], Omit<Meuble, "id">> = {
      canape: { type: "canape", position_x: 0, position_z: 0, largeur: 2.1, profondeur: 0.9, hauteur: 0.85, rotation: 0 },
      fauteuil: { type: "fauteuil", position_x: 0, position_z: 0, largeur: 0.9, profondeur: 0.9, hauteur: 0.85, rotation: 0 },
      table: { type: "table", position_x: 0, position_z: 0, largeur: 1.2, profondeur: 0.8, hauteur: 0.75, rotation: 0 },
      lit: { type: "lit", position_x: 0, position_z: 0, largeur: 1.6, profondeur: 2, hauteur: 0.5, rotation: 0 },
      armoire: { type: "armoire", position_x: 0, position_z: 0, largeur: 1.2, profondeur: 0.6, hauteur: 2.1, rotation: 0 },
      cuisine: { type: "cuisine", position_x: 0, position_z: 0, largeur: 1.2, profondeur: 0.65, hauteur: 0.9, rotation: 0 },
    };
    const meuble = presets[typeMeuble];
    try {
      const response = await apiFetch(`/api/domotique/plan-3d/${pieceSelectionnee.id}/meubles`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(meuble) });
      const donnees = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(donnees.detail || "Impossible d'ajouter ce meuble.");
      setPieces((anciennes) => anciennes.map((piece) => piece.id === pieceSelectionnee.id ? { ...piece, meubles: [...(piece.meubles ?? []), donnees] } : piece));
      setMessage("Meuble ajouté.");
      setErreur("");
    } catch (error) { setErreur(error instanceof Error ? error.message : "Erreur lors de l'ajout du meuble."); }
  };

  const modifierMeuble = async (meuble: Meuble, changements: Partial<Meuble>) => {
    if (!pieceSelectionnee) return;
    const miseAJour = { ...meuble, ...changements };
    setPieces((anciennes) => anciennes.map((piece) => piece.id === pieceSelectionnee.id ? { ...piece, meubles: (piece.meubles ?? []).map((item) => item.id === meuble.id ? miseAJour : item) } : piece));
    try {
      const response = await apiFetch(`/api/domotique/plan-3d/${pieceSelectionnee.id}/meubles/${meuble.id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(miseAJour) });
      const donnees = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(donnees.detail || "Modification du meuble impossible.");
      setPieces((anciennes) => anciennes.map((piece) => piece.id === pieceSelectionnee.id ? { ...piece, meubles: (piece.meubles ?? []).map((item) => item.id === meuble.id ? donnees : item) } : piece));
      setErreur("");
    } catch (error) { setErreur(error instanceof Error ? error.message : "Erreur de modification."); void charger(); }
  };

  const supprimerMeuble = async (meuble: Meuble) => {
    if (!pieceSelectionnee) return;
    const response = await apiFetch(`/api/domotique/plan-3d/${pieceSelectionnee.id}/meubles/${meuble.id}`, { method: "DELETE" });
    if (!response.ok) { setErreur("Impossible de supprimer ce meuble."); return; }
    setPieces((anciennes) => anciennes.map((piece) => piece.id === pieceSelectionnee.id ? { ...piece, meubles: (piece.meubles ?? []).filter((item) => item.id !== meuble.id) } : piece));
    setMessage("Meuble supprimé.");
  };

  const deplacerMeuble = (meuble: Meuble, x: number, z: number, final: boolean) => {
    if (!pieceSelectionnee) return;
    const apercu = { ...meuble, position_x: x, position_z: z };
    setPieces((anciennes) => anciennes.map((piece) => piece.id === pieceSelectionnee.id
      ? { ...piece, meubles: (piece.meubles ?? []).map((item) => item.id === meuble.id ? apercu : item) }
      : piece));
    if (final) void modifierMeuble(apercu, { position_x: x, position_z: z });
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
        <button type="button" onClick={() => { void charger(); void chargerLumieres(); }} disabled={chargement}>Actualiser</button>
        {role === "admin" && <label>Alignement du mobilier<select value={pasGrille} onChange={(event) => setPasGrille(Number(event.target.value))}><option value={0}>Libre</option><option value={0.05}>5 cm</option><option value={0.1}>10 cm</option><option value={0.25}>25 cm</option><option value={0.5}>50 cm</option></select></label>}
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
                <section className="plan3d-openings">
                  <h3>Électricité et équipements domotiques</h3>
                  <div className="plan3d-opening-form">
                    <label>Élément<select value={typeInstallation} onChange={(event) => setTypeInstallation(event.target.value as ElementInstallation["type"])}><option value="prise">Prise électrique</option><option value="interrupteur">Interrupteur</option><option value="appareil">Appareil domotique</option></select></label>
                    {typeInstallation === "appareil" && <label>Appareil<select value={appareilInstallation} onChange={(event) => setAppareilInstallation(event.target.value)}><option value="">Choisir un appareil</option>{appareils.filter((item) => item.piece === pieceSelectionnee?.nom).map((item) => <option key={item.id} value={item.id}>{item.nom} ({item.type})</option>)}</select></label>}
                    <label>Circuit électrique<input value={circuitInstallation} maxLength={80} onChange={(event) => setCircuitInstallation(event.target.value)} /></label>
                    <button type="button" onClick={() => void ajouterInstallation()}>Ajouter au plan</button>
                  </div>
                  {(pieceSelectionnee?.installations ?? []).map((element) => <div className="plan3d-opening-row" key={element.id}>
                    <span>{element.type === "prise" ? "Prise" : element.type === "interrupteur" ? "Interrupteur" : appareils.find((item) => item.id === element.appareil_id)?.nom ?? "Appareil"} · {element.circuit}</span>
                    <label className="plan3d-furniture-control">X <input aria-label="Position X de l'installation" type="number" step="0.1" defaultValue={element.position_x} onBlur={(event) => void modifierInstallation(element, { position_x: Number(event.target.value) })} /></label>
                    <label className="plan3d-furniture-control">Z <input aria-label="Position Z de l'installation" type="number" step="0.1" defaultValue={element.position_z} onBlur={(event) => void modifierInstallation(element, { position_z: Number(event.target.value) })} /></label>
                    <label className="plan3d-furniture-control">H (m) <input aria-label="Hauteur de l'installation" type="number" min="0.05" max="4.5" step="0.05" defaultValue={element.hauteur} onBlur={(event) => void modifierInstallation(element, { hauteur: Number(event.target.value) })} /></label>
                    <button type="button" onClick={async () => { const response = await apiFetch(`/api/domotique/plan-3d/${pieceSelectionnee.id}/installations/${element.id}`, { method: "DELETE" }); if (response.ok) setPieces((old) => old.map((piece) => piece.id === pieceSelectionnee.id ? { ...piece, installations: piece.installations.filter((item) => item.id !== element.id) } : piece)); else setErreur("Suppression impossible."); }}>Retirer</button>
                  </div>)}
                </section>
                <section className="plan3d-openings">
                  <h3>Mobilier 3D</h3>
                  <div className="plan3d-opening-form">
                    <label>Type de meuble<select value={typeMeuble} onChange={(event) => setTypeMeuble(event.target.value as Meuble["type"])}><option value="canape">Canapé</option><option value="fauteuil">Fauteuil</option><option value="table">Table</option><option value="lit">Lit</option><option value="armoire">Armoire</option><option value="cuisine">Meuble de cuisine</option></select></label>
                    <button type="button" onClick={() => void ajouterMeuble()}>Ajouter le meuble</button>
                  </div>
                  {(pieceSelectionnee?.meubles ?? []).map((meuble) => <div className="plan3d-opening-row" key={meuble.id}>
                    <span>{({ canape: "Canapé", fauteuil: "Fauteuil", table: "Table", lit: "Lit", armoire: "Armoire", cuisine: "Meuble de cuisine" } as Record<Meuble["type"], string>)[meuble.type]}</span>
                    <label className="plan3d-furniture-control">X <input type="number" step="0.1" defaultValue={meuble.position_x} onBlur={(event) => void modifierMeuble(meuble, { position_x: Number(event.target.value) })} /></label>
                    <label className="plan3d-furniture-control">Z <input type="number" step="0.1" defaultValue={meuble.position_z} onBlur={(event) => void modifierMeuble(meuble, { position_z: Number(event.target.value) })} /></label>
                    <label className="plan3d-furniture-control">L (m) <input aria-label="Largeur du meuble" type="number" min="0.2" max="10" step="0.1" defaultValue={meuble.largeur} onBlur={(event) => void modifierMeuble(meuble, { largeur: Number(event.target.value) })} /></label>
                    <label className="plan3d-furniture-control">P (m) <input aria-label="Profondeur du meuble" type="number" min="0.2" max="10" step="0.1" defaultValue={meuble.profondeur} onBlur={(event) => void modifierMeuble(meuble, { profondeur: Number(event.target.value) })} /></label>
                    <label className="plan3d-furniture-control">H (m) <input aria-label="Hauteur du meuble" type="number" min="0.2" max="5" step="0.1" defaultValue={meuble.hauteur} onBlur={(event) => void modifierMeuble(meuble, { hauteur: Number(event.target.value) })} /></label>
                    <button type="button" onClick={() => void modifierMeuble(meuble, { rotation: (meuble.rotation + 90) % 360 })}>Tourner 90°</button>
                    <button type="button" onClick={() => void supprimerMeuble(meuble)}>Supprimer</button>
                  </div>)}
                </section>
              </form>
            ) : <p className="plan3d-status">Mode consultation : seul un administrateur peut modifier la géométrie.</p>}
          </div>
          {message && <p className="plan3d-success" role="status">{message}</p>}
          {role === "admin" && <div className="plan3d-selection-bar">{selectionMeuble !== null ? <>Meuble sélectionné · glisse-le pour le déplacer · grille {pasGrille ? `${pasGrille * 100} cm` : "désactivée"}<button type="button" onClick={() => setSelectionMeuble(null)}>Désélectionner</button></> : "Clique sur un meuble pour le sélectionner, puis fais-le glisser."}</div>}
          <Plan3DOptions role={role} onFinitionChange={recevoirFinition} />\n          <div className="plan3d-light-status">{lumieres.length} lumière(s) domotique(s) détectée(s) · {lumieres.filter((lumiere) => lumiere.allume).length} allumée(s). Les sources actives éclairent les pièces correspondantes.</div>
          <div className="plan3d-canvas" role="img" aria-label="Plan 3D composé des pièces enregistrées">
            <Canvas key={reset} shadows camera={{ position: [planLargeur * 0.85, 12, planProfondeur * 0.85], fov: 42 }}>
              <color attach="background" args={[nuit ? "#0b1423" : "#e8eef4"]} />
              <ambientLight intensity={nuit ? 0.4 : 1.1} />
              <directionalLight position={[8, 14, 8]} intensity={nuit ? 0.22 : 1.65} castShadow shadow-mapSize-width={2048} shadow-mapSize-height={2048} shadow-bias={-0.00015} />
              <hemisphereLight args={[nuit ? "#172b50" : "#e7f3ff", nuit ? "#101522" : "#8b7968", nuit ? 0.28 : 0.55]} />
              {piecesVisibles.map((piece) => <SolEtMurs key={piece.id} piece={piece} pieces={piecesVisibles} transparence={transparence} nuit={nuit} deplacer={deplacerOuverture} validerDeplacement={validerDeplacementOuverture} peutModifier={role === "admin"} deplacerMeuble={deplacerMeuble} selectionMeuble={selectionMeuble} selectionnerMeuble={setSelectionMeuble} pasGrille={pasGrille} lumieres={lumieres} appareils={appareils} commander={commanderAppareil} finition={finitions[piece.id]} />)}
              <gridHelper args={[Math.max(planLargeur, planProfondeur) * 2, Math.max(20, Math.ceil(Math.max(planLargeur, planProfondeur) * 2)), nuit ? "#40536b" : "#a9b8c6", nuit ? "#24364b" : "#cbd5df"]} position={[0, -0.04, 0]} />
              <OrbitControls makeDefault enableDamping enablePan enableRotate enableZoom minDistance={5} maxDistance={80} maxPolarAngle={Math.PI / 2.03} target={[0, 1, 0]} />
            </Canvas>
            <div className="plan3d-hint">Faire glisser un meuble pour le déplacer · Curseur sur une ouverture : déplacer le long du mur · Molette : zoomer · Clic droit : déplacer la vue</div>
          </div>
        </>
      )}
      <p className="plan3d-disclaimer">Les pièces sont affichées avec leurs dimensions et leur étage enregistrés. Les positions proposées au départ sont provisoires : ajuste-les pour reproduire ton logement. Les portes et fenêtres sont représentées avec leurs cadres, vantaux et vitrages schématiques. Le mobilier peut être déplacé à la souris, redimensionné, tourné et supprimé par un administrateur. Les meubles peuvent être sélectionnés et déplacés avec accrochage à la grille. Les équipements positionnés peuvent être pilotés depuis le plan 3D ; prises et interrupteurs sont des éléments de repérage, les appareils physiques ne sont pas commandés par un matériel réel avec le pilote simulé.</p>
    </div>
  );
}
