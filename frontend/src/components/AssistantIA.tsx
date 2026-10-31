import { useState } from "react";

type Message = { id: number; role: "user" | "assistant"; content: string; date: Date };
const messageInitial: Message = {
  id: 1, role: "assistant",
  content: "Bonjour ! L'interface de l'assistant est prête. Son moteur conversationnel sera ajouté dans une prochaine étape.",
  date: new Date(),
};

export default function AssistantIA() {
  const [messages, setMessages] = useState<Message[]>([messageInitial]);
  const [saisie, setSaisie] = useState("");
  function envoyer(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const contenu = saisie.trim();
    if (!contenu) return;
    const maintenant = new Date();
    setMessages((anciens) => [...anciens,
      { id: maintenant.getTime(), role: "user", content: contenu, date: maintenant },
      { id: maintenant.getTime() + 1, role: "assistant", content: "Le moteur IA n'est pas encore connecté. Ton message reste local à cette interface et n'a été transmis à aucun service.", date: maintenant },
    ]);
    setSaisie("");
  }
  return <section className="assistant-section">
    <div className="section-heading"><div><h2>Assistant Maison</h2><p>Une interface commune aux futures conversations écrites et vocales.</p></div><span className="assistant-prepared-status">MOTEUR NON CONNECTÉ</span></div>
    <div className="assistant-panel assistant-panel-prepared">
      <div className="assistant-header"><div className="assistant-avatar">✦</div><div><h3>Assistant Maison</h3><p>Interface de conversation · mode préparation</p></div><span className="assistant-status assistant-status-offline"><span className="status-dot" />En attente du moteur IA</span></div>
      <div className="assistant-capabilities"><div><span>⌂</span><strong>Maison</strong><small>Consultation et commandes domotiques à venir</small></div><div><span>◎</span><strong>Questions</strong><small>Questions générales et recherches à venir</small></div><div><span>♫</span><strong>Voix</strong><small>Connexion des modules vocaux à venir</small></div></div>
      <div className="assistant-messages" aria-live="polite">{messages.map((message) => <div key={message.id} className={`assistant-message ${message.role === "user" ? "user-message" : "bot-message"}`}>{message.role === "assistant" && <div className="assistant-message-icon">✦</div>}<div><p>{message.content}</p><small>{message.date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}</small></div></div>)}</div>
      <form className="assistant-input-area" onSubmit={envoyer}><input value={saisie} onChange={(event) => setSaisie(event.target.value)} placeholder="Écris un message (aucun envoi pour le moment)..." aria-label="Message à l'assistant" /><button type="submit" disabled={!saisie.trim()}>Ajouter</button></form>
      <div className="assistant-footer-note"><span>ⓘ</span> Cette conversation est une maquette locale. Aucun modèle IA, service vocal ou service cloud n'est sollicité.</div>
    </div>
  </section>;
}
