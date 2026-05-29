import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useLocation } from "wouter";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  Legend,
} from "recharts";
import {
  Users,
  Bed,
  Stethoscope,
  Activity,
  AlertTriangle,
  RefreshCw,
  Plus,
  Trash2,
  Edit2,
  CheckCircle,
  XCircle,
  LogOut,
  LayoutDashboard,
  Shield,
  Search,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
import {
  getAdminDashboard,
  getAdminResources,
  getAdminDoctors,
  getAdminPatients,
  getAdminDecisions,
  createAdminResource,
  deleteAdminResource,
  createAdminDoctor,
  updateAdminDoctor,
  deleteAdminDoctor,
} from "@/lib/api";
import { toast } from "sonner";

const COLORS = ["#22c55e", "#f59e0b", "#ef4444", "#a62121"];

const normalizeSeverityScore = (raw?: string | number): number | undefined => {
  if (raw === undefined || raw === null) return undefined;
  const parsed = typeof raw === "string" ? Number(raw.replace(",", ".")) : raw;
  return Number.isFinite(parsed) ? parsed : undefined;
};

interface DashboardData {
  patients_today: number;
  severity_distribution: {
    léger: number;
    modéré: number;
    urgent: number;
    critique: number;
  };
  bed_occupancy_rate: number;
  available_beds: number;
  total_beds: number;
  doctors_available_by_specialty: Record<string, number>;
  total_doctors: number;
  transfers: number;
  hospitalization_rate: number;
  critical_detected: number;
  doctor_load: Array<{
    name: string;
    specialty: string;
    available: boolean;
    patient_count: number;
  }>;
  daily_stats: Record<string, { total: number; critical: number; hospitalized: number }>;
  hourly_stats: Record<string, { total: number; critical: number; hospitalized: number }>;
  timestamp: string;
}

interface Resource {
  nom_ressource: string;
  type?: string;
  disponibilite?: string;
  patient_assigne?: string;
  statut?: string;
  derniere_maj?: string;
}

interface Doctor {
  doctor_id: string;
  nom: string;
  specialite: string;
  disponible: string;
  patient_assigne?: string;
  derniere_maj?: string;
}

interface Patient {
  patient_id?: string;
  nom?: string;
  age?: number;
  genre?: string;
  score_gravité?: number | string;
  action_finale?: string;
  medecin_assigne?: string;
  lit_assigne?: string;
  statut?: string;
  heure_arrivée?: string;
}

interface Decision {
  patient_id: string;
  score_gravite?: number;
  action: string;
  timestamp?: string;
}

function SidebarItem({ icon, label, isActive, onClick }: any) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${isActive
        ? "bg-yellow-500 text-white shadow-sm"
        : "text-[var(--sidebar-txt)]/70 hover:bg-[var(--sidebar-hover)] hover:text-[var(--sidebar-txt)]"
        }`}
    >
      {icon}
      {label}
    </button>
  );
}

export default function AdminPage() {
  const [, setLocation] = useLocation();
  const [activeTab, setActiveTab] = useState("dashboard");
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [resources, setResources] = useState<Resource[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [newResourceName, setNewResourceName] = useState("");
  const [newDoctorName, setNewDoctorName] = useState("");
  const [newDoctorSpecialty, setNewDoctorSpecialty] = useState("");
  const [filterDoctorName, setFilterDoctorName] = useState("");
  const [filterDoctorSpecialty, setFilterDoctorSpecialty] = useState("");
  const [filterPatientName, setFilterPatientName] = useState("");
  const [filterPatientStatus, setFilterPatientStatus] = useState("all");
  const [timeFilter, setTimeFilter] = useState("week");

  const handleLogout = () => {
    sessionStorage.removeItem("userRole");
    sessionStorage.removeItem("username");
    setLocation("/");
  };

  const specialties = [
    "Urgences",
    "Cardiologie",
    "Neurologie",
    "Pneumologie",
    "Généraliste",
  ];

  const fetchDashboard = async () => {
    try {
      const data = await getAdminDashboard();
      setDashboardData(data);
    } catch (error) {
      toast.error("Échec du chargement des données du tableau de bord");
    }
  };

  const fetchResources = async () => {
    try {
      const data = await getAdminResources();
      setResources(data);
    } catch (error) {
      toast.error("Échec du chargement des ressources");
    }
  };

  const fetchDoctors = async () => {
    try {
      const data = await getAdminDoctors();
      setDoctors(data);
    } catch (error) {
      toast.error("Échec du chargement des médecins");
    }
  };

  const fetchPatients = async () => {
    try {
      const data = await getAdminPatients();
      // Supprimer les doublons en se basant sur le patient_id
      const uniquePatients = Array.from(new Map(data.map(p => [p.patient_id, p])).values());
      setPatients(uniquePatients);
    } catch (error) {
      toast.error("Échec du chargement des patients");
    }
  };

  const fetchDecisions = async () => {
    try {
      const data = await getAdminDecisions();
      setDecisions(data);
    } catch (error) {
      toast.error("Échec du chargement des décisions");
    }
  };

  const loadAllData = async () => {
    setIsLoading(true);
    await Promise.all([
      fetchDashboard(),
      fetchResources(),
      fetchDoctors(),
      fetchPatients(),
      fetchDecisions(),
    ]);
    setIsLoading(false);
  };

  useEffect(() => {
    loadAllData();
    const interval = setInterval(loadAllData, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleAddResource = async () => {
    if (!newResourceName.trim()) {
      toast.error("Le nom de la ressource est requis");
      return;
    }
    try {
      await createAdminResource({
        nom_ressource: newResourceName,
        type: "Lit",
      });
      toast.success("Ressource ajoutée avec succès");
      setNewResourceName("");
      fetchResources();
      fetchDashboard();
    } catch (error) {
      toast.error("Échec de l'ajout de la ressource");
    }
  };

  const handleDeleteResource = async (nom_ressource: string) => {
    try {
      await deleteAdminResource(nom_ressource);
      toast.success("Ressource supprimée");
      fetchResources();
      fetchDashboard();
    } catch (error) {
      toast.error("Échec de la suppression de la ressource");
    }
  };

  const handleAddDoctor = async () => {
    if (!newDoctorName.trim() || !newDoctorSpecialty) {
      toast.error("Le nom et la spécialité du médecin sont requis");
      return;
    }
    try {
      await createAdminDoctor({
        nom: newDoctorName,
        specialite: newDoctorSpecialty,
      });
      toast.success("Médecin ajouté avec succès");
      setNewDoctorName("");
      setNewDoctorSpecialty("");
      fetchDoctors();
      fetchDashboard();
    } catch (error) {
      toast.error("Échec de l'ajout du médecin");
    }
  };

  const handleDeleteDoctor = async (doctor_id: string) => {
    try {
      await deleteAdminDoctor(doctor_id);
      toast.success("Médecin supprimé");
      fetchDoctors();
      fetchDashboard();
    } catch (error) {
      toast.error("Échec de la suppression du médecin");
    }
  };

  const handleToggleDoctorAvailability = async (doctor: Doctor) => {
    try {
      await updateAdminDoctor({
        doctor_id: doctor.doctor_id,
        disponible: doctor.disponible.toLowerCase() !== "true",
      });
      toast.success("Disponibilité du médecin mise à jour");
      fetchDoctors();
      fetchDashboard();
    } catch (error) {
      toast.error("Échec de la mise à jour du médecin");
    }
  };

  const severityData = dashboardData
    ? [
      { name: "Léger", value: dashboardData.severity_distribution.léger },
      { name: "Modéré", value: dashboardData.severity_distribution.modéré },
      { name: "Urgent", value: dashboardData.severity_distribution.urgent },
      { name: "Critique", value: dashboardData.severity_distribution.critique },
    ]
    : [];

  const dailyStatsData = dashboardData
    ? timeFilter === "day"
      ? Object.entries(dashboardData.hourly_stats ?? {})
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([hour, stats]) => ({
          date: hour,
          total: stats.total,
          critical: stats.critical,
          hospitalized: stats.hospitalized,
        }))
      : Object.entries(dashboardData.daily_stats)
        .slice(timeFilter === "week" ? -7 : -30)
        .map(([date, stats]) => ({
          date: date.slice(5),
          total: stats.total,
          critical: stats.critical,
          hospitalized: stats.hospitalized,
        }))
    : [];

  const doctorSpecialtyData = dashboardData
    ? Object.entries(dashboardData.doctors_available_by_specialty).map(
      ([specialty, count]) => ({
        name: specialty,
        value: count,
      })
    )
    : [];

  const renderContent = () => {
    switch (activeTab) {
      case "dashboard":
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-blue-700 flex items-center gap-2">
                      <Users className="w-4 h-4" />
                      Patients Aujourd'hui
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold text-blue-900">
                      {dashboardData?.patients_today || 0}
                    </div>
                    <div className="text-xs text-blue-600 mt-1">Total admissions</div>
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <Card className="bg-gradient-to-br from-rose-50 to-red-50 border-rose-200">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-rose-700 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4" />
                      Cas Critiques
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold text-rose-900">
                      {dashboardData?.critical_detected || 0}
                    </div>
                    <div className="text-xs text-rose-600 mt-1">Score ≥ 80</div>
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <Card className="bg-gradient-to-br from-violet-50 to-purple-50 border-violet-200">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-violet-700 flex items-center gap-2">
                      <Stethoscope className="w-4 h-4" />
                      Médecins Disponibles
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold text-violet-900">
                      {Object.values(dashboardData?.doctors_available_by_specialty || {}).reduce(
                        (a, b) => a + b,
                        0
                      )}
                    </div>
                    <div className="text-xs text-violet-600 mt-1">Prêts à prendre en charge</div>
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <Card className="bg-gradient-to-br from-emerald-50 to-teal-50 border-emerald-200">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-emerald-700 flex items-center gap-2">
                      <Bed className="w-4 h-4" />
                      Lits Disponibles
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold text-emerald-900">
                      {dashboardData?.available_beds || 0}
                    </div>
                    <div className="text-xs text-emerald-600 mt-1">Sur {dashboardData?.total_beds || 0} total</div>
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="col-span-1 border-[var(--border)] bg-[var(--bg-surface)]">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="w-5 h-5 text-indigo-600" />
                    Répartition par Niveau de Gravité
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={severityData}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={({ name, value }) => `${name}: ${value}`}
                          outerRadius={80}
                          fill="#8884d8"
                          dataKey="value"
                        >
                          {severityData.map((entry, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={COLORS[index % COLORS.length]}
                            />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card className="col-span-1 border-[var(--border)] bg-[var(--bg-surface)]">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Stethoscope className="w-5 h-5 text-indigo-600" />
                    Médecins Disponibles par Spécialité
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={doctorSpecialtyData}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={({ name, value }) => `${name}: ${value}`}
                          outerRadius={80}
                          fill="#180ceb"
                          dataKey="value"
                        >
                          {doctorSpecialtyData.map((entry, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={`hsl(220, 90%, ${30 + (index * 10)}%)`}
                            />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card className="col-span-1 lg:col-span-2 border-[var(--border)] bg-[var(--bg-surface)]">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2">
                      <Activity className="w-5 h-5 text-indigo-600" />
                      Évolution des Patients
                    </CardTitle>
                    <Select value={timeFilter} onValueChange={setTimeFilter}>
                      <SelectTrigger className="w-32">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="day">Jour</SelectItem>
                        <SelectItem value="week">Semaine</SelectItem>
                        <SelectItem value="month">Mois</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={dailyStatsData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Line
                          type="monotone"
                          dataKey="total"
                          stroke="#6366f1"
                          name="Total"
                          strokeWidth={2}
                        />
                        <Line
                          type="monotone"
                          dataKey="critical"
                          stroke="#ef4444"
                          name="Critiques"
                          strokeWidth={2}
                        />
                        <Line
                          type="monotone"
                          dataKey="hospitalized"
                          stroke="#22c55e"
                          name="Hospitalisés"
                          strokeWidth={2}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </div>

          </div>
        );
      case "resources":
        return (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold">Gestion des Ressources</h2>
              <Dialog>
                <DialogTrigger asChild>
                  <Button className="gap-2 bg-blue-900 hover:bg-blue-800">
                    <Plus className="w-4 h-4" />
                    Ajouter un Lit
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Ajouter un nouveau lit</DialogTitle>
                    <DialogDescription>
                      Entrez le nom du lit à ajouter au système.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label htmlFor="resource-name">Nom du lit</Label>
                      <Input
                        id="resource-name"
                        placeholder="Ex: Lit-A16"
                        value={newResourceName}
                        onChange={(e) => setNewResourceName(e.target.value)}
                        required
                        aria-invalid={!newResourceName.trim()}
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button onClick={handleAddResource} className="bg-blue-900 hover:bg-blue-800">Ajouter</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>

            <Card className="border-[var(--border)] bg-[var(--bg-surface)]">
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nom</TableHead>
                      <TableHead>Statut</TableHead>
                      <TableHead>Patient Assigné</TableHead>
                      <TableHead>Dernière MàJ</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {resources.map((resource) => (
                      <TableRow key={resource.nom_ressource}>
                        <TableCell className="font-medium">
                          {resource.nom_ressource}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              resource.statut === "disponible"
                                ? "default"
                                : "destructive"
                            }
                            className={
                              resource.statut === "disponible"
                                ? "bg-emerald-100 text-emerald-700 hover:bg-emerald-200"
                                : ""
                            }
                          >
                            {resource.statut}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {resource.patient_assigne || (
                            <span className="text-slate-400">-</span>
                          )}
                        </TableCell>
                        <TableCell className="text-sm text-slate-500">
                          {resource.derniere_maj}
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteResource(resource.nom_ressource)}
                            className="text-rose-600 hover:text-rose-700"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        );
      case "doctors":
        return (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold">Gestion des Médecins</h2>
              <Dialog>
                <DialogTrigger asChild>
                  <Button className="gap-2 bg-blue-900 hover:bg-blue-800">
                    <Plus className="w-4 h-4" />
                    Ajouter un Médecin
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Ajouter un nouveau médecin</DialogTitle>
                    <DialogDescription>
                      Entrez les informations du médecin.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label htmlFor="doctor-name">Nom</Label>
                      <Input
                        id="doctor-name"
                        placeholder="Ex: Dr. Jean Dupont"
                        value={newDoctorName}
                        onChange={(e) => setNewDoctorName(e.target.value)}
                        required
                        aria-invalid={!newDoctorName.trim()}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="doctor-specialty">Spécialité</Label>
                      <Select
                        value={newDoctorSpecialty}
                        onValueChange={setNewDoctorSpecialty}
                        aria-invalid={!newDoctorSpecialty}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Sélectionnez une spécialité" />
                        </SelectTrigger>
                        <SelectContent>
                          {specialties.map((specialty) => (
                            <SelectItem key={specialty} value={specialty}>
                              {specialty}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button onClick={handleAddDoctor} className="bg-blue-900 hover:bg-blue-800">Ajouter</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>

            <Card className="border-[var(--border)] bg-[var(--bg-surface)] p-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="filter-name">Filtrer par nom</Label>
                  <Input
                    id="filter-name"
                    placeholder="Rechercher par nom..."
                    value={filterDoctorName}
                    onChange={(e) => setFilterDoctorName(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="filter-specialty">Filtrer par spécialité</Label>
                  <Select
                    value={filterDoctorSpecialty}
                    onValueChange={setFilterDoctorSpecialty}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Toutes les spécialités" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Toutes les spécialités</SelectItem>
                      {specialties.map((specialty) => (
                        <SelectItem key={specialty} value={specialty}>
                          {specialty}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </Card>

            <Card className="border-[var(--border)] bg-[var(--bg-surface)]">
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>Nom</TableHead>
                      <TableHead>Spécialité</TableHead>
                      <TableHead>Disponible</TableHead>
                      <TableHead>Patient</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {doctors
                      .filter((doctor) => {
                        const matchesName = filterDoctorName === "" || doctor.nom.toLowerCase().includes(filterDoctorName.toLowerCase());
                        const matchesSpecialty = filterDoctorSpecialty === "all" || filterDoctorSpecialty === "" || doctor.specialite === filterDoctorSpecialty;
                        return matchesName && matchesSpecialty;
                      })
                      .map((doctor) => (
                        <TableRow key={doctor.doctor_id}>
                          <TableCell className="font-mono text-sm">
                            {doctor.doctor_id}
                          </TableCell>
                          <TableCell className="font-medium">{doctor.nom}</TableCell>
                          <TableCell>
                            <Badge variant="outline">{doctor.specialite}</Badge>
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleToggleDoctorAvailability(doctor)}
                            >
                              {doctor.disponible ? (
                                <CheckCircle className="w-5 h-5 text-emerald-500" />
                              ) : (
                                <XCircle className="w-5 h-5 text-rose-500" />
                              )}
                            </Button>
                          </TableCell>
                          <TableCell>
                            {doctor.patient_assigne || (
                              <span className="text-slate-400">-</span>
                            )}
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteDoctor(doctor.doctor_id)}
                              className="text-rose-600 hover:text-rose-700"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        );
      case "patients":
        const filteredPatients = patients.filter((p) => {
          const normalize = (str: string) => (str || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim();

          const search = normalize(filterPatientName);
          const name = normalize(p.nom || "");
          const id = (p.patient_id || "").toLowerCase();
          const matchesName = !search || name.includes(search) || id.includes(search);

          if (filterPatientStatus === "all") return matchesName;

          const pStatus = normalize(p.statut || "en attente");
          const fStatus = normalize(filterPatientStatus);

          // Correspondance exacte par défaut
          let matchesStatus = (pStatus === fStatus);

          if (!matchesStatus) {
            if (fStatus === "traite") {
              // Gère les variations "traité" / "traiter"
              matchesStatus = pStatus === "traite" || pStatus === "traiter";
            } else if (fStatus === "transfere") {
              // Gère les variations "transféré" / "transferer"
              matchesStatus = pStatus === "transfere" || pStatus === "transferer";
            } else {
              // Pour les autres statuts (ex: "en attente"), inclusion classique
              matchesStatus = pStatus.includes(fStatus);
            }
          }

          return matchesName && matchesStatus;
        });

        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold">Liste des Patients</h2>
              <div className="flex items-center gap-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <Input
                    placeholder="Filtrer par nom ou ID..."
                    value={filterPatientName}
                    onChange={(e) => setFilterPatientName(e.target.value)}
                    className="pl-9 w-64 bg-[var(--bg-surface)] border-[var(--border)]"
                  />
                </div>
                <select
                  value={filterPatientStatus}
                  onChange={(e) => setFilterPatientStatus(e.target.value)}
                  className="px-3 py-2 rounded-md border border-[var(--border)] bg-[var(--bg-surface)] text-sm focus:outline-none focus:ring-2 focus:ring-yellow-500"
                >
                  <option value="all">Tous les statuts</option>
                  <option value="traité">Traité</option>
                  <option value="transféré">Transféré</option>
                </select>
              </div>
            </div>

            <Card className="border-[var(--border)] bg-[var(--bg-surface)]">
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>Nom</TableHead>
                      <TableHead>Âge</TableHead>
                      <TableHead>Score</TableHead>
                      <TableHead>Action Finale</TableHead>
                      <TableHead>Statut</TableHead>
                      <TableHead>Médecin Assigné</TableHead>
                      <TableHead>Lit Assigné</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredPatients.map((patient, index) => {
                      const severityScore = normalizeSeverityScore(patient.score_gravité) ?? 0;
                      const patientStatut = (patient.statut || "").toLowerCase();
                      return (
                        <TableRow key={patient.patient_id || index}>
                          <TableCell className="font-mono text-xs">
                            {patient.patient_id?.slice(0, 8)}...
                          </TableCell>
                          <TableCell className="font-medium">{patient.nom}</TableCell>
                          <TableCell>{patient.age} ans</TableCell>
                          <TableCell>
                            <Badge
                              variant={
                                severityScore <= 25
                                  ? "default"
                                  : severityScore <= 50
                                    ? "secondary"
                                    : severityScore <= 75
                                      ? "destructive"
                                      : "outline"
                              }
                            >
                              {severityScore > 0 ? severityScore.toFixed(1) : "-"}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">
                              {patient.action_finale || "en_attente"}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant="secondary"
                              className={
                                patientStatut.includes("consultation") ? "bg-blue-100 text-blue-700" :
                                  patientStatut.includes("traité") ? "bg-emerald-100 text-emerald-700" :
                                    patientStatut.includes("transféré") ? "bg-purple-100 text-purple-700" :
                                      "bg-slate-100 text-slate-700"
                              }
                            >
                              {patient.statut || "en attente"}
                            </Badge>
                          </TableCell>
                          <TableCell>{patient.medecin_assigne || "-"}</TableCell>
                          <TableCell>{patient.lit_assigne || "-"}</TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex h-[100dvh] bg-[var(--bg-base)] text-[var(--text-main)] overflow-hidden">
      {/* Sidebar */}
      <div className="w-64 bg-[var(--sidebar-bg)] text-[var(--sidebar-txt)] flex flex-col border-r border-[var(--border-strong)] flex-shrink-0">
        <div
          className="p-6 flex items-center gap-3 border-b border-[var(--border-strong)]/30 cursor-pointer hover:opacity-80 transition-opacity"
          onClick={() => window.location.href = "/"}
        >
          <Shield className="w-6 h-6 text-yellow-500" />
          <span className="font-bold text-lg tracking-tight">TriageMed Admin</span>
        </div>

        <nav className="flex-1 px-4 space-y-1.5 mt-6">
          <SidebarItem
            icon={<LayoutDashboard className="w-4 h-4" />}
            label="Tableau de Bord"
            isActive={activeTab === "dashboard"}
            onClick={() => setActiveTab("dashboard")}
          />
          <SidebarItem
            icon={<Bed className="w-4 h-4" />}
            label="Ressources"
            isActive={activeTab === "resources"}
            onClick={() => setActiveTab("resources")}
          />
          <SidebarItem
            icon={<Stethoscope className="w-4 h-4" />}
            label="Médecins"
            isActive={activeTab === "doctors"}
            onClick={() => setActiveTab("doctors")}
          />
          <SidebarItem
            icon={<Users className="w-4 h-4" />}
            label="Patients"
            isActive={activeTab === "patients"}
            onClick={() => setActiveTab("patients")}
          />
        </nav>

        <div className="p-4 border-t border-[var(--border-strong)] opacity-90 space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-yellow-500/20 flex items-center justify-center text-yellow-500 shrink-0">
              <Shield className="w-5 h-5" />
            </div>
            <div className="overflow-hidden">
              <div className="text-xs text-[var(--sidebar-txt)]/50 font-medium">Administrateur</div>
              <div className="font-semibold text-sm truncate">Admin</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden relative">
        {/* Header */}
        <header className="h-16 bg-[var(--bg-surface)] border-b border-[var(--border)] flex items-center justify-between px-6 shrink-0">
          <h1 className="text-xl font-bold capitalize">{activeTab.replace("_", " ")}</h1>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={loadAllData}
              disabled={isLoading}
              className="gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
              Actualiser
            </Button>
            <Button variant="ghost" size="sm" onClick={handleLogout} className="text-[var(--text-dimmed)] hover:text-yellow-500">
              <LogOut className="w-4 h-4 mr-2" />
              Déconnexion
            </Button>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto p-6">
          {renderContent()}
        </main>
      </div>
    </div>
  );
}
