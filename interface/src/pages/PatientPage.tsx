import { useState, useRef, useEffect } from "react";
import { useApp } from "@/App";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  postSymptoms,
  postChat,
  getPatients,
  ChatResponse,
  ExtractedData,
  SymptomsResponse,
} from "@/lib/api";
import {
  HeartPulse,
  LogOut,
  User,
  MessageSquare,
  Activity,
  History,
  Search,
  Send,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ChevronRight,
  BrainCircuit,
  Loader2,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { format } from "date-fns";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

const COMMON_SYMPTOMS = [
  "Douleur thoracique",
  "Difficulté respiratoire",
  "Fièvre élevée",
  "Perte de conscience",
  "Douleur abdominale",
  "Mal de tête",
  "Vomissements",
  "Nausée",
  "Trauma crânien",
  "AVC",
  "Hémorragie",
  "Convulsions",
  "Hypoglycémie",
  "Brûlure grave",
];

type Tab = "admission" | "chat" | "status" | "history";

function normalizePatientScore(raw: unknown): number | undefined {
  if (raw === undefined || raw === null || raw === "") return undefined;
  const parsed = typeof raw === "string" ? Number(raw.replace(",", ".")) : Number(raw);
  if (!Number.isFinite(parsed)) return undefined;
  return Math.max(0, Math.min(100, parsed));
}

export default function PatientPage() {
  const { username, logout } = useApp();
  const [activeTab, setActiveTab] = useState<Tab>("admission");

  return (
    <div className="flex h-[100dvh] bg-[var(--bg-inset)] text-[var(--text-main)] overflow-hidden">
      {/* Sidebar */}
      <div className="w-64 bg-[var(--sidebar-bg)] text-[var(--sidebar-txt)] flex flex-col border-r border-[var(--border-strong)] flex-shrink-0">
        <div className="p-6 flex items-center gap-3">
          <HeartPulse className="w-6 h-6 text-[var(--sidebar-active)]" />
          <span className="font-bold text-lg tracking-tight">TriageMed AI</span>
        </div>

        <nav className="flex-1 px-4 space-y-2 mt-4">
          <SidebarItem
            icon={<Activity />}
            label="Nouvelle Admission"
            isActive={activeTab === "admission"}
            onClick={() => setActiveTab("admission")}
          />
          <SidebarItem
            icon={<BrainCircuit />}
            label="Chat IA"
            isActive={activeTab === "chat"}
            onClick={() => setActiveTab("chat")}
            badge="Nouveau"
          />
          <SidebarItem
            icon={<Search />}
            label="Suivi & Statut"
            isActive={activeTab === "status"}
            onClick={() => setActiveTab("status")}
          />
          <SidebarItem
            icon={<History />}
            label="Historique"
            isActive={activeTab === "history"}
            onClick={() => setActiveTab("history")}
          />
        </nav>

        <div className="p-4 border-t border-[var(--border-strong)] opacity-80">
          <div className="text-xs text-[var(--sidebar-txt)]/50 mb-1">Patient Connecté</div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-[var(--sidebar-active)]/20 flex items-center justify-center text-[var(--sidebar-active)]">
              <User className="w-4 h-4" />
            </div>
            <div className="font-medium text-sm truncate">{username}</div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 bg-[var(--bg-surface)] border-b border-[var(--border)] flex items-center justify-between px-6 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="relative flex items-center justify-center">
              <span className="absolute inline-flex h-3 w-3 rounded-full bg-[var(--success)] opacity-75 animate-ping"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--success)]"></span>
            </div>
            <span className="text-sm font-medium text-[var(--text-dimmed)]">Système actif</span>
          </div>
          <Button variant="ghost" size="sm" onClick={logout} className="text-[var(--text-dimmed)] hover:text-[var(--danger)]">
            <LogOut className="w-4 h-4 mr-2" />
            Déconnexion
          </Button>
        </header>

        {/* Tab Content */}
        <main className="flex-1 overflow-auto p-6">
          <div className="max-w-5xl mx-auto h-full">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="h-full"
              >
                {activeTab === "admission" && <AdmissionWizard username={username} />}
                {activeTab === "chat" && <ChatWizard username={username} />}
                {activeTab === "status" && <StatusView />}
                {activeTab === "history" && <HistoryView username={username} />}
              </motion.div>
            </AnimatePresence>
          </div>
        </main>
      </div>
    </div>
  );
}

