/**
 * api.ts — Flask API client pour système de triage médical MAS
 * All calls go to VITE_API_BASE_URL (defaults to http://localhost:5000)
 */

const DEFAULT_API_PORT = 5000;

export const API_BASE =
  import.meta.env.VITE_API_BASE_URL ??
  (typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:${DEFAULT_API_PORT}`
    : "http://localhost:5000");

async function request<T>(
  method: "GET" | "POST" | "PUT" | "DELETE",
  path: string,
  body?: unknown
): Promise<T> {
  try {
    const headers: Record<string, string> = {};
    if (body !== undefined) {
      headers["Content-Type"] = "application/json";
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
      const errorMessage = (data as { message?: string }).message ?? `HTTP ${res.status}`;
      console.error(`API Error: ${errorMessage}`, { status: res.status, data });
      throw new Error(errorMessage);
    }
    
    return data as T;
  } catch (error) {
    console.error(`Request failed: ${method} ${path}`, error);
    throw error;
  }
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface SymptomsDecision {
  action: string;
  urgency: string;
  label: string;
  color: string;
  instructions: string;
}

export interface SymptomsResponse {
  status: string;
  patient_id: string;
  severity_score: number;
  decision: SymptomsDecision;
  explanation: Array<{ symptom: string; impact: number; present: boolean }>;
  symptoms_found: string[];
  symptoms_unknown: string[];
}

export interface Patient {
  patient_id?: string;
  id?: string;
  name?: string;
  nom?: string;
  age?: number;
  gender?: string;
  genre?: string;
  symptoms?: string;
  symptomes?: string;
  pain_level?: number;
  douleur?: number;
  severity_score?: number | string;
  score_gravite?: number | string;
  "score_gravité"?: number | string;
  action?: string;
  action_finale?: string;
  status?: string;
  statut?: string;
  arrival_time?: string;
  // Affectation médecin
  medecin_assigne?: string;
  specialite_assignee?: string;
  mode_affectation?: string;
  lit_assigne?: string;
}

export interface Resource {
  nom_ressource: string;
  type: string;
  statut: string;
  service?: string;
  patient_id?: string;
}

export interface Decision {
  patient_id: string;
  severity_score: number;
  score_gravite?: number;
  action: string;
  rationale: string;
  timestamp?: string;
  decided_by?: string;
}

export interface LogEntry {
  agent?: string;
  action?: string;
  details?: string;
  patient_id?: string;
  niveau?: string;
  timestamp?: string;
}

export interface Metrics {
  total_patients?: number;
  total_decisions?: number;
  available_resources?: number;
  critical_patients?: number;
}

// ── Endpoints ──────────────────────────────────────────────────────────────

/** POST /symptoms — Triage par les agents MAS */
export function postSymptoms(payload: {
  name: string;
  age: number;
  gender: string;
  symptoms: string[];
  symptoms_details?: string;  // JSON string with intensity/duration
  pain_level: number;
  conscious: boolean;
}) {
  return request<SymptomsResponse>("POST", "/symptoms", payload);
}

/** POST /decision — doctor validation */
export function postDecision(payload: {
  patient_id: string;
  action: string;
  score?: number;
  validated_by?: string;
}) {
  return request<{ status: string; patient_id: string }>("POST", "/decision", payload);
}

/** GET /patients */
export function getPatients() {
  return request<{ status: string; data: Patient[]; count: number }>("GET", "/patients");
}

/** GET /resources */
export function getResources() {
  return request<{ status: string; data: Resource[]; count: number }>("GET", "/resources");
}

/** GET /decisions */
export function getDecisions() {
  return request<{ status: string; data: Decision[]; count: number }>("GET", "/decisions");
}

/** GET /logs */
export function getLogs(limit = 50) {
  return request<{ status: string; data: LogEntry[]; count: number }>(
    "GET",
    `/logs?limit=${limit}`
  );
}

/** GET /metrics */
export function getMetrics() {
  return request<{ status: string; data: Metrics }>("GET", "/metrics");
}

/** GET /health */
export function getHealth() {
  return request<{
    status: string;
    api: string;
    sheets: boolean;
  }>("GET", "/health");
}

// ═══════════════════════════════════════════════════════════════════════════════
// Admin Endpoints (Espace Agent Administratif)
// ═══════════════════════════════════════════════════════════════════════════════

/** GET /admin/dashboard */
export function getAdminDashboard() {
  return request<{
    patients_today: number;
    severity_distribution: { léger: number; modéré: number; urgent: number; critique: number };
    bed_occupancy_rate: number;
    available_beds: number;
    total_beds: number;
    doctors_available_by_specialty: Record<string, number>;
    total_doctors: number;
    transfers: number;
    hospitalization_rate: number;
    critical_detected: number;
    doctor_load: Array<{ name: string; specialty: string; available: boolean; patient_count: number }>;
    daily_stats: Record<string, { total: number; critical: number; hospitalized: number }>;
    hourly_stats: Record<string, { total: number; critical: number; hospitalized: number }>;
    timestamp: string;
  }>("GET", "/admin/dashboard");
}

/** GET /admin/resources */
export function getAdminResources() {
  return request<Resource[]>("GET", "/admin/resources");
}

/** POST /admin/resources */
export function createAdminResource(data: { nom_ressource: string; type?: string }) {
  return request<{ success: boolean; message: string }>("POST", "/admin/resources", data);
}

/** PUT /admin/resources */
export function updateAdminResource(data: { nom_ressource: string; statut: string; patient_assigne?: string }) {
  return request<{ success: boolean; message: string }>("PUT", "/admin/resources", data);
}

/** DELETE /admin/resources/<nom_ressource> */
export function deleteAdminResource(nom_ressource: string) {
  // URL encode and trim the resource name to handle special characters and whitespace
  const encoded = encodeURIComponent(nom_ressource.trim());
  return request<{ success: boolean; message: string }>("DELETE", `/admin/resources/${encoded}`);
}

/** GET /admin/doctors */
export function getAdminDoctors() {
  return request<Array<{
    doctor_id: string;
    nom: string;
    specialite: string;
    disponible: string;
    patient_assigne?: string;
    derniere_maj?: string;
  }>>("GET", "/admin/doctors");
}

/** POST /admin/doctors */
export function createAdminDoctor(data: { doctor_id?: string; nom: string; specialite: string }) {
  return request<{ success: boolean; doctor_id: string }>("POST", "/admin/doctors", data);
}

/** PUT /admin/doctors */
export function updateAdminDoctor(data: { doctor_id: string; nom?: string; specialite?: string; disponible?: boolean }) {
  return request<{ success: boolean; message: string }>("PUT", "/admin/doctors", data);
}

/** DELETE /admin/doctors/<doctor_id> */
export function deleteAdminDoctor(doctor_id: string) {
  const encoded = encodeURIComponent(doctor_id.trim());
  return request<{ success: boolean; message: string }>("DELETE", `/admin/doctors/${encoded}`);
}

/** GET /admin/patients */
export function getAdminPatients() {
  return request<Patient[]>("GET", "/admin/patients");
}

/** GET /admin/decisions */
export function getAdminDecisions() {
  return request<Decision[]>("GET", "/admin/decisions");
}

/** GET /admin/logs */
export function getAdminLogs() {
  return request<Array<{
    timestamp: string;
    agent: string;
    action: string;
    details: string;
    patient_id?: string;
    niveau: string;
  }>>("GET", "/admin/logs");
}

// ═══════════════════════════════════════════════════════════════════════════════
// AUTHENTICATION API
// ═══════════════════════════════════════════════════════════════════════════════

export interface LoginResponse {
  success: boolean;
  token: string;
  user: {
    user_id: string;
    username: string;
    role: string;
  };
}

export interface User {
  user_id: string;
  username: string;
  role: string;
  created_at?: string;
  active?: string;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || "Échec de la connexion");
  }
  const data = await res.json();
  // Store token
  sessionStorage.setItem("triage_token", data.token);
  return data;
}

export async function registerUser(
  username: string, 
  password: string, 
  role: string,
  token: string
): Promise<{ success: boolean; message: string; user: User }> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify({ username, password, role }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || "Échec de l'inscription");
  }
  return res.json();
}

export async function getCurrentUser(token: string): Promise<{ user: User }> {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: { "Authorization": `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Échec de la récupération de l'utilisateur actuel");
  return res.json();
}

export async function listUsers(token: string): Promise<{ users: User[] }> {
  const res = await fetch(`${API_BASE}/auth/users`, {
    headers: { "Authorization": `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Échec de la liste des utilisateurs");
  return res.json();
}

export function logout(): void {
  sessionStorage.removeItem("triage_token");
  sessionStorage.removeItem("triage_role");
  sessionStorage.removeItem("triage_username");
}

export function getStoredToken(): string | null {
  return sessionStorage.getItem("triage_token");
}
