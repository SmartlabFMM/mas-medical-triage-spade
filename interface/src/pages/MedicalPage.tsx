import { useState } from "react";
import { useApp } from "@/App";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getPatients,
  getMetrics,
  getResources,
  getDecisions,
  getLogs,
  getHealth,
  postDecision,
  Patient,
} from "@/lib/api";
import {
  HeartPulse,
  LogOut,
  LayoutDashboard,
  Users,
  BoxSelect,
  FileCheck,
  TerminalSquare,
  AlertCircle,
  Activity,
  CheckCircle2,
  Clock,
  UserSquare,
  Stethoscope,
  RefreshCw,
  Server,
  Database,
  BrainCircuit,
  Loader2,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { format } from "date-fns";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { Skeleton } from "@/components/ui/skeleton";

type Tab = "dashboard" | "queue" | "resources" | "decisions" | "logs";

export default function MedicalPage() {
  const { username, logout } = useApp();
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");

  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: 10000,
  });

  return (
    <div className="flex h-[100dvh] bg-[var(--bg-base)] text-[var(--text-main)] overflow-hidden">
      {/* Sidebar */}
      <div className="w-64 bg-[var(--sidebar-bg)] text-[var(--sidebar-txt)] flex flex-col border-r border-[var(--border-strong)] flex-shrink-0">
        <div className="p-6 flex items-center gap-3 border-b border-[var(--border-strong)]/30">
          <HeartPulse className="w-6 h-6 text-[var(--danger)]" />
          <span className="font-bold text-lg tracking-tight">TriageMed Staff</span>
        </div>

        <nav className="flex-1 px-4 space-y-1.5 mt-6">
          <SidebarItem
            icon={<LayoutDashboard />}
            label="Dashboard"
            isActive={activeTab === "dashboard"}
            onClick={() => setActiveTab("dashboard")}
          />
          <SidebarItem
            icon={<Users />}
            label="File d'attente"
            isActive={activeTab === "queue"}
            onClick={() => setActiveTab("queue")}
          />
          <SidebarItem
            icon={<BoxSelect />}
            label="Ressources"
            isActive={activeTab === "resources"}
            onClick={() => setActiveTab("resources")}
          />
          <SidebarItem
            icon={<FileCheck />}
            label="Décisions"
            isActive={activeTab === "decisions"}
            onClick={() => setActiveTab("decisions")}
          />
          <SidebarItem
            icon={<TerminalSquare />}
            label="Logs agents"
            isActive={activeTab === "logs"}
            onClick={() => setActiveTab("logs")}
          />
        </nav>

        <div className="p-4 border-t border-[var(--border-strong)] opacity-90 space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[var(--danger-soft)] flex items-center justify-center text-[var(--danger)] shrink-0">
              <Stethoscope className="w-5 h-5" />
            </div>
            <div className="overflow-hidden">
              <div className="text-xs text-[var(--sidebar-txt)]/50 font-medium">Médecin Connecté</div>
              <div className="font-semibold text-sm truncate">{username}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden relative">
        {/* Header */}
        <header className="h-16 bg-[var(--bg-surface)] border-b border-[var(--border)] flex items-center justify-between px-6 shrink-0">
          <h1 className="text-xl font-bold capitalize">
            {activeTab === "dashboard" && "Vue d'ensemble"}
            {activeTab === "queue" && "File d'attente Patients"}
            {activeTab === "resources" && "État des Ressources"}
            {activeTab === "decisions" && "Historique des Décisions"}
            {activeTab === "logs" && "Activité des Agents (Logs)"}
          </h1>
          <Button variant="ghost" size="sm" onClick={logout} className="text-[var(--text-dimmed)] hover:text-[var(--danger)]">
            <LogOut className="w-4 h-4 mr-2" />
            Déconnexion
          </Button>
        </header>

        {/* Tab Content */}
        <main className="flex-1 overflow-auto p-6 pb-24">
          <div className="max-w-7xl mx-auto h-full">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="h-full"
              >
                {activeTab === "dashboard" && <DashboardView />}
                {activeTab === "queue" && <QueueView username={username} />}
                {activeTab === "resources" && <ResourcesView />}
                {activeTab === "decisions" && <DecisionsView />}
                {activeTab === "logs" && <LogsView />}
              </motion.div>
            </AnimatePresence>
          </div>
        </main>

        {/* System Status Bar - Always Visible */}
        <div className="absolute bottom-0 left-0 right-0 h-12 bg-[var(--bg-elevated)] border-t border-[var(--border)] px-6 flex items-center justify-between text-xs font-medium text-[var(--text-dimmed)] z-10 shadow-[0_-4px_12px_rgba(0,0,0,0.05)]">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${health?.status === "ok" ? "bg-[var(--success)]" : "bg-[var(--danger)]"}`} />
              API: {health?.api || "Inconnu"}
            </div>
            <div className="flex items-center gap-2">
              <Database className="w-3.5 h-3.5" />
              Sheets: <span className={health?.sheets ? "text-[var(--success)]" : "text-[var(--danger)]"}>{health?.sheets ? "Connecté" : "Hors ligne"}</span>
            </div>
            <div className="flex items-center gap-2">
              <BrainCircuit className="w-3.5 h-3.5" />
              Modèles: <span className={health?.ml ? "text-[var(--success)]" : "text-[var(--danger)]"}>ML {health?.ml ? "OK" : "HS"}</span> / 
              <span className={health?.llm ? "text-[var(--success)]" : "text-[var(--danger)]"}> LLM {health?.llm ? "OK" : "HS"}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Server className="w-3.5 h-3.5" />
            TriageMed AI v2.0
          </div>
        </div>
      </div>
    </div>
  );
}

function SidebarItem({ icon, label, isActive, onClick }: any) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
        isActive
          ? "bg-[var(--danger)] text-white shadow-sm"
          : "text-[var(--sidebar-txt)]/70 hover:bg-[var(--sidebar-hover)] hover:text-[var(--sidebar-txt)]"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

// ── Views ─────────────────────────────────────────────────────────────────────

function DashboardView() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["metrics"],
    queryFn: getMetrics,
    refetchInterval: 5000,
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-32 rounded-xl" />)}
      </div>
    );
  }

  if (isError || !data?.data) {
    return (
      <div className="p-6 bg-[var(--danger-soft)] text-[var(--danger)] rounded-xl flex items-center gap-3">
        <AlertCircle className="w-6 h-6" />
        <div>
          <div className="font-bold">Service indisponible</div>
          <div className="text-sm opacity-90">Vérifiez que l'API Flask est démarrée sur le port 5000.</div>
        </div>
      </div>
    );
  }

  const metrics = data.data;

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard 
          title="Total Patients" 
          value={metrics.total_patients} 
          icon={<Users className="w-6 h-6 text-[var(--primary)]" />} 
          trend="+12% cette heure"
          bgColor="var(--primary-soft)"
        />
        <StatCard 
          title="Cas Critiques" 
          value={metrics.critical_patients} 
          icon={<AlertCircle className="w-6 h-6 text-[var(--danger)]" />} 
          trend="À traiter en priorité"
          bgColor="var(--danger-soft)"
          valueColor="var(--danger)"
        />
        <StatCard 
          title="Ressources Libres" 
          value={metrics.available_resources} 
          icon={<BoxSelect className="w-6 h-6 text-[var(--success)]" />} 
          trend="Sur 12 au total"
          bgColor="var(--success-soft)"
        />
        <StatCard 
          title="Décisions Rendues" 
          value={metrics.total_decisions} 
          icon={<FileCheck className="w-6 h-6 text-[var(--warning)]" />} 
          trend="Depuis minuit"
          bgColor="var(--warning-soft)"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="border-[var(--border)] bg-[var(--bg-surface)]">
          <CardHeader>
            <CardTitle>Activité Récente</CardTitle>
            <CardDescription>Évolution des admissions (Dernières 24h)</CardDescription>
          </CardHeader>
          <CardContent className="h-64 flex items-center justify-center text-[var(--text-dimmed)] bg-[var(--bg-inset)]/30 rounded-lg mx-6 mb-6">
            Graphique d'activité (Mock)
          </CardContent>
        </Card>
        
        <Card className="border-[var(--border)] bg-[var(--bg-surface)]">
          <CardHeader>
            <CardTitle>Répartition par Gravité</CardTitle>
            <CardDescription>Scores de triage actuels</CardDescription>
          </CardHeader>
          <CardContent className="h-64 flex items-center justify-center text-[var(--text-dimmed)] bg-[var(--bg-inset)]/30 rounded-lg mx-6 mb-6">
            Graphique de répartition (Mock)
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon, trend, bgColor, valueColor = "var(--text-main)" }: any) {
  return (
    <Card className="border-[var(--border)] bg-[var(--bg-surface)] overflow-hidden">
      <CardContent className="p-6">
        <div className="flex justify-between items-start">
          <div className="space-y-2">
            <p className="text-sm font-medium text-[var(--text-dimmed)]">{title}</p>
            <p className="text-3xl font-bold tracking-tight" style={{ color: valueColor }}>{value !== undefined ? value : "--"}</p>
          </div>
          <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ backgroundColor: bgColor }}>
            {icon}
          </div>
        </div>
        <div className="mt-4 text-xs font-medium text-[var(--text-dimmed)]">
          {trend}
        </div>
      </CardContent>
    </Card>
  );
}

function QueueView({ username }: { username: string }) {
  const queryClient = useQueryClient();
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [decisionAction, setDecisionAction] = useState("");

  const getPatientScore = (patient?: Patient | null): number | undefined => {
    if (!patient) return undefined;
    const raw = patient.severity_score ?? patient.score_gravite ?? patient["score_gravité"];
    if (raw === undefined || raw === null || raw === "") return undefined;
    const parsed = typeof raw === "string" ? Number(raw.replace(",", ".")) : Number(raw);
    if (!Number.isFinite(parsed)) return undefined;
    return Math.max(0, Math.min(100, parsed));
  };

  const { data, isLoading } = useQuery({
    queryKey: ["patients"],
    queryFn: getPatients,
    refetchInterval: 5000,
  });

  const decisionMutation = useMutation({
    mutationFn: postDecision,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["patients"] });
      queryClient.invalidateQueries({ queryKey: ["decisions"] });
      setSelectedPatient(null);
    }
  });

  const handleDecision = () => {
    if (selectedPatient && decisionAction) {
      decisionMutation.mutate({
        patient_id: selectedPatient.patient_id || selectedPatient.id || "",
        action: decisionAction,
        score: getPatientScore(selectedPatient),
        validated_by: username,
      });
    }
  };

  const getUrgencyBadge = (score: number = 0) => {
    if (score >= 80) return <Badge className="bg-[var(--danger)] hover:bg-[var(--danger)] text-white border-transparent">Critique</Badge>;
    if (score >= 60) return <Badge className="bg-[var(--warning)] hover:bg-[var(--warning)] text-white border-transparent">Élevé</Badge>;
    if (score >= 40) return <Badge className="bg-amber-500 hover:bg-amber-500 text-white border-transparent">Moyen</Badge>;
    return <Badge className="bg-[var(--success)] hover:bg-[var(--success)] text-white border-transparent">Faible</Badge>;
  };

  return (
    <div className="space-y-6 h-full flex flex-col">
      <div className="flex justify-between items-center shrink-0">
        <div className="relative w-64">
          <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-dimmed)]" />
          <Input placeholder="Rechercher un patient..." className="pl-9 bg-[var(--bg-surface)]" />
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="bg-[var(--bg-surface)]">
            <Clock className="w-3 h-3 mr-1" /> Actualisation Auto (5s)
          </Badge>
        </div>
      </div>

      <Card className="border-[var(--border)] bg-[var(--bg-surface)] flex-1 overflow-hidden flex flex-col">
        <div className="overflow-auto flex-1">
          <Table>
            <TableHeader className="bg-[var(--bg-inset)] sticky top-0 z-10 shadow-sm">
              <TableRow className="hover:bg-transparent">
                <TableHead>Patient</TableHead>
                <TableHead>Âge</TableHead>
                <TableHead className="max-w-xs">Symptômes</TableHead>
                <TableHead className="text-center">Score</TableHead>
                <TableHead className="text-center">Urgence</TableHead>
                <TableHead>Statut</TableHead>
                <TableHead className="text-right">Heure</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-8" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-48" /></TableCell>
                    <TableCell><Skeleton className="h-8 w-12 mx-auto" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-16 mx-auto" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-16 ml-auto" /></TableCell>
                  </TableRow>
                ))
              ) : !data?.data || data.data.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-32 text-center text-[var(--text-dimmed)]">
                    La file d'attente est vide.
                  </TableCell>
                </TableRow>
              ) : (
                data.data.map((patient, i) => {
                  const score = getPatientScore(patient) ?? 0;
                  const isCritical = score >= 80;
                  return (
                    <TableRow 
                      key={i} 
                      className={`cursor-pointer transition-colors ${isCritical ? 'bg-[var(--danger-soft)]/30 hover:bg-[var(--danger-soft)]/60' : 'hover:bg-[var(--bg-inset)]/50'}`}
                      onClick={() => setSelectedPatient(patient)}
                    >
                      <TableCell>
                        <div className="font-semibold">{patient.name || patient.nom}</div>
                        <div className="text-xs text-[var(--text-dimmed)] font-mono">{patient.patient_id || patient.id}</div>
                      </TableCell>
                      <TableCell>{patient.age}</TableCell>
                      <TableCell className="max-w-xs truncate" title={patient.symptoms || patient.symptomes}>
                        {patient.symptoms || patient.symptomes || "--"}
                      </TableCell>
                      <TableCell className="text-center">
                        <span className={`font-bold text-lg ${isCritical ? 'text-[var(--danger)]' : score >= 60 ? 'text-[var(--warning)]' : 'text-[var(--text-main)]'}`}>
                          {score}
                        </span>
                      </TableCell>
                      <TableCell className="text-center">
                        {getUrgencyBadge(score)}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="capitalize bg-transparent">
                          {patient.status || patient.statut || "en_attente"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right text-sm text-[var(--text-dimmed)]">
                        {patient.arrival_time ? format(new Date(patient.arrival_time), "HH:mm") : "--"}
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>
      </Card>

      <Dialog open={!!selectedPatient} onOpenChange={(open) => !open && setSelectedPatient(null)}>
        <DialogContent className="sm:max-w-[500px] border-[var(--border)] bg-[var(--bg-surface)]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-xl">
              <Stethoscope className="w-5 h-5 text-[var(--primary)]" />
              Décision Médicale
            </DialogTitle>
            <DialogDescription>
              Valider ou modifier la décision pour ce patient.
            </DialogDescription>
          </DialogHeader>

          {selectedPatient && (
            <div className="space-y-6 py-4">
              <div className="p-4 bg-[var(--bg-inset)] rounded-xl border border-[var(--border)] space-y-3">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-bold text-lg">{selectedPatient.name || selectedPatient.nom}</div>
                    <div className="text-sm font-mono text-[var(--text-dimmed)]">{selectedPatient.patient_id || selectedPatient.id}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-medium text-[var(--text-dimmed)]">Score</div>
                    <div className="text-2xl font-bold text-[var(--danger)]">{getPatientScore(selectedPatient) ?? "--"}/100</div>
                  </div>
                </div>
                
                <div>
                  <div className="text-xs font-medium text-[var(--text-dimmed)] uppercase tracking-wider mb-1">Symptômes</div>
                  <p className="text-sm">{selectedPatient.symptoms || selectedPatient.symptomes}</p>
                </div>
                
                <div>
                  <div className="text-xs font-medium text-[var(--text-dimmed)] uppercase tracking-wider mb-1">Action Suggérée (IA)</div>
                  <Badge variant="secondary" className="font-medium text-sm">
                    {selectedPatient.action || "Aucune"}
                  </Badge>
                </div>
              </div>

              <div className="space-y-3">
                <Label htmlFor="decision" className="text-sm font-semibold">Votre Décision</Label>
                <Input 
                  id="decision"
                  placeholder="Ex: Admission immédiate Box Déchocage"
                  value={decisionAction}
                  onChange={(e) => setDecisionAction(e.target.value)}
                  className="bg-[var(--bg-surface)] border-[var(--border-strong)]"
                />
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedPatient(null)}>Annuler</Button>
            <Button 
              onClick={handleDecision} 
              disabled={!decisionAction || decisionMutation.isPending}
              className="bg-[var(--danger)] text-white hover:bg-[var(--danger)]/90"
            >
              {decisionMutation.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              Valider la décision
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function ResourcesView() {
  const { data, isLoading } = useQuery({
    queryKey: ["resources"],
    queryFn: getResources,
    refetchInterval: 10000,
  });

  const chartData = [
    { name: 'Urgences', total: 6, occ: 4 },
    { name: 'Réa', total: 4, occ: 3 },
    { name: 'Radio', total: 3, occ: 1 },
    { name: 'Scan', total: 2, occ: 2 },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 border-[var(--border)] bg-[var(--bg-surface)]">
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

        <Card className="border-[var(--border)] bg-[var(--bg-surface)]">
          <CardHeader>
            <CardTitle>Taux d'occupation</CardTitle>
            <CardDescription>Par service</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--text-dimmed)' }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--text-dimmed)' }} />
                <Tooltip 
                  cursor={{ fill: 'var(--bg-inset)' }} 
                  contentStyle={{ backgroundColor: 'var(--bg-elevated)', borderColor: 'var(--border)', borderRadius: '8px' }}
                />
                <Bar dataKey="occ" name="Occupé" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.occ / entry.total > 0.8 ? 'var(--danger)' : 'var(--primary)'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function DecisionsView() {
  const { data, isLoading } = useQuery({
    queryKey: ["decisions"],
    queryFn: getDecisions,
    refetchInterval: 10000,
  });

  return (
    <Card className="border-[var(--border)] bg-[var(--bg-surface)] h-full flex flex-col">
      <div className="p-6 border-b border-[var(--border)] flex justify-between items-center shrink-0">
        <div>
          <h2 className="text-lg font-bold">Historique des Décisions</h2>
          <p className="text-sm text-[var(--text-dimmed)]">Toutes les décisions validées par le staff médical.</p>
        </div>
      </div>
      <div className="overflow-auto flex-1">
        <Table>
          <TableHeader className="bg-[var(--bg-inset)] sticky top-0 z-10">
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Patient ID</TableHead>
              <TableHead className="text-center">Score</TableHead>
              <TableHead>Action</TableHead>
              <TableHead>Justification</TableHead>
              <TableHead>Décidé par</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="h-32 text-center">
                  <Loader2 className="w-6 h-6 animate-spin mx-auto text-[var(--primary)]" />
                </TableCell>
              </TableRow>
            ) : !data?.data || data.data.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-32 text-center text-[var(--text-dimmed)]">
                  Aucune décision enregistrée.
                </TableCell>
              </TableRow>
            ) : (
              data.data.map((dec, i) => (
                <TableRow key={i} className="hover:bg-[var(--bg-inset)]/50">
                  <TableCell className="text-sm text-[var(--text-dimmed)] whitespace-nowrap">
                    {dec.timestamp ? format(new Date(dec.timestamp), "dd/MM/yy HH:mm") : "--"}
                  </TableCell>
                  <TableCell className="font-mono text-xs font-medium">{dec.patient_id}</TableCell>
                  <TableCell className="text-center font-bold">{dec.severity_score}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className="font-semibold bg-[var(--bg-surface)]">
                      {dec.action}
                    </Badge>
                  </TableCell>
                  <TableCell className="max-w-xs truncate text-sm" title={dec.rationale}>
                    {dec.rationale || "--"}
                  </TableCell>
                  <TableCell className="text-sm font-medium">
                    {dec.decided_by || "--"}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </Card>
  );
}

function LogsView() {
  const queryClient = useQueryClient();
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["logs"],
    queryFn: () => getLogs(100),
    refetchInterval: 5000,
  });

  const getLevelColor = (level: string = "INFO") => {
    switch (level.toUpperCase()) {
      case "ERROR": return "bg-[var(--danger-soft)] text-[var(--danger)] border-[var(--danger)]/30";
      case "WARNING": return "bg-[var(--warning-soft)] text-[var(--warning)] border-[var(--warning)]/30";
      default: return "bg-[var(--primary-soft)] text-[var(--primary)] border-[var(--primary)]/30";
    }
  };

  return (
    <Card className="border-[var(--border)] bg-[var(--bg-surface)] h-full flex flex-col font-mono text-sm">
      <div className="p-4 border-b border-[var(--border)] bg-[var(--bg-inset)] flex justify-between items-center shrink-0">
        <div className="flex items-center gap-2 font-bold text-[var(--text-main)] font-sans">
          <TerminalSquare className="w-5 h-5 text-[var(--primary)]" />
          Trace des Agents Multi-Agent (BDI)
        </div>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={() => queryClient.invalidateQueries({ queryKey: ["logs"] })}
          disabled={isFetching}
          className="font-sans h-8"
        >
          <RefreshCw className={`w-3.5 h-3.5 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
          Rafraîchir
        </Button>
      </div>
      
      <div className="overflow-auto flex-1 p-4 bg-[#0a0a0a] text-gray-300">
        {isLoading ? (
          <div className="flex justify-center p-8">
            <Loader2 className="w-6 h-6 animate-spin text-gray-500" />
          </div>
        ) : !data?.data || data.data.length === 0 ? (
          <div className="text-gray-500 italic">Aucun log disponible.</div>
        ) : (
          <div className="space-y-1.5">
            {data.data.map((log, i) => (
              <div key={i} className="flex items-start gap-3 hover:bg-white/5 p-1 rounded">
                <span className="text-gray-500 shrink-0 w-32">
                  {log.timestamp ? format(new Date(log.timestamp), "yyyy-MM-dd HH:mm:ss") : "----"}
                </span>
                <span className={`px-2 py-0.5 rounded text-xs font-bold shrink-0 w-20 text-center ${getLevelColor(log.niveau)}`}>
                  {log.niveau || "INFO"}
                </span>
                <span className="text-blue-400 font-bold shrink-0 w-32">[{log.agent || "SYSTEM"}]</span>
                <span className="text-yellow-300 font-semibold shrink-0 w-40">{log.action || "ACT"}</span>
                {log.patient_id && <span className="text-purple-400 shrink-0">{log.patient_id}</span>}
                <span className="text-gray-300 break-words">{log.details}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

// Minimal icon to avoid import issues
function SearchIcon(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  );
}