function SidebarItem({ icon, label, isActive, onClick, badge }: any) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
        isActive
          ? "bg-[var(--sidebar-active)]/10 text-[var(--sidebar-active)]"
          : "text-[var(--sidebar-txt)]/70 hover:bg-[var(--sidebar-hover)] hover:text-[var(--sidebar-txt)]"
      }`}
    >
      <div className="flex items-center gap-3">
        {icon}
        {label}
      </div>
      {badge && (
        <span className="text-[10px] uppercase font-bold bg-[var(--sidebar-active)] text-white px-1.5 py-0.5 rounded">
          {badge}
        </span>
      )}
    </button>
  );
}

// ── Admission Wizard ──────────────────────────────────────────────────────────

function AdmissionWizard({ username }: { username: string }) {
  const [step, setStep] = useState(1);
  const [age, setAge] = useState("");
  const [gender, setGender] = useState("");
  const [conscious, setConscious] = useState("");
  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>([]);
  const [customSymptom, setCustomSymptom] = useState("");
  const [painLevel, setPainLevel] = useState([5]);
  const [submittedPatientId, setSubmittedPatientId] = useState<string | null>(null);

  const submitMutation = useMutation({
    mutationFn: postSymptoms,
    onSuccess: (res) => {
      setSubmittedPatientId(res.patient_id);
    },
  });

  const finalPatientQuery = useQuery({
    queryKey: ["admission-final", submittedPatientId],
    queryFn: async () => {
      const res = await getPatients();
      return res.data.find((p) => (p.patient_id || p.id) === submittedPatientId);
    },
    enabled: !!submittedPatientId,
    refetchInterval: 3000,
  });

  const handleNext = () => {
    if (step < 3) setStep(step + 1);
  };

  const handleSubmit = () => {
    submitMutation.mutate({
      name: username,
      age: parseInt(age) || 30,
      gender: gender || "M",
      symptoms: selectedSymptoms,
      pain_level: painLevel[0],
      conscious: conscious === "oui",
    });
  };

  if (submitMutation.data) {
    const res = submitMutation.data;
    const p: any = finalPatientQuery.data;
    const finalAction = p?.action_finale || p?.action || "";
    const finalScore = normalizePatientScore(p?.score_gravite ?? p?.["score_gravité"] ?? p?.severity_score);
    const preliminaryScore = normalizePatientScore(res.severity_score);
    const isFinalized = !!finalAction && String(finalAction).trim() !== "";
    return (
      <Card className="max-w-2xl mx-auto border-[var(--border)] bg-[var(--bg-surface)]">
        <CardHeader className="text-center pb-2">
          <div className="mx-auto w-16 h-16 bg-[var(--success-soft)] rounded-full flex items-center justify-center mb-4">
            <CheckCircle2 className="w-8 h-8 text-[var(--success)]" />
          </div>
          <CardTitle className="text-2xl">Évaluation Terminée</CardTitle>
          <CardDescription>Votre dossier a été transmis au personnel médical.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6 pt-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-lg bg-[var(--bg-inset)] border border-[var(--border)]">
              <div className="text-sm text-[var(--text-dimmed)] mb-1">ID Patient</div>
              <div className="font-mono font-medium">{res.patient_id}</div>
            </div>
            <div className="p-4 rounded-lg bg-[var(--bg-inset)] border border-[var(--border)]">
              <div className="text-sm text-[var(--text-dimmed)] mb-1">
                {isFinalized ? "Score Final (Agents)" : "Score Préliminaire"}
              </div>
              <div className="text-2xl font-bold text-[var(--danger)]">
                {(isFinalized ? finalScore : preliminaryScore) ?? "--"}/100
              </div>
            </div>
          </div>

          {!isFinalized ? (
            <div className="p-4 rounded-lg border border-[var(--warning)]/30 bg-[var(--warning-soft)]/30">
              <div className="flex items-center gap-2 mb-2">
                <Loader2 className="w-5 h-5 animate-spin text-[var(--warning)]" />
                <h3 className="font-semibold text-[var(--warning)]">En attente de décision des agents...</h3>
              </div>
              <p className="text-sm text-[var(--text-dimmed)]">
                Votre cas est en cours de traitement par les agents cliniques et ressources.
              </p>
            </div>
          ) : (
            <div className="p-4 rounded-lg border border-[var(--border)]" style={{ backgroundColor: `${res.decision.color}10`, borderColor: res.decision.color }}>
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-5 h-5" style={{ color: res.decision.color }} />
                <h3 className="font-semibold" style={{ color: res.decision.color }}>{finalAction}</h3>
              </div>
              <p className="text-sm text-[var(--text-dimmed)]">Décision finale validée par les agents.</p>
            </div>
          )}

          <Button
            className="w-full"
            onClick={() => {
              setStep(1);
              setSubmittedPatientId(null);
              submitMutation.reset();
            }}
          >
            Nouvelle Admission
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Nouvelle Admission</h1>
        <div className="flex items-center gap-2">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${step >= s ? 'bg-[var(--primary)] text-white' : 'bg-[var(--bg-surface)] border border-[var(--border)] text-[var(--text-dimmed)]'}`}>
                {s}
              </div>
              {s < 3 && <div className={`w-8 h-1 rounded-full ${step > s ? 'bg-[var(--primary)]' : 'bg-[var(--bg-surface)] border border-[var(--border)]'}`} />}
            </div>
          ))}
        </div>
      </div>

      <Card className="border-[var(--border)] bg-[var(--bg-surface)]">
        <CardContent className="p-6">
          {step === 1 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
              <div className="space-y-2">
                <Label>Nom Patient (Lecture seule)</Label>
                <Input value={username} readOnly className="bg-[var(--bg-inset)]" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Âge</Label>
                  <Input type="number" value={age} onChange={(e) => setAge(e.target.value)} placeholder="Ex: 35" />
                </div>
                <div className="space-y-2">
                  <Label>Genre</Label>
                  <Select value={gender} onValueChange={setGender}>
                    <SelectTrigger><SelectValue placeholder="Sélectionner" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="M">Masculin</SelectItem>
                      <SelectItem value="F">Féminin</SelectItem>
                      <SelectItem value="Autre">Autre</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label>État de conscience</Label>
                <Select value={conscious} onValueChange={setConscious}>
                  <SelectTrigger><SelectValue placeholder="Sélectionner" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="oui">Conscient et alerte</SelectItem>
                    <SelectItem value="non">Altéré ou inconscient</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </motion.div>
          )}

          {step === 2 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
              <div className="space-y-3">
                <Label>Symptômes courants</Label>
                <div className="flex flex-wrap gap-2">
                  {COMMON_SYMPTOMS.map((sym) => (
                    <Badge
                      key={sym}
                      variant="outline"
                      className={`cursor-pointer px-3 py-1.5 text-sm ${selectedSymptoms.includes(sym) ? 'bg-[var(--primary)] text-white border-[var(--primary)]' : 'hover:bg-[var(--bg-inset)]'}`}
                      onClick={() => {
                        setSelectedSymptoms(prev => 
                          prev.includes(sym) ? prev.filter(s => s !== sym) : [...prev, sym]
                        );
                      }}
                    >
                      {sym}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <Label>Ajouter un autre symptôme</Label>
                <div className="flex gap-2">
                  <Input 
                    value={customSymptom} 
                    onChange={(e) => setCustomSymptom(e.target.value)} 
                    placeholder="Ex: Vertiges"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && customSymptom.trim()) {
                        e.preventDefault();
                        setSelectedSymptoms([...selectedSymptoms, customSymptom.trim()]);
                        setCustomSymptom("");
                      }
                    }}
                  />
                  <Button type="button" variant="secondary" onClick={() => {
                    if (customSymptom.trim()) {
                      setSelectedSymptoms([...selectedSymptoms, customSymptom.trim()]);
                      setCustomSymptom("");
                    }
                  }}>Ajouter</Button>
                </div>
              </div>

              <div className="space-y-4 pt-4 border-t border-[var(--border)]">
                <div className="flex justify-between items-center">
                  <Label>Niveau de douleur: <span className="text-lg font-bold text-[var(--primary)]">{painLevel[0]}/10</span></Label>
                </div>
                <Slider 
                  value={painLevel} 
                  onValueChange={setPainLevel} 
                  max={10} 
                  step={1} 
                  className="py-4"
                />
                <div className="flex justify-between text-xs text-[var(--text-dimmed)]">
                  <span>Aucune douleur (0)</span>
                  <span>Douleur extrême (10)</span>
                </div>
              </div>
            </motion.div>
          )}

          {step === 3 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
              <div className="rounded-lg bg-[var(--bg-inset)] border border-[var(--border)] p-4 space-y-4">
                <h3 className="font-semibold text-lg border-b border-[var(--border)] pb-2">Résumé de l'admission</h3>
                
                <div className="grid grid-cols-2 gap-y-2 text-sm">
                  <div className="text-[var(--text-dimmed)]">Patient</div>
                  <div className="font-medium">{username}</div>
                  
                  <div className="text-[var(--text-dimmed)]">Profil</div>
                  <div className="font-medium">{age} ans, {gender}</div>
                  
                  <div className="text-[var(--text-dimmed)]">Conscience</div>
                  <div className="font-medium">{conscious === "oui" ? "Conscient" : "Altéré/Inconscient"}</div>
                  
                  <div className="text-[var(--text-dimmed)]">Douleur</div>
                  <div className="font-medium text-[var(--danger)]">{painLevel[0]}/10</div>
                </div>

                <div className="pt-2 border-t border-[var(--border)]">
                  <div className="text-sm text-[var(--text-dimmed)] mb-2">Symptômes déclarés</div>
                  <div className="flex flex-wrap gap-2">
                    {selectedSymptoms.length > 0 ? (
                      selectedSymptoms.map(s => <Badge key={s} variant="secondary">{s}</Badge>)
                    ) : (
                      <span className="text-sm italic">Aucun symptôme renseigné</span>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </CardContent>
        <div className="p-6 pt-0 flex justify-between">
          <Button variant="outline" onClick={() => setStep(step - 1)} disabled={step === 1 || submitMutation.isPending}>
            Précédent
          </Button>
          {step < 3 ? (
            <Button onClick={handleNext} className="bg-[var(--primary)] text-white hover:bg-[var(--primary-h)]">
              Suivant <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          ) : (
            <Button onClick={handleSubmit} disabled={submitMutation.isPending} className="bg-[var(--primary)] text-white hover:bg-[var(--primary-h)]">
              {submitMutation.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              Soumettre l'admission
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}

// ── Chat IA Wizard ────────────────────────────────────────────────────────────

interface ChatMessage {
  id: string;
  role: "user" | "ai";
  content: string;
}

function ChatWizard({ username }: { username: string }) {
  const [sessionId, setSessionId] = useState<string>(() => crypto.randomUUID());
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: "1", role: "ai", content: `Bonjour ${username}, je suis votre infirmière IA de triage. Décrivez vos symptômes et je vous poserai des questions pour évaluer votre état.` }
  ]);
  const [input, setInput] = useState("");
  const [extractedData, setExtractedData] = useState<ExtractedData | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [isWaitingDecision, setIsWaitingDecision] = useState(false);
  const [finalDecision, setFinalDecision] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const decisionQuery = useQuery({
    queryKey: ["chat-final-decision", sessionId],
    queryFn: async () => {
      const res = await getPatients();
      return res.data.find((p) => (p.patient_id || p.id) === sessionId);
    },
    enabled: isWaitingDecision && !finalDecision,
    refetchInterval: 3000,
  });

  const chatMutation = useMutation({
    mutationFn: (msg: string) => postChat(msg, sessionId),
    onSuccess: (data) => {
      setMessages(prev => [...prev, { id: crypto.randomUUID(), role: "ai", content: data.reply }]);
      if (data.extracted_data) {
        setExtractedData(data.extracted_data);
      }
      if (data.is_complete) {
        setIsComplete(true);
        setIsWaitingDecision(true);
        setMessages(prev => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "ai",
            content:
              "Merci. Vos symptômes ont été transmis à l'équipe clinique. Veuillez patienter pendant l'analyse de votre dossier.",
          },
        ]);
      }
    },
    onError: (error: any) => {
      console.error("Chat error:", error);
      setMessages(prev => [...prev, { 
        id: crypto.randomUUID(), 
        role: "ai", 
        content: "Désolé, une erreur technique est survenue. Veuillez réessayer s'il vous plaît." 
      }]);
    }
  });

  useEffect(() => {
    if (!isWaitingDecision || finalDecision) return;
    const patient: any = decisionQuery.data;
    const action = (patient?.action_finale || patient?.action || "").toString().trim();
    if (!action) return;

    setFinalDecision(action);
    setIsWaitingDecision(false);
    setMessages(prev => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role: "ai",
        content: `Decision medicale: ${action}. Merci de rester disponible pour les instructions du personnel soignant.`,
      },
    ]);
  }, [decisionQuery.data, isWaitingDecision, finalDecision]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, chatMutation.isPending]);

  const handleSend = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isComplete || chatMutation.isPending) return;

    const userMsg = input.trim();
    setInput("");
    setMessages(prev => [...prev, { id: crypto.randomUUID(), role: "user", content: userMsg }]);
    chatMutation.mutate(userMsg);
  };

  const handleReset = () => {
    setSessionId(crypto.randomUUID());
    setMessages([{ id: "1", role: "ai", content: `Bonjour ${username}, je suis votre infirmière IA de triage. Décrivez vos symptômes et je vous poserai des questions pour évaluer votre état.` }]);
    setExtractedData(null);
    setIsComplete(false);
    setIsWaitingDecision(false);
    setFinalDecision(null);
    chatMutation.reset();
  };

  const getUrgencyColor = (u: string) => {
    switch (u) {
      case "critical": return "bg-[var(--danger)] text-white";
      case "high": return "bg-[var(--warning)] text-white";
      case "medium": return "bg-amber-500 text-white";
      case "low": return "bg-[var(--success)] text-white";
      default: return "bg-gray-500 text-white";
    }
  };

  return (
    <div className="flex h-full gap-6">
      {/* Chat Area */}
      <Card className="flex-1 flex flex-col border-[var(--border)] bg-[var(--bg-surface)] overflow-hidden h-[calc(100vh-120px)]">
        <CardHeader className="border-b border-[var(--border)] py-4 px-6 flex flex-row items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[var(--primary-soft)] flex items-center justify-center text-[var(--primary)]">
              <BrainCircuit className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-lg">Infirmière IA de Triage</CardTitle>
              <div className="flex items-center gap-2 text-xs text-[var(--text-dimmed)] mt-0.5">
                <span className="flex h-2 w-2 rounded-full bg-[var(--success)]"></span>
                Session active • {sessionId.substring(0, 8)}
              </div>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={handleReset}>Nouvelle Session</Button>
        </CardHeader>

        <ScrollArea className="flex-1 p-6" ref={scrollRef}>
          <div className="space-y-6">
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex gap-3 max-w-[85%] ${msg.role === "user" ? "ml-auto flex-row-reverse" : ""}`}
              >
                {msg.role === "ai" && (
                  <div className="w-8 h-8 rounded-full bg-[var(--primary-soft)] flex shrink-0 items-center justify-center text-[var(--primary)] mt-1">
                    <BrainCircuit className="w-4 h-4" />
                  </div>
                )}
                <div 
                  className={`p-4 rounded-2xl ${
                    msg.role === "user" 
                      ? "bg-[var(--primary)] text-white rounded-tr-sm" 
                      : "bg-[var(--bg-inset)] border border-[var(--border)] rounded-tl-sm text-[var(--text-main)]"
                  }`}
                >
                  <p className="text-sm leading-relaxed">{msg.content}</p>
                </div>
              </motion.div>
            ))}
            
            {chatMutation.isPending && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3 max-w-[85%]">
                <div className="w-8 h-8 rounded-full bg-[var(--primary-soft)] flex shrink-0 items-center justify-center text-[var(--primary)] mt-1">
                  <BrainCircuit className="w-4 h-4" />
                </div>
                <div className="p-4 rounded-2xl bg-[var(--bg-inset)] border border-[var(--border)] rounded-tl-sm">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-[var(--text-dimmed)] rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></span>
                    <span className="w-2 h-2 bg-[var(--text-dimmed)] rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></span>
                    <span className="w-2 h-2 bg-[var(--text-dimmed)] rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></span>
                  </div>
                </div>
              </motion.div>
            )}

            {isComplete && (
              <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="mx-auto my-6 text-center max-w-md">
                <div className="bg-[var(--success-soft)] border border-[var(--success)] text-[var(--success)] p-4 rounded-xl">
                  <CheckCircle2 className="w-8 h-8 mx-auto mb-2" />
                  <h3 className="font-bold text-lg mb-1">Évaluation complète</h3>
                  <p className="text-sm opacity-90">Vos informations ont été transmises aux agents médicaux pour analyse immédiate.</p>
                </div>
              </motion.div>
            )}

            {isWaitingDecision && (
              <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="mx-auto my-3 text-center max-w-md">
                <div className="bg-[var(--warning-soft)] border border-[var(--warning)] text-[var(--warning)] p-4 rounded-xl">
                  <Loader2 className="w-6 h-6 mx-auto mb-2 animate-spin" />
                  <h3 className="font-bold text-base mb-1">Analyse en cours</h3>
                  <p className="text-sm opacity-90">Veuillez patienter pendant le calcul de la decision finale.</p>
                </div>
              </motion.div>
            )}

            {finalDecision && (
              <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="mx-auto my-3 text-center max-w-md">
                <div className="bg-[var(--primary-soft)] border border-[var(--primary)] text-[var(--primary)] p-4 rounded-xl">
                  <CheckCircle2 className="w-6 h-6 mx-auto mb-2" />
                  <h3 className="font-bold text-base mb-1">Decision finale</h3>
                  <p className="text-sm opacity-90 font-semibold">{finalDecision}</p>
                </div>
              </motion.div>
            )}
          </div>
        </ScrollArea>

        <div className="p-4 bg-[var(--bg-surface)] border-t border-[var(--border)] shrink-0">
          <form onSubmit={handleSend} className="flex gap-3 max-w-4xl mx-auto">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={isComplete ? "Session terminée" : "Décrivez ce que vous ressentez..."}
              className="h-12 bg-[var(--bg-inset)] border-[var(--border)] rounded-full px-6 shadow-sm"
              disabled={isComplete || chatMutation.isPending}
            />
            <Button 
              type="submit" 
              size="icon" 
              className="h-12 w-12 rounded-full bg-[var(--primary)] text-white hover:bg-[var(--primary-h)] shadow-sm shrink-0"
              disabled={!input.trim() || isComplete || chatMutation.isPending}
            >
              <Send className="w-5 h-5" />
            </Button>
          </form>
        </div>
      </Card>

      {/* Side Panel */}
      <AnimatePresence>
        {extractedData && (
          <motion.div
            initial={{ opacity: 0, x: 20, width: 0 }}
            animate={{ opacity: 1, x: 0, width: 320 }}
            className="shrink-0"
          >
            <Card className="border-[var(--border)] bg-[var(--bg-surface)] h-[calc(100vh-120px)] flex flex-col">
              <CardHeader className="py-4 border-b border-[var(--border)] bg-[var(--bg-inset)]/50 shrink-0">
                <CardTitle className="text-sm font-bold flex items-center gap-2 text-[var(--text-main)]">
                  <Activity className="w-4 h-4 text-[var(--primary)]" />
                  Live Clinical Extraction
                </CardTitle>
              </CardHeader>
              <ScrollArea className="flex-1 p-5">
                <div className="space-y-6">
                  <div>
                    <div className="text-xs font-semibold text-[var(--text-dimmed)] uppercase tracking-wider mb-3">Urgence Estimée</div>
                    <Badge className={`w-full justify-center py-1.5 text-sm uppercase tracking-wider font-bold ${getUrgencyColor(extractedData.urgency)} border-transparent`}>
                      {extractedData.urgency}
                    </Badge>
                  </div>

                  <div>
                    <div className="text-xs font-semibold text-[var(--text-dimmed)] uppercase tracking-wider mb-3">Symptômes Détectés</div>
                    <div className="flex flex-wrap gap-1.5">
                      {extractedData.symptoms.length > 0 ? (
                        extractedData.symptoms.map((s, i) => (
                          <Badge key={i} variant="secondary" className="bg-[var(--bg-inset)] border-[var(--border)] text-xs font-medium">
                            {s}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-sm text-[var(--text-dimmed)] italic">Analyse en cours...</span>
                      )}
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-end mb-2">
                      <div className="text-xs font-semibold text-[var(--text-dimmed)] uppercase tracking-wider">Douleur</div>
                      <div className="text-lg font-bold text-[var(--primary)]">{extractedData.pain_level}/10</div>
                    </div>
                    <div className="h-2 bg-[var(--bg-inset)] rounded-full overflow-hidden">
                      <div 
                        className="h-full transition-all duration-500 ease-out" 
                        style={{ 
                          width: `${(extractedData.pain_level / 10) * 100}%`,
                          backgroundColor: extractedData.pain_level > 7 ? 'var(--danger)' : extractedData.pain_level > 4 ? 'var(--warning)' : 'var(--primary)'
                        }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="text-xs font-semibold text-[var(--text-dimmed)] uppercase tracking-wider mb-3">État de Conscience</div>
                    <div className="flex items-center gap-2">
                      <div className={`w-3 h-3 rounded-full ${extractedData.is_conscious ? 'bg-[var(--success)]' : 'bg-[var(--danger)] animate-pulse'}`} />
                      <span className="text-sm font-medium">{extractedData.is_conscious ? "Conscient" : "Altéré / Inconscient"}</span>
                    </div>
                  </div>

                  {extractedData.notes && (
                    <div>
                      <div className="text-xs font-semibold text-[var(--text-dimmed)] uppercase tracking-wider mb-2">Notes</div>
                      <p className="text-sm text-[var(--text-dimmed)] bg-[var(--bg-inset)] p-3 rounded-lg border border-[var(--border)] leading-relaxed">
                        {extractedData.notes}
                      </p>
                    </div>
                  )}

                  <div className="pt-4 border-t border-[var(--border)]">
                    <div className="flex justify-between items-center text-xs mb-1">
                      <span className="text-[var(--text-dimmed)] font-medium">Confiance Modèle</span>
                      <span className="font-bold">{Math.round(extractedData.confidence * 100)}%</span>
                    </div>
                    <div className="h-1.5 bg-[var(--bg-inset)] rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-[var(--primary-soft)] transition-all duration-500" 
                        style={{ width: `${extractedData.confidence * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              </ScrollArea>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Status View ───────────────────────────────────────────────────────────────

function StatusView() {
  const [patientId, setPatientId] = useState("");
  const [searchId, setSearchId] = useState("");

  const { data, isError, isLoading } = useQuery({
    queryKey: ["patient", searchId],
    queryFn: () => getPatients().then(res => res.data.find(p => p.patient_id === searchId || p.id === searchId)),
    enabled: !!searchId,
    refetchInterval: 5000,
  });

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Suivi du Statut</h1>
      
      <Card className="border-[var(--border)] bg-[var(--bg-surface)]">
        <CardContent className="pt-6">
          <div className="flex gap-3">
            <Input
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              placeholder="Entrez votre ID Patient (ex: PAT-1234)"
              className="bg-[var(--bg-inset)]"
              onKeyDown={(e) => {
                if (e.key === 'Enter') setSearchId(patientId);
              }}
            />
            <Button onClick={() => setSearchId(patientId)} className="bg-[var(--primary)] text-white hover:bg-[var(--primary-h)]">
              <Search className="w-4 h-4 mr-2" />
              Rechercher
            </Button>
          </div>
        </CardContent>
      </Card>

      {isLoading && (
        <div className="flex justify-center p-12">
          <Loader2 className="w-8 h-8 animate-spin text-[var(--primary)]" />
        </div>
      )}

      {isError && (
        <div className="p-4 bg-[var(--danger-soft)] text-[var(--danger)] rounded-lg text-center">
          Erreur lors de la recherche. Veuillez réessayer.
        </div>
      )}

      {data === undefined && searchId && !isLoading && !isError && (
        <div className="p-4 bg-[var(--warning-soft)] text-[var(--warning)] rounded-lg text-center">
          Aucun patient trouvé avec l'ID "{searchId}".
        </div>
      )}

      {data && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <Card className="border-[var(--border)] bg-[var(--bg-surface)] overflow-hidden">
            <div className="bg-[var(--bg-inset)] p-4 border-b border-[var(--border)] flex justify-between items-center">
              <div>
                <div className="text-sm text-[var(--text-dimmed)]">Patient</div>
                <div className="font-bold text-lg">{data.name || data.nom}</div>
              </div>
              <Badge variant="outline" className="font-mono bg-[var(--bg-surface)]">
                {data.patient_id || data.id}
              </Badge>
            </div>
            <CardContent className="p-6 space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <div className="text-sm font-medium text-[var(--text-dimmed)] mb-2">Statut Actuel</div>
                  <div className="flex items-center gap-2">
                    <span className="relative flex h-3 w-3">
                      {(data.status === "en_attente" || data.statut === "en_attente") && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--warning)] opacity-75"></span>}
                      <span className={`relative inline-flex rounded-full h-3 w-3 ${(data.status === "en_attente" || data.statut === "en_attente") ? 'bg-[var(--warning)]' : 'bg-[var(--success)]'}`}></span>
                    </span>
                    <span className="font-semibold capitalize">{data.status || data.statut || "Non défini"}</span>
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium text-[var(--text-dimmed)] mb-2">Score Gravité</div>
                  <div className="text-2xl font-bold text-[var(--danger)]">
                    {normalizePatientScore(data.severity_score ?? data.score_gravite ?? (data as any)["score_gravité"]) ?? "--"}/100
                  </div>
                </div>
              </div>

              {(data.action) && (
                <div className="p-4 bg-[var(--primary-soft)] rounded-lg border border-[var(--primary)]/20">
                  <div className="text-sm font-medium text-[var(--primary)] mb-1">Décision Médicale</div>
                  <div className="font-semibold text-lg">{data.action}</div>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  );
}

// ── History View ──────────────────────────────────────────────────────────────

function HistoryView({ username }: { username: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["history", username],
    queryFn: () => getPatients().then(res => res.data.filter(p => (p.name === username || p.nom === username))),
  });

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold">Historique des Admissions</h1>

      <Card className="border-[var(--border)] bg-[var(--bg-surface)]">
        <div className="rounded-md border border-[var(--border)] m-6 overflow-hidden">
          <Table>
            <TableHeader className="bg-[var(--bg-inset)]">
              <TableRow className="hover:bg-transparent">
                <TableHead className="w-[120px]">Date</TableHead>
                <TableHead>ID</TableHead>
                <TableHead>Symptômes</TableHead>
                <TableHead className="text-center">Score</TableHead>
                <TableHead>Décision</TableHead>
                <TableHead className="text-right">Statut</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-24 text-center">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto text-[var(--primary)]" />
                  </TableCell>
                </TableRow>
              ) : !data || data.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-24 text-center text-[var(--text-dimmed)]">
                    Aucun historique trouvé.
                  </TableCell>
                </TableRow>
              ) : (
                data.map((visit, i) => (
                  <TableRow key={i} className="hover:bg-[var(--bg-inset)]/50">
                    <TableCell className="font-medium">
                      {visit.arrival_time ? format(new Date(visit.arrival_time), "dd/MM/yy HH:mm") : "--"}
                    </TableCell>
                    <TableCell className="font-mono text-xs">{visit.patient_id || visit.id}</TableCell>
                    <TableCell className="max-w-[200px] truncate" title={visit.symptoms || visit.symptomes}>
                      {visit.symptoms || visit.symptomes || "--"}
                    </TableCell>
                    <TableCell className="text-center font-bold text-[var(--danger)]">
                      {normalizePatientScore(visit.severity_score ?? visit.score_gravite ?? (visit as any)["score_gravité"]) ?? "--"}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="bg-[var(--bg-inset)]">
                        {visit.action || "--"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Badge className={
                        (visit.status === "traité" || visit.statut === "traité") ? "bg-[var(--success)] hover:bg-[var(--success)] text-white border-transparent" :
                        "bg-[var(--warning)] hover:bg-[var(--warning)] text-white border-transparent"
                      }>
                        {visit.status || visit.statut}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </Card>
    </div>
  );
}
