import { useState, useRef, useEffect } from "react";
import { useApp } from "@/App";
import { useLocation } from "wouter";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  postSymptoms,
  getPatients,
  getResources,
} from "@/lib/api";
import {
  HeartPulse,
  LogOut,
  User,
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ChevronRight,
  Loader2,
  Search,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { format } from "date-fns";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Slider } from "@/components/ui/slider";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

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

interface SymptomDetail {
  name: string;
  intensity: 1 | 2 | 3;
  duration: string;
}

type Tab = "admission" | "status" | "history" | "resources";

function normalizePatientScore(raw: unknown): number | undefined {
  if (raw === undefined || raw === null || raw === "") return undefined;
  const parsed = typeof raw === "string" ? Number(raw.replace(",", ".")) : Number(raw);
  if (!Number.isFinite(parsed)) return undefined;
  return Math.max(0, Math.min(100, parsed));
}

export default function SecretairePage() {
  const { username, logout } = useApp();
  const [, setLocation] = useLocation();
  const [activeTab, setActiveTab] = useState<Tab>("admission");

  const handleLogout = () => {
    logout();
    setLocation("/");
  };

  return (
    <div className="flex h-[100dvh] bg-[var(--bg-inset)] text-[var(--text-main)] overflow-hidden">
      {/* Sidebar */}
      <div className="w-64 bg-[var(--sidebar-bg)] text-[var(--sidebar-txt)] flex flex-col border-r border-[var(--border-strong)] flex-shrink-0">
        <div
          className="p-6 flex items-center gap-3 cursor-pointer hover:opacity-80 transition-opacity"
          onClick={() => window.location.href = "/"}
        >
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
        </nav>

        <div className="p-4 border-t border-[var(--border-strong)] opacity-90 space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[var(--sidebar-active)]/20 flex items-center justify-center text-[var(--sidebar-active)] shrink-0">
              <User className="w-5 h-5" />
            </div>
            <div className="overflow-hidden">
              <div className="text-xs text-[var(--sidebar-txt)]/50 font-medium">secretaire connecté</div>
              <div className="font-semibold text-sm truncate">{username}</div>
            </div>
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
          <Button variant="ghost" size="sm" onClick={handleLogout} className="text-[var(--text-dimmed)] hover:text-[var(--danger)]">
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
                {activeTab === "status" && <StatusView />}
                {activeTab === "history" && <HistoryView username={username} />}
                {activeTab === "resources" && <ResourcesView />}
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
      className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${isActive
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
  const [patientName, setPatientName] = useState("");
  const [age, setAge] = useState("");
  const [gender, setGender] = useState("");
  const [conscious, setConscious] = useState("");
  const [selectedSymptoms, setSelectedSymptoms] = useState<SymptomDetail[]>([]);
  const [customSymptom, setCustomSymptom] = useState("");
  const [customSymptomIntensity, setCustomSymptomIntensity] = useState<1 | 2 | 3>(1);
  const [customSymptomDuration, setCustomSymptomDuration] = useState("");
  const [painLevel, setPainLevel] = useState([5]);
  const addedSymptoms = selectedSymptoms.filter((s) => !COMMON_SYMPTOMS.includes(s.name));
  const [submittedPatientId, setSubmittedPatientId] = useState<string | null>(null);
  const [formError, setFormError] = useState("");

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

  const isValidDuration = (value: string) => {
    const normalized = value.trim().toLowerCase();
    return /^[0-9]+\s*(h|h(?:eures?)?|j|jours?|m|min|mn)$/i.test(normalized);
  };

  const validatePatientStep = () => {
    if (!patientName.trim()) return "Le nom du patient est requis.";
    if (/^\d+$/.test(patientName.trim())) return "Le nom du patient doit contenir des lettres, pas seulement des chiffres.";
    if (!age.trim()) return "L'âge est requis.";
    const ageNumber = Number(age);
    if (!Number.isInteger(ageNumber) || ageNumber <= 0 || ageNumber > 120) {
      return "L'âge doit être un entier entre 1 et 120.";
    }
    if (!gender) return "Le genre est requis.";
    if (!conscious) return "L'état de conscience est requis.";
    return null;
  };

  const validateSymptomStep = () => {
    if (selectedSymptoms.length === 0 && !customSymptom.trim()) {
      return "Veuillez ajouter au moins un symptôme.";
    }
    for (const symptom of selectedSymptoms) {
      if (!symptom.duration.trim()) {
        return `La durée est requise pour le symptôme "${symptom.name}".`;
      }
      if (!isValidDuration(symptom.duration)) {
        return `Durée invalide pour le symptôme "${symptom.name}". Utilisez un format comme 2h, 3j, 15mn.`;
      }
    }
    if (customSymptom.trim()) {
      if (!customSymptomDuration.trim()) {
        return "La durée du symptôme personnalisé est requise.";
      }
      if (!isValidDuration(customSymptomDuration)) {
        return "La durée du symptôme personnalisé est invalide. Utilisez un format comme 2h, 3j, 15mn.";
      }
    }
    return null;
  };

  const handleNext = () => {
    if (step === 1) {
      const error = validatePatientStep();
      if (error) {
        setFormError(error);
        return;
      }
    }

    if (step === 2) {
      const error = validateSymptomStep();
      if (error) {
        setFormError(error);
        return;
      }
    }

    setFormError("");
    if (step < 3) setStep(step + 1);
  };

  const resetForm = () => {
    setStep(1);
    setPatientName("");
    setAge("");
    setGender("");
    setConscious("");
    setSelectedSymptoms([]);
    setCustomSymptom("");
    setCustomSymptomIntensity(1);
    setCustomSymptomDuration("");
    setFormError("");
    setSubmittedPatientId(null);
    submitMutation.reset();
  };

  const handleSubmit = () => {
    const error = validatePatientStep();
    if (error) {
      setFormError(error);
      setStep(1);
      return;
    }

    const symptomError = validateSymptomStep();
    if (symptomError) {
      setFormError(symptomError);
      setStep(2);
      return;
    }

    setFormError("");
    const payload = {
      name: patientName || username || "Patient-Anonyme",
      age: parseInt(age) || 30,
      gender: gender || "M",
      pain_level: 0,
      symptoms: selectedSymptoms.map((s) => s.name),
      symptoms_details: JSON.stringify(
        selectedSymptoms.map((s) => ({
          symptom: s.name,
          intensity: s.intensity,
          duration: s.duration,
        }))
      ),
      conscious: true,
    };
    console.log("[FRONTEND DEBUG] Sending payload:", payload);
    submitMutation.mutate(payload);
  };

  if (submitMutation.data) {
    const res = submitMutation.data;
    const p: any = finalPatientQuery.data;
    const finalAction = p?.action_finale || p?.action || "";
    const finalScore = normalizePatientScore(p?.score_gravite ?? p?.["score_gravité"] ?? p?.severity_score);
    const preliminaryScore = normalizePatientScore(res.severity_score);
    const isFinalized = !!finalAction && String(finalAction).trim() !== "";
    const transferReasonMessage = finalAction === "transférer"
      ? "Aucun lit disponible."
      : "";
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
              <div className="text-sm text-[var(--text-dimmed)] mb-1">Patient</div>
              <div className="font-semibold text-lg">{patientName || "Non renseigné"}</div>
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
            <div className={`p-4 rounded-lg border ${finalAction === "hospitaliser" ? "border-[var(--danger)] bg-[var(--danger-soft)]/30" : "border-[var(--border)]"}`} style={finalAction !== "hospitaliser" && res.decision?.color ? { backgroundColor: `${res.decision.color}10`, borderColor: res.decision.color } : {}}>
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className={`w-5 h-5 ${finalAction === "hospitaliser" ? "text-[var(--danger)]" : ""}`} style={finalAction !== "hospitaliser" && res.decision?.color ? { color: res.decision.color } : {}} />
                <h3 className={`font-semibold ${finalAction === "hospitaliser" ? "text-[var(--danger)]" : ""}`} style={finalAction !== "hospitaliser" && res.decision?.color ? { color: res.decision.color } : {}}>{finalAction}</h3>
              </div>
              {transferReasonMessage ? (
                <div className="mb-3 rounded-md bg-[var(--warning-soft)]/80 border border-[var(--warning)]/40 p-3 text-sm text-[var(--warning)]">
                  {transferReasonMessage}
                </div>
              ) : null}
              {finalAction === "hospitaliser" && (
                <div className="mt-2 pt-2 border-t border-[var(--danger)]/20 space-y-2">
                  {p?.medecin_assigne ? (
                    <div className="flex items-center gap-2 text-sm">
                      <span className="font-medium text-[var(--danger)]">Médecin:</span>
                      <span className="font-bold">{p.medecin_assigne}</span>
                      {p.specialite_assignee && (
                        <Badge variant="outline" className="text-xs bg-white/50 border-[var(--danger)]/30">
                          {p.specialite_assignee}
                        </Badge>
                      )}
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-sm text-[var(--warning)]">
                      <AlertTriangle className="w-4 h-4" />
                      <span className="font-semibold">⚠ Aucun médecin disponible</span>
                    </div>
                  )}
                  {p?.lit_assigne && (
                    <div className="flex items-center gap-2 text-sm">
                      <span className="font-medium text-[var(--danger)]">Lit:</span>
                      <span className="font-bold">{p.lit_assigne}</span>
                    </div>
                  )}
                  {p?.mode_affectation && (
                    <div className="text-xs text-[var(--text-dimmed)]">
                      Mode: {p.mode_affectation}
                    </div>
                  )}
                </div>
              )}
              <p className="text-sm text-[var(--text-dimmed)] mt-2">Décision finale validée par les agents.</p>
            </div>
          )}

          <Button
            className="w-full bg-emerald-600 text-white hover:bg-emerald-700"
            onClick={resetForm}
          >
            Nouvelle Admission
          </Button>
        </CardContent>
      </Card>
    );
  }

  // Form render (step 1, 2, 3)
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
          {formError && (
            <Alert variant="destructive" className="mb-4">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          )}
          {step === 1 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
              <div className="space-y-2">
                <Label>Nom Patient</Label>
                <Input
                  value={patientName}
                  onChange={(e) => setPatientName(e.target.value)}
                  placeholder="Entrez votre nom complet"
                  className="bg-[var(--bg-inset)]"
                  required
                  aria-invalid={Boolean(formError && !patientName.trim())}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Âge</Label>
                  <Input
                    type="number"
                    value={age}
                    onChange={(e) => setAge(e.target.value)}
                    placeholder="Ex: 35"
                    min={1}
                    max={120}
                    step={1}
                    required
                    aria-invalid={Boolean(formError && (!age.trim() || Number(age) <= 0 || Number(age) > 120))}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Genre</Label>
                  <Select value={gender} onValueChange={setGender} aria-invalid={Boolean(formError && !gender)}>
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
                <Select value={conscious} onValueChange={setConscious} aria-invalid={Boolean(formError && !conscious)}>
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
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <Label>Symptômes sélectionnés</Label>
                  <span className="text-xs text-[var(--text-dimmed)]">{selectedSymptoms.length} symptôme(s)</span>
                </div>

                {/* Liste scrollable des symptômes courants */}
                <ScrollArea className="h-[200px] border border-[var(--border)] rounded-lg p-3 bg-[var(--bg-inset)]">
                  <div className="space-y-2">
                    {COMMON_SYMPTOMS.map((sym) => {
                      const existing = selectedSymptoms.find(s => s.name === sym);
                      const isSelected = !!existing;

                      return (
                        <div key={sym} className={`p-3 rounded-lg border transition-all ${isSelected ? 'border-[var(--primary)] bg-[var(--primary-soft)]' : 'border-[var(--border)] bg-[var(--bg-surface)] hover:bg-[var(--bg-inset)]'}`}>
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => {
                                  if (isSelected) {
                                    setSelectedSymptoms(prev => prev.filter(s => s.name !== sym));
                                  } else {
                                    setSelectedSymptoms(prev => [...prev, { name: sym, intensity: 2, duration: "" }]);
                                  }
                                }}
                                className="w-4 h-4 accent-[var(--primary)]"
                              />
                              <span className="font-medium text-sm">{sym}</span>
                            </div>
                            {isSelected && (
                              <Badge
                                variant="outline"
                                className={`text-xs ${existing.intensity === 1 ? 'border-green-300 bg-green-50 text-green-700' : existing.intensity === 2 ? 'border-yellow-300 bg-yellow-50 text-yellow-700' : 'border-red-300 bg-red-50 text-red-700'}`}
                              >
                                {existing.intensity === 1 ? "Faible" : existing.intensity === 2 ? "Modéré" : "Élevé"}
                              </Badge>
                            )}
                          </div>

                          {isSelected && (
                            <div className="flex gap-3 mt-2 pl-6">
                              <div className="flex-1">
                                <Label className="text-xs text-[var(--text-dimmed)] mb-1 block">Intensité</Label>
                                <div className="flex gap-1">
                                  {[1, 2, 3].map((level) => (
                                    <button
                                      key={level}
                                      type="button"
                                      onClick={() => {
                                        setSelectedSymptoms(prev =>
                                          prev.map(s => s.name === sym ? { ...s, intensity: level as 1 | 2 | 3 } : s)
                                        );
                                      }}
                                      className={`flex-1 py-1.5 text-xs font-medium rounded transition-colors ${existing.intensity === level
                                          ? level === 1 ? 'bg-green-500 text-white' : level === 2 ? 'bg-yellow-500 text-white' : 'bg-red-500 text-white'
                                          : 'bg-[var(--bg-inset)] text-[var(--text-dimmed)] hover:bg-[var(--border)]'
                                        }`}
                                    >
                                      {level === 1 ? 'Faible' : level === 2 ? 'Modéré' : 'Élevé'}
                                    </button>
                                  ))}
                                </div>
                              </div>
                              <div className="flex-1">
                                <Label className="text-xs text-[var(--text-dimmed)] mb-1 block">Durée</Label>
                                <Input
                                  type="text"
                                  placeholder="Ex: 2h, 3j"
                                  value={existing.duration}
                                  onChange={(e) => {
                                    setSelectedSymptoms(prev =>
                                      prev.map(s => s.name === sym ? { ...s, duration: e.target.value } : s)
                                    );
                                  }}
                                  className="h-8 text-sm"
                                  required
                                  aria-invalid={Boolean(formError && !existing.duration.trim())}
                                />
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </ScrollArea>

                <div className="space-y-3 rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] p-4">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">Symptômes ajoutés</span>
                    <span className="text-xs text-[var(--text-dimmed)]">{addedSymptoms.length} total</span>
                  </div>
                  {addedSymptoms.length > 0 ? (
                    <div className="space-y-2">
                      {addedSymptoms.map((symptom) => (
                        <div key={symptom.name} className="flex flex-col gap-2 rounded-lg border border-[var(--border)] bg-white p-3">
                          <div className="flex items-center justify-between gap-4">
                            <span className="font-medium">{symptom.name}</span>
                            <Badge
                              variant="outline"
                              className={`text-xs ${symptom.intensity === 1 ? 'border-green-300 bg-green-50 text-green-700' : symptom.intensity === 2 ? 'border-yellow-300 bg-yellow-50 text-yellow-700' : 'border-red-300 bg-red-50 text-red-700'}`}
                            >
                              {symptom.intensity === 1 ? 'Faible' : symptom.intensity === 2 ? 'Modéré' : 'Élevé'}
                            </Badge>
                          </div>
                          {symptom.duration && (
                            <p className="text-xs text-[var(--text-dimmed)]">Durée : {symptom.duration}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm italic text-[var(--text-dimmed)]">Aucun symptôme ajouté pour le moment.</p>
                  )}
                </div>
              </div>

              {/* Ajouter symptôme personnalisé */}
              <div className="space-y-3 border border-[var(--border)] rounded-lg p-3 bg-[var(--bg-surface)]">
                <Label className="text-sm">Ajouter un symptôme personnalisé</Label>
                <div className="grid grid-cols-3 gap-2">
                  <Input
                    value={customSymptom}
                    onChange={(e) => setCustomSymptom(e.target.value)}
                    placeholder="Nom du symptôme"
                    className="col-span-1 text-sm"
                  />
                  <Select
                    value={String(customSymptomIntensity)}
                    onValueChange={(v) => setCustomSymptomIntensity(Number(v) as 1 | 2 | 3)}
                  >
                    <SelectTrigger className="text-sm">
                      <SelectValue placeholder="Intensité" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1" className="bg-green-50 text-green-700 hover:bg-green-100">
                        Faible
                      </SelectItem>
                      <SelectItem value="2" className="bg-yellow-50 text-yellow-700 hover:bg-yellow-100">
                        Modéré
                      </SelectItem>
                      <SelectItem value="3" className="bg-red-50 text-red-700 hover:bg-red-100">
                        Élevé
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <Input
                    value={customSymptomDuration}
                    onChange={(e) => setCustomSymptomDuration(e.target.value)}
                    placeholder="Durée"
                    className="text-sm"
                    required
                    aria-invalid={Boolean(formError && customSymptom.trim() && !customSymptomDuration.trim())}
                  />
                </div>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    if (!customSymptom.trim()) {
                      setFormError("Le nom du symptôme personnalisé est requis.");
                      return;
                    }
                    if (!customSymptomDuration.trim()) {
                      setFormError("La durée du symptôme personnalisé est requise.");
                      return;
                    }
                    if (selectedSymptoms.some((s) => s.name.toLowerCase() === customSymptom.trim().toLowerCase())) {
                      setFormError("Ce symptôme est déjà ajouté.");
                      return;
                    }

                    setSelectedSymptoms([...selectedSymptoms, {
                      name: customSymptom.trim(),
                      intensity: customSymptomIntensity,
                      duration: customSymptomDuration.trim(),
                    }]);
                    setCustomSymptom("");
                    setCustomSymptomIntensity(1);
                    setCustomSymptomDuration("");
                    setFormError("");
                  }}
                  className="w-full"
                >
                  Ajouter le symptôme
                </Button>
              </div>

            </motion.div>
          )}

          {step === 3 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
              <div className="rounded-lg bg-[var(--bg-inset)] border border-[var(--border)] p-4 space-y-4">
                <h3 className="font-semibold text-lg border-b border-[var(--border)] pb-2">Résumé de l'admission</h3>

                <div className="grid grid-cols-2 gap-y-2 text-sm">
                  <div className="text-[var(--text-dimmed)]">Patient</div>
                  <div className="font-medium">{patientName || "Non renseigné"}</div>

                  <div className="text-[var(--text-dimmed)]">Profil</div>
                  <div className="font-medium">{age} ans, {gender}</div>

                  <div className="text-[var(--text-dimmed)]">Conscience</div>
                  <div className="font-medium">{conscious === "oui" ? "Conscient" : "Altéré/Inconscient"}</div>
                </div>

                <div className="pt-2 border-t border-[var(--border)]">
                  <div className="text-sm text-[var(--text-dimmed)] mb-2">Symptômes déclarés ({selectedSymptoms.length})</div>
                  <div className="space-y-1 max-h-[100px] overflow-y-auto">
                    {selectedSymptoms.length > 0 ? (
                      selectedSymptoms.map((s, i) => (
                        <div key={i} className="flex items-center justify-between text-sm">
                          <span className="font-medium">{s.name}</span>
                          <div className="flex items-center gap-2">
                            <Badge
                              variant="outline"
                              className={`text-xs ${s.intensity === 1 ? 'bg-green-100 text-green-700 border-green-300' :
                                  s.intensity === 2 ? 'bg-yellow-100 text-yellow-700 border-yellow-300' :
                                    'bg-red-100 text-red-700 border-red-300'
                                }`}
                            >
                              {s.intensity === 1 ? 'Faible' : s.intensity === 2 ? 'Modéré' : 'Élevé'}
                            </Badge>
                            {s.duration && <span className="text-[var(--text-dimmed)] text-xs">({s.duration})</span>}
                          </div>
                        </div>
                      ))
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
            <Button onClick={handleSubmit} disabled={submitMutation.isPending} className="bg-emerald-600 text-white hover:bg-emerald-700">
              {submitMutation.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              Soumettre l'admission
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}

// ── Resources View ────────────────────────────────────────────────────────────

function ResourcesView() {
  const { data, isLoading } = useQuery({
    queryKey: ["resources"],
    queryFn: getResources,
    refetchInterval: 10000,
  });

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <Card className="border-[var(--border)] bg-[var(--bg-surface)]">
        <CardHeader>
          <CardTitle>Disponibilité des Ressources</CardTitle>
          <CardDescription>Vue en temps réel des équipements et lits</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
            </div>
          ) : !data?.data || data.data.length === 0 ? (
            <div className="p-8 text-center text-[var(--text-dimmed)] bg-[var(--bg-inset)] rounded-xl border border-[var(--border)]">
              Aucune ressource configurée.
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {data.data.map((res, i) => {
                const isAvailable = res.statut === "disponible";
                return (
                  <div
                    key={i}
                    className={`p-4 rounded-xl border ${isAvailable ? 'border-[var(--success)]/30 bg-[var(--success-soft)]/20' : 'border-[var(--danger)]/30 bg-[var(--danger-soft)]/20'} flex flex-col justify-between`}
                  >
                    <div className="flex justify-between items-start mb-3">
                      <div className="font-semibold text-sm">{res.nom_ressource}</div>
                      <span className={`w-2.5 h-2.5 rounded-full ${isAvailable ? 'bg-[var(--success)]' : 'bg-[var(--danger)] animate-pulse'}`} />
                    </div>
                    <div>
                      <div className="text-xs text-[var(--text-dimmed)] uppercase">{res.type} • {res.service}</div>
                      {!isAvailable && res.patient_id && (
                        <div className="text-xs font-mono mt-1 font-medium bg-[var(--bg-surface)] p-1 rounded inline-block">
                          {res.patient_id}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
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
