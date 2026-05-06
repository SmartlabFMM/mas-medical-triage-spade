import { useState } from "react";
import { useApp } from "@/App";
import { useLocation } from "wouter";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format, formatDistanceToNow } from "date-fns";
import { fr } from "date-fns/locale";
import {
  getPatients,
  getMetrics,
  getResources,
  getHealth,
  postDecision,
  Patient,
} from "@/lib/api";
import { DoctorDashboard } from "./DoctorDashboard";
import {
  HeartPulse,
  LogOut,
  LayoutDashboard,
  Users,
  BoxSelect,
  AlertCircle,
  Activity,
  CheckCircle2,
  Clock,
  UserSquare,
  Stethoscope,
  Server,
  Database,
  BrainCircuit,
  Loader2,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
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

type Tab = "dashboard";

export default function MedicalPage() {
  const { username, logout } = useApp();
  const [, setLocation] = useLocation();
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");

  const handleLogout = () => {
    logout();
    setLocation("/");
  };

  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: 10000,
  });

  return (
    <div className="flex h-[100dvh] bg-[var(--bg-base)] text-[var(--text-main)] overflow-hidden">
      {/* Sidebar */}
      <div className="w-64 bg-[var(--sidebar-bg)] text-[var(--sidebar-txt)] flex flex-col border-r border-[var(--border-strong)] flex-shrink-0">
        <div 
          className="p-6 flex items-center gap-3 border-b border-[var(--border-strong)]/30 cursor-pointer hover:opacity-80 transition-opacity"
          onClick={() => window.location.href = "/"}
        >
          <HeartPulse className="w-6 h-6 text-[var(--danger)]" />
          <span className="font-bold text-lg tracking-tight">TriageMed Staff</span>
        </div>

        <nav className="flex-1 px-4 space-y-1.5 mt-6">
          <SidebarItem
            icon={<LayoutDashboard />}
            label="Tableau de Bord"
            isActive={activeTab === "dashboard"}
            onClick={() => setActiveTab("dashboard")}
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
            Aujourd'hui le {format(new Date(), "dd/MM/yyyy", { locale: fr })}
          </h1>
          <Button variant="ghost" size="sm" onClick={handleLogout} className="text-[var(--text-dimmed)] hover:text-[var(--danger)]">
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
{activeTab === "dashboard" && <DoctorDashboard key="doctor-dashboard" />}
              </motion.div>
            </AnimatePresence>
          </div>
        </main>
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
          icon={<Activity className="w-6 h-6 text-[var(--warning)]" />} 
          trend="Depuis minuit"
          bgColor="var(--warning-soft)"
        />
      </div>

      <DashboardCharts metrics={metrics} />
    </div>
  );
}

