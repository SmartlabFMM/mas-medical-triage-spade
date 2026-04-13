/**
 * api.ts — Flask API client for TriageMed AI
 * All calls go to VITE_API_BASE_URL (defaults to http://localhost:5000)
 */

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5000";

async function request<T>(
  method: "GET" | "POST" | "DELETE",
  path: string,
  body?: unknown
): Promise<T> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: { "Content-Type": "application/json" },
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

export interface ExtractedData {
  symptoms: string[];
  pain_level: number;
  urgency: "low" | "medium" | "high" | "critical";
  is_conscious: boolean;
  notes: string;
  confidence: number;
}

export interface ChatResponse {
  status: string;
  session_id: string;
  reply: string;
  extracted_data: ExtractedData;
  is_complete: boolean;
  next_question: string;
}

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
  model_confidence: string;
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
  severity_score?: number;
  score_gravite?: number;
  "score_gravité"?: number;
  action?: string;
  status?: string;
  statut?: string;
  arrival_time?: string;
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

/** POST /chat — LLM triage dialogue */
export function postChat(message: string, sessionId?: string) {
  return request<ChatResponse>("POST", "/chat", {
    message,
    session_id: sessionId,
  });
}

/** POST /symptoms — ML triage (structured form) */
export function postSymptoms(payload: {
  name: string;
  age: number;
  gender: string;
  symptoms: string[];
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
    ml: boolean;
    llm: boolean;
    sheets: boolean;
  }>("GET", "/health");
}
