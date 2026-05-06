"""
core/sheets_manager.py — Google Sheets Integration.
Gère toutes les opérations lecture/écriture avec retry et cache.
"""
from __future__ import annotations
import time
import logging
from datetime import datetime
from typing import Any
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError, SpreadsheetNotFound

logger = logging.getLogger(__name__)

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

RESOURCES_HEADERS = ["name", "availability", "load",
                     "assigned_patient", "status", "last_updated"]
LOGS_HEADERS      = ["timestamp", "agent", "action", "details", "patient_id"]


class SheetsManager:
    """
    Gestionnaire centralisé Google Sheets.
    Authentification, création des feuilles, écriture avec retry.
    """

    def __init__(self, credentials_path: str,
                 spreadsheet_name: str = "MAS_Resources"):
        self.credentials_path = credentials_path
        self.spreadsheet_name = spreadsheet_name
        self._client:           gspread.Client    | None = None
        self._spreadsheet:      gspread.Spreadsheet| None = None
        self._sheet_resources:  gspread.Worksheet | None = None
        self._sheet_logs:       gspread.Worksheet | None = None
        self._cache:     dict[str, Any] = {}
        self._cache_ttl: float = 5.0
        self._cache_time:float = 0.0

    # ── Authentification ──────────────────────────────────────────────────────

    def authenticate(self) -> None:
        creds = Credentials.from_service_account_file(
            self.credentials_path, scopes=SCOPES
        )
        self._client = gspread.authorize(creds)
        logger.info("Google Sheets : authentification OK")

    # ── Setup spreadsheet ─────────────────────────────────────────────────────

    def setup_spreadsheet(self) -> None:
        try:
            self._spreadsheet = self._client.open(self.spreadsheet_name)
            logger.info(f"Spreadsheet ouvert : {self.spreadsheet_name}")
        except SpreadsheetNotFound:
            self._spreadsheet = self._client.create(self.spreadsheet_name)
            logger.info(f"Spreadsheet créé : {self.spreadsheet_name}")
        self._setup_sheets()

    def _setup_sheets(self) -> None:
        titles = [ws.title for ws in self._spreadsheet.worksheets()]

        if "Resources" not in titles:
            self._sheet_resources = self._spreadsheet.add_worksheet(
                title="Resources", rows=100, cols=10)
            self._sheet_resources.append_row(RESOURCES_HEADERS)
        else:
            self._sheet_resources = self._spreadsheet.worksheet("Resources")

        if "Logs" not in titles:
            self._sheet_logs = self._spreadsheet.add_worksheet(
                title="Logs", rows=1000, cols=10)
            self._sheet_logs.append_row(LOGS_HEADERS)
        else:
            self._sheet_logs = self._spreadsheet.worksheet("Logs")

        if "Sheet1" in titles:
            self._spreadsheet.del_worksheet(
                self._spreadsheet.worksheet("Sheet1"))

    # ── Écriture avec retry ───────────────────────────────────────────────────

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
                    self.append_log("SYSTEM", "ERROR", str(e))
                    raise
                else:
                    time.sleep(1)

    def update_resource(self, data: dict) -> None:
        """Met à jour ou crée une ligne dans Sheet1 (Resources)."""
        name = data.get("resource", "Unknown")
        row  = [
            name,
            str(data.get("availability", True)),
            str(data.get("load", 0)),
            data.get("patient", ""),
            data.get("status", "idle"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ]

        def _write():
            try:
                cell = self._sheet_resources.find(name)
                self._sheet_resources.update(
                    f"A{cell.row}:F{cell.row}", [row])
                logger.info(f"Ressource mise à jour : {name}")
            except gspread.exceptions.CellNotFound:
                self._sheet_resources.append_row(row)
                logger.info(f"Ressource ajoutée : {name}")

        self._retry(_write)
        self._invalidate_cache()

    def append_log(self, agent: str, action: str,
                   details: str = "", patient_id: str = "") -> None:
        """Ajoute une entrée dans Sheet2 (Logs)."""
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            agent, action, details, patient_id
        ]
        self._retry(self._sheet_logs.append_row, row)

    # ── Lecture avec cache ────────────────────────────────────────────────────

    def get_all_resources(self) -> list[dict]:
        now = time.time()
        if "res" in self._cache and (now - self._cache_time) < self._cache_ttl:
            return self._cache["res"]
        records = self._sheet_resources.get_all_records()
        self._cache["res"] = records
        self._cache_time   = now
        return records

    def get_all_logs(self, limit: int = 100) -> list[dict]:
        records = self._sheet_logs.get_all_records()
        return records[-limit:]

    def get_metrics(self) -> dict:
        resources = self.get_all_resources()
        if not resources:
            return {"avg_load": 0, "available_count": 0,
                    "busy_count": 0, "total_resources": 0}
        loads     = [float(r.get("load", 0)) for r in resources]
        available = sum(1 for r in resources
                        if str(r.get("availability")) == "True")
        busy      = sum(1 for r in resources if r.get("status") == "busy")
        return {
            "avg_load":        round(sum(loads) / len(loads), 1),
            "available_count": available,
            "busy_count":      busy,
            "total_resources": len(resources),
        }

    def _invalidate_cache(self) -> None:
        self._cache.clear()
        self._cache_time = 0.0
