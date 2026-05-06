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
    "Patients":  ["patient_id","nom","age","genre","symptomes","symptoms_details",
                  "score_gravité","action_finale","heure_arrivée","statut",
                  "specialite_assignee","medecin_assigne","lit_assigne","mode_affectation"],
    "Resources": ["nom_ressource","disponibilite","charge_%",
                  "patient_assigne","statut","derniere_maj"],
    "Decisions": ["decision_id","patient_id","score_gravite","action",
                  "raisonnement","nb_cycles","timestamp","agent_decideur"],
    "Logs":      ["timestamp","agent","action","details","patient_id","niveau"],
    "Doctors":   ["doctor_id","nom","specialite","disponible","patient_assigne","derniere_maj"],
    "ArchivedPatients": ["patient_id","nom","age","genre","symptomes","symptoms_details",
                         "score_gravité","action_finale","heure_arrivée","statut",
                         "specialite_assignee","medecin_assigne","lit_assigne","mode_affectation",
                         "archived_at","archived_reason"],
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

    def _retry(self, func, *args, retries: int = 5, **kwargs) -> Any:
        """Exécute une fonction avec retry en cas de quota atteint (429)."""
        last_exception = None
        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except APIError as e:
                last_exception = e
                if "429" in str(e):
                    wait = (2 ** attempt) + 1
                    logger.warning(f"Quota atteint (429) — Tentative {attempt+1}/{retries} — Attente {wait}s")
                    time.sleep(wait)
                elif attempt == retries - 1:
                    raise
                else:
                    time.sleep(1)
        
        # Si on sort de la boucle sans avoir retourné, on lève la dernière exception
        if last_exception:
            raise last_exception
        return None

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _get_headers(self, sheet_name: str) -> list:
        """Retourne les en-têtes d'une feuille Google Sheets."""
        try:
            return self._sheets[sheet_name].row_values(1)
        except Exception:
            return HEADERS.get(sheet_name, [])

    def _find_col_index(self, sheet_name: str, field_name: str) -> int | None:
        headers = [h.lower() for h in self._get_headers(sheet_name)]
        field_name = field_name.lower()
        for idx, header in enumerate(headers, start=1):
            if header == field_name:
                return idx
        return None

    def _find_row_index(self, sheet_name: str, key: str, value: Any) -> int | None:
        ws = self._sheets[sheet_name]
        records = ws.get_all_records(expected_headers=HEADERS[sheet_name])
        for i, record in enumerate(records, start=2):
            if str(record.get(key, "")).strip() == str(value).strip():
                return i
        return None

    def update_patient_fields(self, patient_id: str, updates: dict[str, Any]) -> bool:
        """Met à jour des champs arbitraires pour un patient existant."""
        row_idx = self._find_row_index("Patients", "patient_id", patient_id)
        if row_idx is None:
            return False

        ws = self._sheets["Patients"]
        success = False
        for field_name, value in updates.items():
            col_idx = self._find_col_index("Patients", field_name)
            if col_idx is None:
                continue
            ws.update_cell(row_idx, col_idx, value)
            success = True

        if success:
            self._invalidate_cache()
        return success

    def archive_patient(self, patient_id: str, reason: str | None = None) -> bool:
        """Déplace un patient traité ou transféré dans la feuille d'archive.
        Vérifie d'abord si le patient est déjà archivé pour éviter les doublons.
        """
        # ── Guard: skip if already archived ──────────────────────────────
        try:
            existing = self._sheets["ArchivedPatients"].get_all_records()
            for rec in existing:
                if str(rec.get("patient_id", "")).strip() == str(patient_id).strip():
                    logger.info(f"[archive_patient] Patient {patient_id} déjà archivé — doublon ignoré")
                    # Still make sure the patient is removed from active sheet
                    active = self._sheets["Patients"].get_all_records(expected_headers=HEADERS["Patients"])
                    for j, r in enumerate(active, start=2):
                        if str(r.get("patient_id", "")).strip() == str(patient_id).strip():
                            self._sheets["Patients"].delete_rows(j)
                            self._invalidate_cache()
                            break
                    return True
        except Exception as e:
            logger.warning(f"[archive_patient] Impossible de vérifier les doublons: {e}")

        # ── Read patient from active sheet ────────────────────────────────
        patients = self._sheets["Patients"].get_all_records(expected_headers=HEADERS["Patients"])
        row_idx = None
        patient_row = None
        for i, record in enumerate(patients, start=2):
            if str(record.get("patient_id", "")).strip() == str(patient_id).strip():
                row_idx = i
                patient_row = record
                break

        if row_idx is None or patient_row is None:
            return False

        archive_headers = HEADERS["ArchivedPatients"]
        archived_values = [patient_row.get(header, "") for header in archive_headers[:-2]]
        archived_values.append(self._now())
        archived_values.append(reason or "")
        self._sheets["ArchivedPatients"].append_row(archived_values)
        self._sheets["Patients"].delete_rows(row_idx)
        self._invalidate_cache()
        return True

    def find_doctor_by_name(self, doctor_name: str) -> dict | None:
        doctors = self._sheets["Doctors"].get_all_records(expected_headers=HEADERS["Doctors"])
        for doc in doctors:
            if str(doc.get("nom", "")).strip().lower() == str(doctor_name).strip().lower():
                return doc
        return None

    def find_doctor_by_patient(self, patient_id: str) -> dict | None:
        doctors = self._sheets["Doctors"].get_all_records(expected_headers=HEADERS["Doctors"])
        target = str(patient_id).strip()
        for doc in doctors:
            assignments = [p.strip() for p in str(doc.get("patient_assigne", "")).split(",") if p.strip()]
            if target in assignments:
                return doc
        return None

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
        res = self._retry(self._sheets["Resources"].get_all_records)
        return res if res is not None else []

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

        if not resources:
            return summary

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
                        patient_data.get("symptoms_details", r.get("symptoms_details", "")),  # colonne 6
                        score,  # colonne 7
                        action,  # colonne 8
                        patient_data.get("arrival_time", r.get("heure_arrivée", self._now())),  # colonne 9
                        patient_data.get("status", r.get("statut", "en_attente")),  # colonne 10
                        r.get("specialite_assignee", ""),  # colonne 11
                        r.get("medecin_assigne", ""),  # colonne 12
                        r.get("lit_assigne", ""),  # colonne 13
                        r.get("mode_affectation", ""),  # colonne 14
                    ]
                    ws.update(f"A{i+2}:N{i+2}", [row])
                    return
            patient_name = patient_data.get("name") or f"Patient-{pid[:8]}"
            print(f"[DB DEBUG] patient_data.name: {patient_data.get('name')}, patient_name: {patient_name}")
            row = [
                pid,
                patient_name,
                patient_data.get("age", ""),
                patient_data.get("gender", ""),
                ", ".join(patient_data.get("symptoms", [])),
                patient_data.get("symptoms_details", ""),  # symptoms_details (colonne 6)
                self._normalize_score(patient_data.get("severity_score", "")),  # score_gravité (colonne 7)
                patient_data.get("action", ""),  # action_finale (colonne 8)
                patient_data.get("arrival_time", self._now()),  # heure_arrivée (colonne 9)
                patient_data.get("status", "en_attente"),  # statut (colonne 10)
                "",  # specialite_assignee (colonne 11)
                "",  # medecin_assigne (colonne 12)
                "",  # lit_assigne (colonne 13)
                "",  # mode_affectation (colonne 14)
            ]
            ws.append_row(row)
        self._retry(_write)
        self._invalidate_cache()

    def update_patient_decision(self, patient_id: str,
                                 action: str, score: float | None,
                                 status: str = "trié") -> None:
        def _write():
            ws      = self._sheets["Patients"]
            headers = [h.lower() for h in ws.row_values(1)]
            
            def get_col_idx(name):
                try:
                    for i, h in enumerate(headers):
                        if name in h: return i + 1
                    return None
                except: return None

            idx_score  = get_col_idx("score") or 7
            idx_action = get_col_idx("action") or 8
            idx_status = get_col_idx("statut") or 10

            records = ws.get_all_records()
            for i, r in enumerate(records):
                if r.get("patient_id") == patient_id:
                    row_idx = i + 2
                    
                    # On prépare les mises à jour
                    updates = []
                    if score is not None:
                        updates.append({'range': f"{chr(64+idx_score)}{row_idx}", 'values': [[self._normalize_score(score)]]})
                    updates.append({'range': f"{chr(64+idx_action)}{row_idx}", 'values': [[action]]})
                    updates.append({'range': f"{chr(64+idx_status)}{row_idx}", 'values': [[status]]})
                    
                    # Batch update pour économiser le quota et assurer l'atomicité
                    ws.batch_update(updates)
                    return
        self._retry(_write)
        self._invalidate_cache()

    def update_patient_bed(self, patient_id: str, bed_name: str) -> None:
        """Update the assigned bed for a patient."""
        def _write():
            ws = self._sheets["Patients"]
            headers = [h.lower() for h in ws.row_values(1)]

            def get_col_letter(name):
                try:
                    idx = -1
                    for i, h in enumerate(headers):
                        if name in h:
                            idx = i + 1
                            break
                    if idx == -1:
                        return None
                    return chr(64 + idx)
                except:
                    return None

            col_bed = get_col_letter("lit_assigne") or get_col_letter("bed_assigned") or "L"

            records = ws.get_all_records()
            for i, r in enumerate(records):
                if r.get("patient_id") == patient_id:
                    row_idx = i + 2
                    ws.update(f"{col_bed}{row_idx}", [[bed_name]])
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

    def get_patients(self) -> list[dict]:
        def _fetch():
            rows = self._sheets["Patients"].get_all_records(expected_headers=HEADERS["Patients"])
            for r in rows:
                for k in list(r.keys()):
                    key_l = str(k).lower()
                    if "score_gravit" in key_l or "severity_score" in key_l:
                        r[k] = self._normalize_score(r.get(k))
            return rows
        return self._cached("patients", lambda: self._retry(_fetch))

    def get_archived_patients(self) -> list[dict]:
        def _fetch():
            rows = self._sheets["ArchivedPatients"].get_all_records(expected_headers=HEADERS["ArchivedPatients"])
            for r in rows:
                for k in list(r.keys()):
                    key_l = str(k).lower()
                    if "score_gravit" in key_l or "severity_score" in key_l:
                        r[k] = self._normalize_score(r.get(k))
            return rows
        return self._cached("archived_patients", lambda: self._retry(_fetch))

    def get_resources(self)  -> list[dict]:
        return self._cached("resources",
                            lambda: self._sheets["Resources"].get_all_records())

    def get_decisions(self) -> list[dict]:
        def _fetch():
            rows = self._sheets["Decisions"].get_all_records()
            for r in rows:
                for k in list(r.keys()):
                    key_l = str(k).lower()
                    if "score_gravit" in key_l or "severity_score" in key_l:
                        r[k] = self._normalize_score(r.get(k))
            return rows
        return self._cached("decisions", lambda: self._retry(_fetch))

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

    # ─────────────────────────────────────────────────────────────────────────
    # GESTION DES MÉDECINS ET ASSIGNATION
    # ─────────────────────────────────────────────────────────────────────────

    def get_doctors_status_summary(self) -> dict:
        """Résumé de l'état des médecins."""
        doctors = self.get_doctors()
        available = 0
        occupied = 0
        by_specialty = {}
        
        for doc in doctors:
            spec = doc.get("specialite", "Inconnue")
            is_avail = str(doc.get("disponible", "")).lower() == "true"
            
            if spec not in by_specialty:
                by_specialty[spec] = {"available": 0, "occupied": 0}
            
            if is_avail:
                available += 1
                by_specialty[spec]["available"] += 1
            else:
                occupied += 1
                by_specialty[spec]["occupied"] += 1
                
        return {
            "total_doctors": len(doctors),
            "available": available,
            "occupied": occupied,
            "by_specialty": by_specialty
        }

    def get_doctors(self) -> list[dict]:
        """Récupère tous les médecins."""
        return self._sheets["Doctors"].get_all_records()

    def find_available_doctor(self, specialty: str) -> dict | None:
        """Trouve un médecin disponible par spécialité.

        Choisit le médecin avec le minimum de patients assignés parmi tous les médecins
        de la spécialité, peu importe leur statut de disponibilité.
        """
        doctors = self.get_doctors()
        specialty_normalized = specialty.lower().strip()
        print(f"[SheetsDB] Recherche médecin spécialité: '{specialty_normalized}'")

        candidates = []

        for doc in doctors:
            doc_specialty = doc.get("specialite", "").lower().strip()
            if doc_specialty != specialty_normalized:
                continue

            doc_available = str(doc.get("disponible", "")).lower()
            assignments = [p.strip() for p in str(doc.get("patient_assigne", "")).split(",") if p.strip()]
            print(f"[SheetsDB]   - {doc.get('nom')}: spécialité='{doc_specialty}', disponible='{doc_available}', assignés={len(assignments)}")

            candidates.append((len(assignments), doc))

        if candidates:
            best = min(candidates, key=lambda item: item[0])[1]
            print(f"[SheetsDB]   [OK] Médecin avec minimum de patients trouvé: {best.get('nom')} ({candidates[0][0]} patients)")
            return best

        print(f"[SheetsDB]   ✗ Aucun médecin trouvé pour '{specialty_normalized}'")
        return None

    def assign_doctor(self, doctor_id: str, patient_id: str) -> bool:
        """Assigne un patient à un médecin."""
        try:
            doctors = self._sheets["Doctors"].get_all_records(expected_headers=HEADERS["Doctors"])
            for i, doc in enumerate(doctors, start=2):
                if doc.get("doctor_id") == doctor_id:
                    current_assignments = str(doc.get("patient_assigne", "")).strip()
                    if current_assignments:
                        assignments = [p.strip() for p in current_assignments.split(",") if p.strip()]
                        if patient_id not in assignments:
                            assignments.append(patient_id)
                        new_patient_assigne = ",".join(assignments)
                    else:
                        new_patient_assigne = patient_id
                    self._sheets["Doctors"].update_cell(i, 5, new_patient_assigne)  # patient_assigne (colonne E)
                    self._sheets["Doctors"].update_cell(i, 6, self._now())  # derniere_maj (colonne F)
                    return True
            return False
        except Exception as e:
            logger.error(f"[SheetsDB] Erreur assign_doctor: {e}")
            return False

    def release_doctor(self, doctor_id: str, patient_id: str | None = None) -> bool:
        """Libère un médecin (patient terminé)."""
        try:
            doctors = self._sheets["Doctors"].get_all_records(expected_headers=HEADERS["Doctors"])
            for i, doc in enumerate(doctors, start=2):
                if doc.get("doctor_id") == doctor_id:
                    current_assignments = str(doc.get("patient_assigne", "")).strip()
                    if patient_id and current_assignments:
                        assignments = [p.strip() for p in current_assignments.split(",") if p.strip() and p.strip() != str(patient_id).strip()]
                        self._sheets["Doctors"].update_cell(i, 5, ",".join(assignments))
                        if not assignments:
                            self._sheets["Doctors"].update_cell(i, 4, "TRUE")  # disponible (colonne D)
                    else:
                        self._sheets["Doctors"].update_cell(i, 5, "")  # patient_assigne (colonne E)
                        self._sheets["Doctors"].update_cell(i, 4, "TRUE")  # disponible (colonne D)
                    self._sheets["Doctors"].update_cell(i, 6, self._now())  # derniere_maj (colonne F)
                    return True
            return False
        except Exception as e:
            logger.error(f"[SheetsDB] Erreur release_doctor: {e}")
            return False

    def update_patient_doctor_assignment(self, patient_id: str, doctor_name: str | None, specialty: str, mode: str) -> bool:
        """Met à jour l'assignation médecin dans la fiche patient."""
        try:
            print(f"[SheetsDB] update_patient_doctor_assignment called for {patient_id} with doctor={doctor_name}, specialty={specialty}")
            patients = self._sheets["Patients"].get_all_records(expected_headers=HEADERS["Patients"])
            for i, p in enumerate(patients, start=2):
                if p.get("patient_id") == patient_id:
                    # Obtenir les indices de colonne dynamiquement
                    headers = self._get_headers("Patients")
                    print(f"[SheetsDB] Headers found: {headers}")
                    col_specialty = headers.index("specialite_assignee") + 1
                    col_doctor = headers.index("medecin_assigne") + 1
                    col_bed = headers.index("lit_assigne") + 1
                    col_mode = headers.index("mode_affectation") + 1
                    col_status = headers.index("statut") + 1
                    print(f"[SheetsDB] Updating row {i}: specialty_col={col_specialty}, doctor_col={col_doctor}, mode_col={col_mode}, status_col={col_status}")
                    self._sheets["Patients"].update_cell(i, col_specialty, specialty)
                    self._sheets["Patients"].update_cell(i, col_doctor, doctor_name or "")
                    self._sheets["Patients"].update_cell(i, col_mode, mode)
                    
                    # Déterminer le statut
                    new_status = "En attente"
                    if doctor_name:
                        new_status = "En consultation"
                    elif mode == "Transfert":
                        new_status = "Transféré"
                    
                    self._sheets["Patients"].update_cell(i, col_status, new_status)
                    self._invalidate_cache()
                    print(f"[SheetsDB] [OK] Patient {patient_id} updated with doctor={doctor_name}")
                    return True
            print(f"[SheetsDB] ✗ Patient {patient_id} not found in sheet")
            return False
        except Exception as e:
            logger.error(f"[SheetsDB] Erreur update_patient_doctor_assignment: {e}")
            import traceback
            traceback.print_exc()
            return False

    def delete_doctor(self, doctor_id: str) -> bool:
        """Supprime un médecin de la base."""
        try:
            doctors = self._sheets["Doctors"].get_all_records()
            for i, doc in enumerate(doctors, start=2):
                if doc.get("doctor_id") == doctor_id:
                    self._sheets["Doctors"].delete_rows(i)
                    return True
            return False
        except Exception as e:
            logger.error(f"[SheetsDB] Erreur delete_doctor: {e}")
            return False
