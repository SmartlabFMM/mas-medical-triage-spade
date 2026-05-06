import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { fr } from "date-fns/locale";
import { useApp } from "@/App";
import {
  Users,
  AlertCircle,
  Activity,
  Clock,
  CheckCircle2,
  RefreshCw,
  ChevronDown,
  Stethoscope,
  UserCheck,
  ArrowRight,
  History,
  Archive,
  Filter,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";
import {
  getDoctorPatients,
  getDoctorStats,
  getDoctorHistory,
  updatePatientStatus,
  DoctorPatient,
  ArchivedPatient,
  getSeverityFromScore,
  getStatusColor,
} from "@/lib/doctorApi";

// ── Valid transitions per status ───────────────────────────────────────────
const VALID_TRANSITIONS: Record<string, string[]> = {
  "En attente":     ["En consultation"],
  "En consultation": ["Traité", "Transféré"],
  "Traité":         [],   // terminal
  "Transféré":      [],   // terminal
};

const STATUS_OPTIONS = [
  { value: "En attente",     label: "En attente",     icon: Clock,        color: "text-yellow-600" },
  { value: "En consultation", label: "En consultation", icon: Stethoscope,  color: "text-blue-600" },
  { value: "Traité",          label: "Traité",          icon: CheckCircle2, color: "text-green-600" },
  { value: "Transféré",       label: "Transféré",       icon: ArrowRight,   color: "text-purple-600" },
];

// ── KPI Card ──────────────────────────────────────────────────────────────
function KPICard({ title, value, icon: Icon, color, bgColor, description }: {
  title: string; value: number; icon: React.ElementType;
  color: string; bgColor: string; description: string;
}) {
  return (
    <Card className={`${bgColor} border-2`}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className={`text-sm font-medium ${color}`}>{title}</p>
            <p className={`text-3xl font-bold ${color}`}>{value}</p>
          </div>
          <div className="w-12 h-12 rounded-full flex items-center justify-center bg-white shadow-sm">
            <Icon className={`w-6 h-6 ${color}`} />
          </div>
        </div>
        <p className={`text-xs mt-2 opacity-80 ${color}`}>{description}</p>
      </CardContent>
    </Card>
  );
}

// ── Patient Row (active queue) ────────────────────────────────────────────
function PatientRow({ patient, onStatusChange, isUpdating }: {
  patient: DoctorPatient;
  onStatusChange: (patientId: string, status: string) => void;
  isUpdating: boolean;
}) {
  const severity = getSeverityFromScore(patient.normalized_score);
  
  // Normalize internal system statuses ("en_attente", "décidé", etc.) to UI expectations
  const rawStatus = patient.statut || patient.status || "En attente";
  
  const stripAccents = (s: string) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const normalizedRaw = stripAccents(rawStatus);

  let currentStatus = "En attente";
  if (normalizedRaw.includes("consultation")) {
    currentStatus = "En consultation";
  } else if (normalizedRaw.startsWith("trait")) {
    currentStatus = "Traité";
  } else if (normalizedRaw.startsWith("transf")) {
    currentStatus = "Transféré";
  }

  const StatusIcon = STATUS_OPTIONS.find((s) => s.value === currentStatus)?.icon || Clock;
  const allowedNext = VALID_TRANSITIONS[currentStatus] ?? [];

  return (
    <div className={`p-4 border-b border-[var(--border)] hover:bg-[var(--bg-inset)] transition-colors ${severity.bgColor}`}>
      <div className="flex items-center justify-between gap-4">
        {/* Score */}
        <div className="flex flex-col items-center min-w-[60px]">
          <span className="text-2xl font-bold">{patient.normalized_score}</span>
          <span className="text-xs opacity-70">/100</span>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-lg truncate">
              {patient.name || patient.nom || "-"}
            </span>
            <Badge className={getStatusColor(currentStatus)}>{currentStatus}</Badge>
            <Badge variant="outline" className={`${severity.color} whitespace-nowrap`}>
              {severity.label}
            </Badge>
          </div>
          <div className="text-sm text-[var(--text-dimmed)]">{patient.age} ans</div>
          <div className="text-sm text-[var(--text-dimmed)] truncate max-w-md mt-1">
            {patient.symptoms || patient.symptomes || "Pas de symptômes"}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="text-xs text-[var(--text-dimmed)] text-right">
            {(patient.arrival_time || patient.heure_arrivée as string)
              ? formatDistanceToNow(
                  new Date(patient.arrival_time || (patient.heure_arrivée as string)),
                  { addSuffix: true, locale: fr }
                )
              : "--"}
          </div>

          {allowedNext.length > 0 ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" disabled={isUpdating} className="flex items-center gap-1">
                  <StatusIcon className="w-4 h-4" />
                  Modifier statut
                  <ChevronDown className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel className="text-xs text-muted-foreground">
                  Transitions possibles
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                {allowedNext.map((nextStatus) => {
                  const opt = STATUS_OPTIONS.find((o) => o.value === nextStatus)!;
                  return (
                    <DropdownMenuItem
                      key={nextStatus}
                      onClick={() => onStatusChange(patient.patient_id, nextStatus)}
                      className={`flex items-center gap-2 ${opt.color}`}
                    >
                      <opt.icon className="w-4 h-4" />
                      {opt.label}
                    </DropdownMenuItem>
                  );
                })}
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Badge variant="outline" className="text-xs text-slate-400">
              Statut final
            </Badge>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Archived patient row (history tab) ───────────────────────────────────
function HistoryRow({ patient }: { patient: ArchivedPatient }) {
  const severity = getSeverityFromScore(patient.normalized_score);
  const status = patient.statut || "";
  const isTransferred = status.toLowerCase().includes("transf");

  return (
    <TableRow className="hover:bg-[var(--bg-inset)]">
      <TableCell className="font-medium truncate max-w-[140px]">
        {patient.nom || patient.name || "-"}
      </TableCell>
      <TableCell>{patient.age}</TableCell>
      <TableCell>
        <span className={`font-bold ${severity.color}`}>{patient.normalized_score}</span>
        <span className="text-xs text-slate-400">/100</span>
      </TableCell>
      <TableCell>
        <Badge className={isTransferred ? "bg-purple-500" : "bg-green-500"}>
          {status || "—"}
        </Badge>
      </TableCell>
      <TableCell className="text-sm text-slate-500 truncate max-w-[160px]">
        {patient.symptomes || patient.symptoms || "—"}
      </TableCell>
      <TableCell className="text-xs text-slate-400 whitespace-nowrap">
        {patient.archived_at
          ? formatDistanceToNow(new Date(patient.archived_at), { addSuffix: true, locale: fr })
          : "—"}
      </TableCell>
    </TableRow>
  );
}

// ── Main Dashboard ────────────────────────────────────────────────────────
export function DoctorDashboard() {
  const { username } = useApp();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<"queue" | "history">("queue");
  const [historyFilter, setHistoryFilter] = useState<"all" | "Traité" | "Transféré">("all");
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  // Fetch active patients
  const {
    data: patientsData,
    isLoading: isLoadingPatients,
    error: patientsError,
    refetch: refetchPatients,
  } = useQuery({
    queryKey: ["doctor-patients", username],
    queryFn: getDoctorPatients,
    refetchInterval: 60000,
  });

  // Fetch stats
  const {
    data: statsData,
    isLoading: isLoadingStats,
    refetch: refetchStats,
  } = useQuery({
    queryKey: ["doctor-stats", username],
    queryFn: getDoctorStats,
    refetchInterval: 60000,
  });

  // Fetch archived history
  const {
    data: historyData,
    isLoading: isLoadingHistory,
    refetch: refetchHistory,
  } = useQuery({
    queryKey: ["doctor-history", username],
    queryFn: getDoctorHistory,
    refetchInterval: 120000,
    enabled: activeTab === "history",
  });

  // Status update mutation (Optimistic UI update)
  const updateStatusMutation = useMutation({
    mutationFn: ({ patientId, status }: { patientId: string; status: string }) =>
      updatePatientStatus(patientId, status),
    onMutate: async ({ patientId, status }) => {
      // Cancel any outgoing refetches so they don't overwrite our optimistic update
      await queryClient.cancelQueries({ queryKey: ["doctor-patients", username] });
      // Snapshot the previous value
      const previousPatients = queryClient.getQueryData(["doctor-patients", username]);

      // Optimistically update to the new value
      queryClient.setQueryData(["doctor-patients", username], (old: any) => {
        if (!old || !old.patients) return old;
        
        let newPatients = [...old.patients];
        
        // If status is a final state (Traité or Transféré), remove from queue instantly
        const isFinal = status.toLowerCase().startsWith('trait') || status.toLowerCase().startsWith('transf');
        
        if (isFinal) {
          newPatients = newPatients.filter((p: any) => p.patient_id !== patientId);
        } else {
          // Otherwise update just the status
          newPatients = newPatients.map((p: any) => 
            p.patient_id === patientId ? { ...p, statut: status, status: status } : p
          );
        }
        
        return {
          ...old,
          patients: newPatients,
          total_patients: newPatients.length
        };
      });

      // Return a context object with the snapshotted value
      return { previousPatients };
    },
    onError: (err, newTodo, context: any) => {
      toast.error(`Erreur: ${err.message}`);
      // Rollback on error
      if (context?.previousPatients) {
        queryClient.setQueryData(["doctor-patients", username], context.previousPatients);
      }
    },
    onSuccess: (data) => {
      toast.success(data.message);
    },
    onSettled: () => {
      // Sync fresh data after mutation finishes
      queryClient.invalidateQueries({ queryKey: ["doctor-patients"] });
      queryClient.invalidateQueries({ queryKey: ["doctor-stats"] });
      queryClient.invalidateQueries({ queryKey: ["doctor-history"] });
    },
  });

  const handleStatusChange = (patientId: string, status: string) => {
    updateStatusMutation.mutate({ patientId, status });
  };

  const handleRefresh = async () => {
    await Promise.all([refetchPatients(), refetchStats(), refetchHistory()]);
    setLastUpdated(new Date());
    toast.success("Données actualisées");
  };

  const isLoading = isLoadingPatients || isLoadingStats;
  const patients = patientsData?.patients || [];
  const stats = statsData;

  // Deduplicate & filter archived patients
  const stripAccents = (s: string) =>
    s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

  const rawHistory = historyData?.history || [];

  // Keep only the most recent entry per patient_id (guard against Sheet duplicates)
  const deduped = Object.values(
    rawHistory.reduce((acc, p) => {
      const key = p.patient_id;
      if (!acc[key] || (p.archived_at || "") > (acc[key].archived_at || "")) {
        acc[key] = p;
      }
      return acc;
    }, {} as Record<string, typeof rawHistory[0]>)
  );

  const filteredHistory = historyFilter === "all"
    ? deduped
    : deduped.filter((p) => {
        const s = stripAccents(p.statut || "");
        if (historyFilter === "Traité")    return s.startsWith("trait");
        if (historyFilter === "Transféré") return s.startsWith("transf");
        return true;
      });

  if (patientsError) {
    return (
      <div className="p-8 text-center">
        <AlertCircle className="w-12 h-12 mx-auto mb-4 text-red-500" />
        <h3 className="text-lg font-semibold text-red-600">Erreur de chargement</h3>
        <p className="text-[var(--text-dimmed)]">{(patientsError as Error).message}</p>
        <Button onClick={handleRefresh} className="mt-4">
          <RefreshCw className="w-4 h-4 mr-2" />
          Réessayer
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">
            {statsData?.doctor_username && `${statsData.doctor_username}`}
          </h2>
          <p className="text-xs text-[var(--text-dimmed)] mt-0.5">
            Mis à jour {formatDistanceToNow(lastUpdated, { addSuffix: true, locale: fr })}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isLoading}>
          <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
          Actualiser
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {isLoadingStats ? (
          Array(4).fill(0).map((_, i) => <Skeleton key={i} className="h-28" />)
        ) : (
          <>
            <KPICard
              title="Total Patients"
              value={stats?.total_patients || 0}
              icon={UserCheck}
              color="text-blue-700"
              bgColor="bg-blue-50 border-blue-300"
              description="Patients actuellement assignés"
            />
            <KPICard
              title="Critiques"
              value={stats?.severity_distribution?.critical || 0}
              icon={AlertCircle}
              color="text-red-700"
              bgColor="bg-red-50 border-red-300"
              description="Score ≥ 80 - Attention immédiate"
            />
            <KPICard
              title="Urgents"
              value={stats?.severity_distribution?.urgent || 0}
              icon={Activity}
              color="text-orange-700"
              bgColor="bg-orange-50 border-orange-300"
              description="Score 60-79 - Priorité élevée"
            />
            <KPICard
              title="Archivés"
              value={historyData?.total || 0}
              icon={Archive}
              color="text-slate-700"
              bgColor="bg-slate-50 border-slate-300"
              description="Traités ou Transférés"
            />
          </>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-[var(--border)]">
        <button
          onClick={() => setActiveTab("queue")}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "queue"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-[var(--text-dimmed)] hover:text-[var(--text-primary)]"
          }`}
        >
          <Users className="w-4 h-4" />
          File d'attente
          {patients.length > 0 && (
            <Badge className="bg-indigo-600 text-white text-xs ml-1 px-1.5 py-0">
              {patients.length}
            </Badge>
          )}
        </button>
        <button
          onClick={() => setActiveTab("history")}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "history"
              ? "border-slate-600 text-slate-700"
              : "border-transparent text-[var(--text-dimmed)] hover:text-[var(--text-primary)]"
          }`}
        >
          <History className="w-4 h-4" />
          Historique
          {(historyData?.total ?? 0) > 0 && (
            <Badge className="bg-slate-500 text-white text-xs ml-1 px-1.5 py-0">
              {historyData?.total}
            </Badge>
          )}
        </button>
      </div>

      {/* ── Tab: Queue ── */}
      {activeTab === "queue" && (
        <Card className="border-[var(--border)] bg-[var(--bg-surface)] flex-1 overflow-hidden flex flex-col">
          <CardHeader className="border-b border-[var(--border)] pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Users className="w-5 h-5" />
              Patients actifs
            </CardTitle>
            <CardDescription>
              Trié par gravité décroissante · Les transitions de statut suivent le cycle de vie médical
            </CardDescription>
            {/* Legend */}
            <div className="flex flex-wrap gap-3 mt-2">
              {STATUS_OPTIONS.map((opt) => (
                <div key={opt.value} className={`flex items-center gap-1 text-xs ${opt.color}`}>
                  <opt.icon className="w-3 h-3" />
                  {opt.value}
                  {opt.value !== "Traité" && opt.value !== "Transféré" && (
                    <ArrowRight className="w-3 h-3 text-slate-300" />
                  )}
                </div>
              ))}
            </div>
          </CardHeader>
          <div className="overflow-auto flex-1">
            {isLoadingPatients ? (
              <div className="p-4 space-y-3">
                {[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-24 w-full" />)}
              </div>
            ) : patients.length === 0 ? (
              <div className="p-8 text-center text-[var(--text-dimmed)]">
                <UserCheck className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p className="font-medium">Aucun patient en file d'attente</p>
                <p className="text-sm">La file d'attente est vide pour le moment.</p>
              </div>
            ) : (
              <div>
                {patients.map((patient) => (
                  <PatientRow
                    key={patient.patient_id}
                    patient={patient}
                    onStatusChange={handleStatusChange}
                    isUpdating={updateStatusMutation.isPending}
                  />
                ))}
              </div>
            )}
          </div>
        </Card>
      )}

      {/* ── Tab: History ── */}
      {activeTab === "history" && (
        <Card className="border-[var(--border)] bg-[var(--bg-surface)] flex-1 overflow-hidden flex flex-col">
          <CardHeader className="border-b border-[var(--border)] pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-base">
                  <History className="w-5 h-5" />
                  Historique des patients archivés
                </CardTitle>
                <CardDescription>
                  Patients traités ou transférés — archivés automatiquement après clôture
                </CardDescription>
              </div>
              {/* Filter */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" className="gap-2">
                    <Filter className="w-4 h-4" />
                    {historyFilter === "all" ? "Tous" : historyFilter}
                    <ChevronDown className="w-4 h-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => setHistoryFilter("all")}>Tous</DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setHistoryFilter("Traité")}>
                    <CheckCircle2 className="w-4 h-4 mr-2 text-green-600" />
                    Traités seulement
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setHistoryFilter("Transféré")}>
                    <ArrowRight className="w-4 h-4 mr-2 text-purple-600" />
                    Transférés seulement
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </CardHeader>
          <div className="overflow-auto flex-1">
            {isLoadingHistory ? (
              <div className="p-4 space-y-3">
                {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
              </div>
            ) : filteredHistory.length === 0 ? (
              <div className="p-8 text-center text-[var(--text-dimmed)]">
                <Archive className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p className="font-medium">Aucun patient archivé</p>
                <p className="text-sm">Les patients Traités ou Transférés apparaîtront ici.</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nom</TableHead>
                    <TableHead>Âge</TableHead>
                    <TableHead>Score</TableHead>
                    <TableHead>Statut final</TableHead>
                    <TableHead>Symptômes</TableHead>
                    <TableHead>Archivé</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredHistory.map((patient) => (
                    <HistoryRow key={patient.patient_id} patient={patient} />
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
