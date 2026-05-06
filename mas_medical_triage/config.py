"""
config.py — Configuration centrale (SPADE + Google Sheets).
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── XMPP / SPADE ─────────────────────────────────────────────────────────────
XMPP_SERVER: str = os.getenv("XMPP_SERVER", "localhost")

# Security Settings
XMPP_VERIFY_CERTIFICATE: bool = os.getenv("XMPP_VERIFY_CERTIFICATE", "false").lower() == "true"  # Default false for localhost

# For SPADE, verify_security controls both authentication and certificate verification
# We adjust it based on certificate verification setting for local development
XMPP_VERIFY_SECURITY_RAW: bool = os.getenv("XMPP_VERIFY_SECURITY", "true").lower() == "true"
XMPP_ALLOW_TLS: bool = os.getenv("XMPP_ALLOW_TLS", "true").lower() == "true"

# Adjust verify_security based on certificate verification for development
XMPP_VERIFY_SECURITY: bool = XMPP_VERIFY_SECURITY_RAW and XMPP_VERIFY_CERTIFICATE

AGENTS_JID = {
    "conversational": os.getenv("JID_CONVERSATIONAL", "conversational@localhost"),
    "clinical":       os.getenv("JID_CLINICAL",        "clinical@localhost"),
    "resource":       os.getenv("JID_RESOURCE",         "resource@localhost"),
    "meta":           os.getenv("JID_META",             "meta@localhost"),
}

# Require explicit password configuration - no defaults for security
def _get_agent_password(agent_name: str) -> str:
    """Get agent password from environment, raise error if not set."""
    password = os.getenv(f"PWD_{agent_name.upper()}")
    if not password:
        raise ValueError(f"Password for {agent_name} agent not configured. Set PWD_{agent_name.upper()} in .env file.")
    return password

AGENTS_PWD = {
    "conversational": _get_agent_password("conversational"),
    "clinical":       _get_agent_password("clinical"),
    "resource":       _get_agent_password("resource"),
    "meta":           _get_agent_password("meta"),
}

# ── Hôpital ───────────────────────────────────────────────────────────────────
HOSPITAL_NAME: str    = os.getenv("HOSPITAL_NAME", "Urgences_Demo")
BEDS_TOTAL: int       = int(os.getenv("BEDS_TOTAL", 20))
BEDS_AVAILABLE: int   = int(os.getenv("BEDS_AVAILABLE", 15))
WAIT_TIME_AVG: float  = float(os.getenv("WAIT_TIME_AVG", 12.5))

SPECIALISTS: dict[str, int] = {
    "cardiologie":   int(os.getenv("SPECIALIST_CARDIO", 2)),
    "neurologie":    int(os.getenv("SPECIALIST_NEURO", 1)),
    "traumatologie": int(os.getenv("SPECIALIST_TRAUMA", 3)),
    "general":       int(os.getenv("SPECIALIST_GENERAL", 5)),
}

# ── Simulation ────────────────────────────────────────────────────────────────
MAX_PATIENTS: int       = int(os.getenv("MAX_PATIENTS", 20))
TRIAGE_TIMEOUT: float   = float(os.getenv("TRIAGE_TIMEOUT", 6))
SIMULATION_SPEED: float = float(os.getenv("SIMULATION_SPEED", 1.0))

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE: str  = os.getenv("LOG_FILE", "logs/triage.log")

# ── Google Sheets ─────────────────────────────────────────────────────────────
GOOGLE_CREDENTIALS_PATH: str  = os.getenv("GOOGLE_CREDENTIALS_PATH",
                                           "credentials/credentials.json")
GOOGLE_SPREADSHEET_NAME: str  = os.getenv("GOOGLE_SPREADSHEET_NAME", "MAS_Resources")