function DashboardCharts({ metrics }: { metrics: any }) {
  // Données pour le graphique de gravité
  const severityData = [
    { name: "Critique", value: metrics.critical_patients || 0, color: "#ef4444" },
    { name: "Urgent", value: metrics.urgent_patients || 0, color: "#f97316" },
    { name: "Modéré", value: metrics.moderate_patients || 0, color: "#eab308" },
    { name: "Faible", value: metrics.low_patients || 0, color: "#22c55e" },
  ];

  // Données pour l'activité (mock mais réalistes)
  const activityData = [
    { hour: "00h", patients: 2 },
    { hour: "04h", patients: 1 },
    { hour: "08h", patients: 5 },
    { hour: "12h", patients: 8 },
    { hour: "16h", patients: 6 },
    { hour: "20h", patients: 4 },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card className="border-[var(--border)] bg-[var(--bg-surface)]">
        <CardHeader>
          <CardTitle>Activité Récente</CardTitle>
          <CardDescription>Évolution des admissions (Dernières 24h)</CardDescription>
        </CardHeader>
        <CardContent className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={activityData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="hour" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--text-dimmed)' }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--text-dimmed)' }} />
              <Tooltip 
                cursor={{ fill: 'var(--bg-inset)' }} 
                contentStyle={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)', borderRadius: '8px' }}
              />
              <Bar dataKey="patients" fill="var(--primary)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
      
      <Card className="border-[var(--border)] bg-[var(--bg-surface)]">
        <CardHeader>
          <CardTitle>Répartition par Gravité</CardTitle>
          <CardDescription>Scores de triage actuels</CardDescription>
        </CardHeader>
        <CardContent className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={severityData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--text-dimmed)' }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--text-dimmed)' }} />
              <Tooltip 
                cursor={{ fill: 'var(--bg-inset)' }} 
                contentStyle={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)', borderRadius: '8px' }}
              />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {severityData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
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

// ── Severity Dashboard View ────────────────────────────────────────────────────

function SeverityView({ username }: { username: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["patients"],
    queryFn: getPatients,
    refetchInterval: 5000,
  });

  const getPatientScore = (patient?: Patient | null): number | undefined => {
    if (!patient) return undefined;
    const raw = patient.severity_score ?? patient.score_gravite ?? patient["score_gravité"];
    if (raw === undefined || raw === null || raw === "") return undefined;
    const parsed = typeof raw === "string" ? Number(raw.replace(",", ".")) : Number(raw);
    if (!Number.isFinite(parsed)) return undefined;
    return Math.max(0, Math.min(100, parsed));
  };

  // Calculate severity counts
  const severityCounts = {
    critical: 0,
    urgent: 0,
    moderate: 0,
    low: 0,
  };

  const patientsWithScores = data?.data?.map((p: Patient) => {
    const score = getPatientScore(p) ?? 0;
    return { ...p, score };
  }) || [];

  patientsWithScores.forEach((p: Patient & { score: number }) => {
    if (p.score >= 80) severityCounts.critical++;
    else if (p.score >= 60) severityCounts.urgent++;
    else if (p.score >= 40) severityCounts.moderate++;
    else severityCounts.low++;
  });

  // Sort patients by severity (highest first)
  const sortedPatients = [...patientsWithScores].sort((a, b) => b.score - a.score);

  const getUrgencyBadge = (score: number = 0) => {
    if (score >= 80) return <Badge className="bg-red-500 hover:bg-red-500 text-white border-transparent">Critique</Badge>;
    if (score >= 60) return <Badge className="bg-orange-500 hover:bg-orange-500 text-white border-transparent">Urgent</Badge>;
    if (score >= 40) return <Badge className="bg-yellow-500 hover:bg-yellow-500 text-white border-transparent">Modéré</Badge>;
    return <Badge className="bg-green-500 hover:bg-green-500 text-white border-transparent">Faible</Badge>;
  };

  const getSeverityColor = (score: number) => {
    if (score >= 80) return "bg-red-100 text-red-800 border-red-300";
    if (score >= 60) return "bg-orange-100 text-orange-800 border-orange-300";
    if (score >= 40) return "bg-yellow-100 text-yellow-800 border-yellow-300";
    return "bg-green-100 text-green-800 border-green-300";
  };

  return (
    <div className="space-y-6 h-full flex flex-col">
      {/* Severity Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="border-red-300 bg-red-50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-red-800">Critique</p>
                <p className="text-2xl font-bold text-red-600">{severityCounts.critical}</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-red-500 flex items-center justify-center">
                <AlertCircle className="w-5 h-5 text-white" />
              </div>
            </div>
            <p className="text-xs text-red-700 mt-2">Score ≥ 80</p>
          </CardContent>
        </Card>

        <Card className="border-orange-300 bg-orange-50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-orange-800">Urgent</p>
                <p className="text-2xl font-bold text-orange-600">{severityCounts.urgent}</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-orange-500 flex items-center justify-center">
                <Activity className="w-5 h-5 text-white" />
              </div>
            </div>
            <p className="text-xs text-orange-700 mt-2">Score 60-79</p>
          </CardContent>
        </Card>

        <Card className="border-yellow-300 bg-yellow-50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-yellow-800">Modéré</p>
                <p className="text-2xl font-bold text-yellow-600">{severityCounts.moderate}</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-yellow-500 flex items-center justify-center">
                <Clock className="w-5 h-5 text-white" />
              </div>
            </div>
            <p className="text-xs text-yellow-700 mt-2">Score 40-59</p>
          </CardContent>
        </Card>

        <Card className="border-green-300 bg-green-50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-green-800">Faible</p>
                <p className="text-2xl font-bold text-green-600">{severityCounts.low}</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-green-500 flex items-center justify-center">
                <CheckCircle2 className="w-5 h-5 text-white" />
              </div>
            </div>
            <p className="text-xs text-green-700 mt-2">Score &lt; 40</p>
          </CardContent>
        </Card>
      </div>

      {/* Patients List Sorted by Severity */}
      <Card className="border-[var(--border)] bg-[var(--bg-surface)] flex-1 overflow-hidden flex flex-col">
        <CardHeader className="border-b border-[var(--border)]">
          <CardTitle className="flex items-center gap-2">
            <Users className="w-5 h-5" />
            Liste des Patients par Niveau de Gravité
          </CardTitle>
          <CardDescription>
            Patients triés du plus critique au moins critique
          </CardDescription>
        </CardHeader>
        <div className="overflow-auto flex-1">
          {isLoading ? (
            <div className="p-4 space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : sortedPatients.length === 0 ? (
            <div className="p-8 text-center text-[var(--text-dimmed)]">
              <AlertCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Aucun patient en attente</p>
            </div>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {sortedPatients.map((patient, index) => (
                <div
                  key={index}
                  className={`p-4 flex items-center justify-between hover:bg-[var(--bg-inset)] transition-colors ${getSeverityColor(patient.score)}`}
                >
                  <div className="flex items-center gap-4">
                    <div className="flex flex-col items-center w-12">
                      <span className="text-2xl font-bold">{patient.score}</span>
                      <span className="text-xs opacity-70">/100</span>
                    </div>
                    <div>
                      <div className="font-semibold">{patient.name || patient.nom || "-"}</div>
                      <div className="text-sm opacity-80">
                        {patient.age} ans • {patient.patient_id || patient.id}
                      </div>
                      <div className="text-sm opacity-70 truncate max-w-xs">
                        {patient.symptoms || patient.symptomes || "Pas de symptômes"}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className="text-xs opacity-70 mb-1">
                        {(patient.arrival_time || (patient as any).heure_arrivée) ? format(new Date(patient.arrival_time || (patient as any).heure_arrivée), "HH:mm") : "--"}
                      </div>
                      <div className="text-xs opacity-60 flex items-center justify-end gap-1">
                        {(patient.arrival_time || (patient as any).heure_arrivée) ? formatDistanceToNow(new Date(patient.arrival_time || (patient as any).heure_arrivée), { addSuffix: true, locale: fr }) : "--"}
                      </div>
                      {getUrgencyBadge(patient.score)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>
    </div>
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
