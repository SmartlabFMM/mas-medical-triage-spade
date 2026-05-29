/**
 * doctorApi.ts — API client pour les endpoints médecins avec JWT
 * Requires authentication token from localStorage
 */

const DEFAULT_API_PORT = 5000;

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ??
  (typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:${DEFAULT_API_PORT}`
    : "http://localhost:5000");

/**
 * Get JWT token from sessionStorage
 */
function getToken(): string | null {
  return sessionStorage.getItem("triage_token") || localStorage.getItem("token") || localStorage.getItem("jwt_token") || null;
}

/**
 * Make authenticated request to doctor endpoints
 */
async function authRequest<T>(
  method: "GET" | "POST" | "PUT" | "DELETE",
  path: string,
  body?: unknown
): Promise<T> {
  const token = getToken();
  
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  const data = await res.json().catch(() => {
    console.error(`Failed to parse JSON response from ${method} ${path}`);
    return {};
  });

  if (!res.ok) {
    const errorMessage = (data as { error?: string; message?: string }).error ?? 
                        (data as { message?: string }).message ?? 
                        `HTTP ${res.status}`;
    console.error(`API Error: ${errorMessage}`, { status: res.status, data });
    throw new Error(errorMessage);
  }

  return data as T;
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface DoctorPatient {
  patient_id: string;
  name?: string;
  nom?: string;
  age: number | string;
  symptoms?: string;
  symptomes?: string;
  severity_score?: number | string;
  score_gravite?: number | string;
  score_gravité?: number | string;
  normalized_score: number;
  arrival_time?: string;
  statut?: string;
  status?: string;
  medecin_assigne?: string;
  [key: string]: unknown;
}

export interface DoctorPatientsResponse {
  success: boolean;
  doctor_username: string;
  total_patients: number;
  severity_counts: {
    critical: number;
    urgent: number;
    moderate: number;
    low: number;
  };
  patients: DoctorPatient[];
}

export interface DoctorStatsResponse {
  success: boolean;
  doctor_username: string;
  total_patients: number;
  severity_distribution: {
    critical: number;
    urgent: number;
    moderate: number;
    low: number;
  };
  status_distribution: Record<string, number>;
}

export interface UpdateStatusResponse {
  success: boolean;
  message: string;
  patient_id: string;
  new_status: string;
}

// ── Doctor API Functions ──────────────────────────────────────────────────

/** GET /api/doctor/patients — Get patients assigned to authenticated doctor */
export function getDoctorPatients() {
  return authRequest<DoctorPatientsResponse>("GET", "/api/doctor/patients");
}

/** GET /api/doctor/stats — Get statistics for doctor's patients */
export function getDoctorStats() {
  return authRequest<DoctorStatsResponse>("GET", "/api/doctor/stats");
}

/** POST /api/doctor/patient/<patient_id>/status — Update patient status */
export function updatePatientStatus(patientId: string, status: string) {
  return authRequest<UpdateStatusResponse>(
    "POST", 
    `/api/doctor/patient/${patientId}/status`,
    { status }
  );
}

export interface ArchivedPatient {
  patient_id: string;
  nom?: string;
  name?: string;
  age?: number | string;
  symptomes?: string;
  symptoms?: string;
  score_gravité?: number | string;
  normalized_score: number;
  statut?: string;
  action_finale?: string;
  medecin_assigne?: string;
  heure_arrivée?: string;
  archived_at?: string;
  archived_reason?: string;
  [key: string]: unknown;
}

export interface DoctorHistoryResponse {
  success: boolean;
  doctor_username: string;
  total: number;
  history: ArchivedPatient[];
}

/** GET /api/doctor/history — Get archived patients for the authenticated doctor */
export function getDoctorHistory() {
  return authRequest<DoctorHistoryResponse>("GET", "/api/doctor/history");
}

// ── Severity Helpers ─────────────────────────────────────────────────────

export function getSeverityFromScore(score: number): {
  label: string;
  color: string;
  bgColor: string;
} {
  if (score >= 80) {
    return {
      label: "Critique",
      color: "text-red-600",
      bgColor: "bg-red-100 border-red-300",
    };
  }
  if (score >= 60) {
    return {
      label: "Urgent",
      color: "text-orange-600",
      bgColor: "bg-orange-100 border-orange-300",
    };
  }
  if (score >= 40) {
    return {
      label: "Modéré",
      color: "text-yellow-600",
      bgColor: "bg-yellow-100 border-yellow-300",
    };
  }
  return {
    label: "Faible",
    color: "text-green-600",
    bgColor: "bg-green-100 border-green-300",
  };
}

export function getStatusColor(status: string): string {
  const normalized = status?.toLowerCase() || "";
  
  if (normalized.includes("traité") || normalized.includes("traite") || normalized.includes("done")) {
    return "bg-green-500";
  }
  if (normalized.includes("consultation") || normalized.includes("consult")) {
    return "bg-blue-500";
  }
  if (normalized.includes("transfér") || normalized.includes("transfer")) {
    return "bg-purple-500";
  }
  if (normalized.includes("attente") || normalized.includes("waiting")) {
    return "bg-yellow-500";
  }
  return "bg-gray-500";
}
