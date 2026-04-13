"""
core/sheets_db.py — Google Sheets comme base de données dynamique temps réel.
Le Sheet Resources est la SOURCE DE VÉRITÉ — l'agent lit et modifie en temps réel.
"""
from __future__ import annotations
import time
import logging
import uuid
from datetime import datetime
from typing import Any
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError

logger = logging.getLogger(__name__)

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = {
    "Patients":  ["patient_id","nom","age","genre","symptomes",
                  "score_gravité","action_finale","heure_arrivée","statut"],
    "Resources": ["nom_ressource","disponibilite","charge_%",
                  "patient_assigne","statut","derniere_maj"],
    "Decisions": ["decision_id","patient_id","score_gravite","action",
                  "raisonnement","nb_cycles","timestamp","agent_decideur"],
    "Logs":      ["timestamp","agent","action","details","patient_id","niveau"],
}


class SheetsDB:
    """
    Base de données Google Sheets temps réel.
    Sheet Resources = source de vérité pour les ressources hospitalières.
    """

    def __init__(self, credentials_path: str,
                 spreadsheet_name: str = "MAS_Resources"):
        self.credentials_path = credentials_path
        self.spreadsheet_name = spreadsheet_name
        self._client:      gspread.Client      | None = None
        self._spreadsheet: gspread.Spreadsheet | None = None
        self._sheets:      dict[str, gspread.Worksheet] = {}
        self._cache:       dict[str, Any] = {}
        self._cache_time:  float = 0.0
        self._cache_ttl:   float = 3.0  # 3s pour être plus réactif

    # ── Connexion ─────────────────────────────────────────────────────────────

    def connect(self) -> None:
        creds = Credentials.from_service_account_file(
            self.credentials_path, scopes=SCOPES)
        self._client      = gspread.authorize(creds)
        self._spreadsheet = self._client.open(self.spreadsheet_name)
        self._load_sheets()
        logger.info(f"SheetsDB connecté : {self.spreadsheet_name}")

    def _load_sheets(self) -> None:
        existing = {ws.title: ws for ws in self._spreadsheet.worksheets()}
        for name, headers in HEADERS.items():
            if name not in existing:
                ws = self._spreadsheet.add_worksheet(
                    title=name, rows=1000, cols=len(headers))
                ws.append_row(headers)
            else:
                ws = existing[name]
                if not ws.row_values(1):
                    ws.append_row(headers)
            self._sheets[name] = ws

    # ── Retry ─────────────────────────────────────────────────────────────────

    def _retry(self, func, *args, retries: int = 3, **kwargs) -> Any:
        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except APIError as e:
                if "429" in str(e):
                    wait = 2 ** attempt
                    logger.warning(f"Rate limit — attente {wait}s")
                    time.sleep(wait)
                elif attempt == retries - 1:
                    raise
                else:
                    time.sleep(1)

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _normalize_score(self, raw: Any) -> float:
        """
        Normalize score values from mixed Sheets locales/formats to 0..100.
        Handles comma decimals (e.g. '57,7'), '/100' suffixes, and malformed
        numeric coercions such as 577 (from 57,7 interpreted with comma removed).
        """
        if raw in (None, ""):
            return 0.0

        try:
            if isinstance(raw, str):
                txt = raw.strip().lower().replace("/100", "").replace("%", "")
                txt = txt.replace(",", ".")
                value = float(txt)
            else:
                value = float(raw)
        except (TypeError, ValueError):
            return 0.0

        # Heuristic for locale-mangled decimals, e.g. 577 -> 57.7.
        while value > 100 and value < 10000:
            value /= 10.0

        return max(0.0, min(100.0, round(value, 1)))

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET RESOURCES — Source de vérité
    # ══════════════════════════════════════════════════════════════════════════

    def get_resources_live(self) -> list[dict]:
        """
        Lit les ressources directement depuis Google Sheets (pas de cache).
        C'est la source de vérité — appelé avant chaque décision.
        """
        return self._retry(self._sheets["Resources"].get_all_records)

    def find_available_resource(self, resource_type: str) -> dict | None:
        """
        Cherche une ressource disponible par type (Lit, Cardio, Neuro, Trauma, General).
        Retourne la première ressource disponible ou None.
        """
        resources = self.get_resources_live()
        for r in resources:
            name  = str(r.get("nom_ressource", ""))
            avail = str(r.get("disponibilite", "")).lower()
            if resource_type.lower() in name.lower() and avail == "true":
                return r
        return None

    def allocate_resource(self, resource_name: str, patient_id: str,
                          patient_name: str = "") -> bool:
        """
        Alloue une ressource à un patient — la marque comme OCCUPÉE.
        Retourne True si allocation réussie, False si déjà occupée.
        """
        def _write():
            ws = self._sheets["Resources"]
            records = ws.get_all_records()
            for i, r in enumerate(records):
                if r.get("nom_ressource") == resource_name:
                    row_idx = i + 2  # +2 car ligne 1 = headers
                    # Vérifie disponibilité au moment de l'écriture (sécurité)
                    current = str(r.get("disponibilite", "")).lower()
                    if current != "true":
                        return False
                    # Marque comme occupé
                    ws.update(f"A{row_idx}:F{row_idx}", [[
                        resource_name,
                        "False",
                        "100",
                        patient_name or patient_id,
                        "occupé",
                        self._now(),
                    ]])
                    logger.info(f"Ressource allouée : {resource_name} → {patient_name}")
                    return True
            return False

        result = self._retry(_write)
        self._invalidate_cache()
        return result or False

    def release_resource(self, resource_name: str) -> None:
        """
        Libère une ressource — la remet DISPONIBLE.
        Appelé après la fin du triage d'un patient.
        """
        def _write():
            ws = self._sheets["Resources"]
            records = ws.get_all_records()
            for i, r in enumerate(records):
                if r.get("nom_ressource") == resource_name:
                    row_idx = i + 2
                    ws.update(f"A{row_idx}:F{row_idx}", [[
                        resource_name,
                        "True",
                        "0",
                        "",
                        "disponible",
                        self._now(),
                    ]])
                    logger.info(f"Ressource libérée : {resource_name}")
                    return

        self._retry(_write)
        self._invalidate_cache()

    def get_availability_summary(self) -> dict:
        """
        Résumé de disponibilité par type — lu depuis le Sheet.
        Utilisé par ResourceAgent pour informer MetaAgent.
        """
        resources = self.get_resources_live()
        summary   = {
            "lits":    {"total": 0, "disponibles": 0, "occupes": 0},
            "cardio":  {"total": 0, "disponibles": 0, "occupes": 0},
            "neuro":   {"total": 0, "disponibles": 0, "occupes": 0},
            "trauma":  {"total": 0, "disponibles": 0, "occupes": 0},
            "general": {"total": 0, "disponibles": 0, "occupes": 0},
        }

        for r in resources:
            name  = str(r.get("nom_ressource", "")).lower()
            avail = str(r.get("disponibilite", "")).lower() == "true"

            for key in summary:
                if key in name or (key == "lits" and "lit" in name):
                    summary[key]["total"] += 1
                    if avail:
                        summary[key]["disponibles"] += 1
                    else:
                        summary[key]["occupes"] += 1
                    break

        return summary

    def update_resource_status(self, data: dict) -> None:
        """Mise à jour générique d'une ressource."""
        name = data.get("resource", "Unknown")
        def _write():
            ws = self._sheets["Resources"]
            records = ws.get_all_records()
            for i, r in enumerate(records):
                if r.get("nom_ressource") == name:
                    row_idx = i + 2
                    ws.update(f"A{row_idx}:F{row_idx}", [[
                        name,
                        str(data.get("availability", True)),
                        str(data.get("load", 0)),
                        data.get("patient", ""),
                        data.get("status", "disponible"),
                        self._now(),
                    ]])
                    return
            # Si pas trouvé, ajoute
            ws.append_row([
                name,
                str(data.get("availability", True)),
                str(data.get("load", 0)),
                data.get("patient", ""),
                data.get("status", "disponible"),
                self._now(),
            ])
        self._retry(_write)
        self._invalidate_cache()

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET PATIENTS
    # ══════════════════════════════════════════════════════════════════════════

    def upsert_patient(self, patient_data: dict) -> None:
        pid = patient_data.get("id", "")
        def _write():
            ws = self._sheets["Patients"]
            records = ws.get_all_records()
            for i, r in enumerate(records):
                if r.get("patient_id") == pid:
                    existing_score = r.get("score_gravite") or r.get("score_gravité") or ""
                    existing_action = (
                        r.get("action_finale")
                        or r.get("action")
                        or ""
                    )
                    score = self._normalize_score(
                        patient_data.get("severity_score", existing_score)
                    )
                    action = patient_data.get("action", existing_action)
                    row = [
                        pid,
                        patient_data.get("name", r.get("nom", "")),
                        patient_data.get("age", r.get("age", "")),
                        patient_data.get("gender", r.get("genre", "")),
                        ", ".join(patient_data.get("symptoms", [])) or r.get("symptomes", ""),
                        score,
                        action,
                        patient_data.get("arrival_time", r.get("heure_arrivée", self._now())),
                        patient_data.get("status", r.get("statut", "en_attente")),
                    ]
                    ws.update(f"A{i+2}:I{i+2}", [row])
                    return
            row = [
                pid,
                patient_data.get("name", ""),
                patient_data.get("age", ""),
                patient_data.get("gender", ""),
                ", ".join(patient_data.get("symptoms", [])),
                self._normalize_score(patient_data.get("severity_score", "")),
                patient_data.get("action", ""),
                patient_data.get("arrival_time", self._now()),
                patient_data.get("status", "en_attente"),
            ]
            ws.append_row(row)
        self._retry(_write)
        self._invalidate_cache()

    def update_patient_decision(self, patient_id: str,
                                 action: str, score: float | None,
                                 status: str = "décidé") -> None:
        def _write():
            ws      = self._sheets["Patients"]
            # Récupère les en-têtes pour trouver les colonnes dynamiquement
            headers = [h.lower() for h in ws.row_values(1)]
            
            def get_col_letter(name):
                try:
                    idx = -1
                    for i, h in enumerate(headers):
                        if name in h: # Gère 'score_gravité' ou 'score_gravite'
                            idx = i + 1
                            break
                    if idx == -1: return None
                    return chr(64 + idx)
                except: return None

            col_score = get_col_letter("score") or "F"
            col_action = get_col_letter("action") or "G"
            col_status = get_col_letter("statut") or "I"

            records = ws.get_all_records()
            for i, r in enumerate(records):
                if r.get("patient_id") == patient_id:
                    row_idx = i + 2
                    if score is not None:
                        ws.update(f"{col_score}{row_idx}", [[self._normalize_score(score)]])
                    ws.update(f"{col_action}{row_idx}", [[action]])
                    ws.update(f"{col_status}{row_idx}", [[status]])
                    return
        self._retry(_write)
        self._invalidate_cache()

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET DECISIONS
    # ══════════════════════════════════════════════════════════════════════════

    def insert_decision(self, decision_data: dict) -> None:
        row = [
            str(uuid.uuid4())[:8],
            decision_data.get("patient_id", ""),
            self._normalize_score(decision_data.get("severity_score", 0)),
            decision_data.get("action", ""),
            decision_data.get("rationale", ""),
            decision_data.get("cycle_count", 1),
            decision_data.get("timestamp", self._now()),
            decision_data.get("decided_by", "MetaAgent"),
        ]
        self._retry(self._sheets["Decisions"].append_row, row)

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET LOGS
    # ══════════════════════════════════════════════════════════════════════════

    def log(self, agent: str, action: str, details: str = "",
            patient_id: str = "", niveau: str = "INFO") -> None:
        row = [self._now(), agent, action, details, patient_id, niveau]
        self._retry(self._sheets["Logs"].append_row, row)

    # ══════════════════════════════════════════════════════════════════════════
    # LECTURE avec cache
    # ══════════════════════════════════════════════════════════════════════════

    def get_patients(self)   -> list[dict]:
        def _fetch():
            rows = self._sheets["Patients"].get_all_records()
            for r in rows:
                for k in list(r.keys()):
                    key_l = str(k).lower()
                    if "score_gravit" in key_l or "severity_score" in key_l:
                        r[k] = self._normalize_score(r.get(k))
            return rows
        return self._cached("patients", _fetch)

    def get_resources(self)  -> list[dict]:
        return self._cached("resources",
                            lambda: self._sheets["Resources"].get_all_records())

    def get_decisions(self)  -> list[dict]:
        def _fetch():
            rows = self._sheets["Decisions"].get_all_records()
            for r in rows:
                for k in list(r.keys()):
                    key_l = str(k).lower()
                    if "score_gravit" in key_l or "severity_score" in key_l:
                        r[k] = self._normalize_score(r.get(k))
            return rows
        return self._cached("decisions", _fetch)

    def get_logs(self, limit: int = 100) -> list[dict]:
        return self._sheets["Logs"].get_all_records()[-limit:]

    def get_metrics(self) -> dict:
        patients  = self.get_patients()
        resources = self.get_resources()
        decisions = self.get_decisions()
        available = sum(1 for r in resources
                        if str(r.get("disponibilite","")).lower() == "true")
        occupied  = sum(1 for r in resources
                        if str(r.get("disponibilite","")).lower() == "false")
        def _safe_float(p):
            val = p.get("score_gravite") or p.get("score_gravité") or 0
            try:
                if isinstance(val, str):
                    val = val.replace(',', '.')
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        critical  = sum(1 for p in patients if _safe_float(p) >= 70)
        return {
            "total_patients":    len(patients),
            "total_decisions":   len(decisions),
            "total_resources":   len(resources),
            "available_resources": available,
            "occupied_resources":  occupied,
            "critical_patients":   critical,
        }

    def _cached(self, key: str, fetch_fn) -> list[dict]:
        now = time.time()
        if key in self._cache and (now - self._cache_time) < self._cache_ttl:
            return self._cache[key]
        result = fetch_fn()
        self._cache[key] = result
        self._cache_time = now
        return result

    def _invalidate_cache(self) -> None:
        self._cache.clear()
        self._cache_time = 0.0
