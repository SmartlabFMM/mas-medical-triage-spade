# Codebase Inventory - AI Multi-Agent Medical Triage System

## Core Domains

### API

| Feature | Purpose | Files | Signatures | Config / Env | Notes |
|---------|---------|-------|------------|--------------|-------|
| Symptom Analysis Endpoint | Analyze patient symptoms and return triage decision | `api/app.py` | `@app.route('/symptoms', methods=['POST'])` (line 172) | `JWT_SECRET_KEY` | Rule-based fallback when LLM unavailable |
| Decision Validation Endpoint | Validate doctor's triage decision | `api/app.py` | `@app.route('/decision', methods=['POST'])` (line 231) | `JWT_SECRET_KEY` | Stores decision in database |
| Patient CRUD Operations | Get all patients from database | `api/app.py` | `@app.route('/patients', methods=['GET'])` (line 290) | `DATABASE_URL` | Returns demo data if DB fails |
| Resource Management | Get hospital resources (beds, specialists) | `api/app.py` | `@app.route('/resources', methods=['GET'])` (line 299) | `DATABASE_URL` | Replaces patient UUID with name |
| Decision History | Get all triage decisions | `api/app.py` | `@app.route('/decisions', methods=['GET'])` (line 315) | `DATABASE_URL` | Query from Decision table |
| System Logs | Get agent activity logs | `api/app.py` | `@app.route('/logs', methods=['GET'])` (line 323) | `DATABASE_URL` | Supports limit query param |
| System Metrics | Get system KPIs (patients, decisions, hospitalization rate) | `api/app.py` | `@app.route('/metrics', methods=['GET'])` (line 332) | `DATABASE_URL` | Aggregates from multiple tables |
| Health Check | Verify database connectivity | `api/app.py` | `@app.route('/health', methods=['GET'])` (line 350) | `DATABASE_URL` | Simple SELECT 1 query |
| Admin Dashboard | Get comprehensive admin KPIs and stats | `api/app.py` | `@app.route('/admin/dashboard', methods=['GET'])` (line 366) | `DATABASE_URL` | Returns patient evolution, doctor load, critical cases |
| Admin Resources CRUD | Manage hospital resources (GET, POST, PUT, DELETE) | `api/app.py` | `@app.route('/admin/resources', methods=['GET', 'POST', 'PUT'])` (line 507) | `DATABASE_URL` | Updates Resource table |
| Admin Doctors CRUD | Manage doctor records (GET, POST, PUT, DELETE) | `api/app.py` | `@app.route('/admin/doctors', methods=['GET', 'POST', 'PUT'])` (line 537) | `DATABASE_URL` | Updates Doctor table |
| Admin Patients List | Get all active and archived patients | `api/app.py` | `@app.route('/admin/patients', methods=['GET'])` (line 573) | `DATABASE_URL` | Joins Patient and ArchivedPatient |
| Admin Decisions List | Get all triage decisions | `api/app.py` | `@app.route('/admin/decisions', methods=['GET'])` (line 588) | `DATABASE_URL` | Returns Decision records |
| Admin Logs List | Get recent system logs | `api/app.py` | `@app.route('/admin/logs', methods=['GET'])` (line 597) | `DATABASE_URL` | Last 100 logs, ordered by timestamp |
| User Authentication | Login with JWT token generation | `api/auth.py` | `@auth_bp.route('/login', methods=['POST'])` (line 49) | `USERS_JSON` | Bcrypt password hashing |
| User Registration | Create new user account | `api/auth.py` | `@auth_bp.route('/register', methods=['POST'])` (line 84) | `USERS_JSON` | Supports patient, secretaire, medical, admin roles |
| Current User Info | Get authenticated user profile | `api/auth.py` | `@auth_bp.route('/me', methods=['GET'])` (line 111) | JWT token | Requires valid JWT |
| User List (Admin) | List all users (admin only) | `api/auth.py` | `@auth_bp.route('/users', methods=['GET'])` (line 124) | JWT token | Admin role required |
| Doctor Patient List | Get patients assigned to authenticated doctor | `api/doctor.py` | `@doctor_bp.route('/patients', methods=['GET'])` (line 69) | JWT token | Filters by medecin_assigne, excludes treated/transferred |
| Doctor Patient Status Update | Update patient status (traité, transféré, etc.) | `api/doctor.py` | `@doctor_bp.route('/patient/<patient_id>/status', methods=['POST'])` (line 121) | JWT token | Archives patient on final status, releases bed |
| Doctor Statistics | Get patient severity and status distribution | `api/doctor.py` | `@doctor_bp.route('/stats', methods=['GET'])` (line 213) | JWT token | Aggregates by normalized_score |
| Doctor History | Get archived patients for doctor | `api/doctor.py` | `@doctor_bp.route('/history', methods=['GET'])` (line 260) | JWT token | Queries ArchivedPatient table |

### UI

| Feature | Purpose | Files | Signatures | Config / Env | Notes |
|---------|---------|-------|------------|--------------|-------|
| Admin Dashboard Page | Admin interface with KPIs, charts, doctor management | `interface/src/pages/AdminPage.tsx` | `function AdminPage()` (line 1) | `VITE_API_BASE_URL` | Uses Recharts for visualizations |
| Doctor Dashboard Page | Doctor interface with patient list and statistics | `interface/src/pages/DoctorDashboard.tsx` | `function DoctorDashboard()` (line 1) | `VITE_API_BASE_URL` | JWT auth required |
| Login Page | User authentication interface | `interface/src/pages/LoginPage.tsx` | `function LoginPage()` (line 1) | `VITE_API_BASE_URL` | Stores token in sessionStorage |
| Medical Page | Medical staff interface for patient intake | `interface/src/pages/MedicalPage.tsx` | `function MedicalPage()` (line 1) | `VITE_API_BASE_URL` | Symptom form with severity display |
| Patient Page | Patient detail view with history | `interface/src/pages/PatientPage.tsx` | `function PatientPage()` (line 1) | `VITE_API_BASE_URL` | Shows decisions and timeline |
| Secretaire Page | Secretary interface for patient registration | `interface/src/pages/SecretairePage.tsx` | `function SecretairePage()` (line 1) | `VITE_API_BASE_URL` | Patient creation form |
| Chat Interface | Real-time chat interface for agent communication | `interface/src/pages/chat.tsx` | `function ChatPage()` (line 1) | `VITE_API_BASE_URL` | WebSocket-based messaging |
| Dashboard Overview | Main dashboard with system overview | `interface/src/pages/dashboard.tsx` | `function Dashboard()` (line 1) | `VITE_API_BASE_URL` | Landing page after login |
| Session Page | Doctor session interface for patient treatment | `interface/src/pages/session.tsx` | `function SessionPage()` (line 1) | `VITE_API_BASE_URL` | Treatment workflow |
| API Client | HTTP client for Flask API communication | `interface/src/lib/api.ts` | `function request<T>()` (line 14) | `VITE_API_BASE_URL` | Generic fetch wrapper |
| Doctor API Client | Authenticated API client for doctor endpoints | `interface/src/lib/doctorApi.ts` | `function authRequest<T>()` (line 24) | `VITE_API_BASE_URL` | Adds JWT Authorization header |
| Utility Functions | Helper functions for UI | `interface/src/lib/utils.ts` | `function cn()` (line 1) | none | Tailwind class concatenation |

### Agents

| Feature | Purpose | Files | Signatures | Config / Env | Notes |
|---------|---------|-------|------------|--------------|-------|
| Conversational Agent | Receives patient data, coordinates triage workflow | `agents/conversational_agent.py` | `class ConversationalAgent(Agent)` (line 30) | `JID_CONVERSATIONAL`, `PWD_CONVERSATIONAL` | WatchPatientsBehaviour polls DB every 10s |
| Listen Decision Behaviour | Receives final decisions from MetaAgent | `agents/conversational_agent.py` | `class ListenDecisionBehaviour(CyclicBehaviour)` (line 33) | none | Writes decision to Database |
| Send Symptoms Behaviour | Sends patient symptoms to ClinicalAgent | `agents/conversational_agent.py` | `class SendSymptomsBehaviour(OneShotBehaviour)` (line 76) | none | Writes patient to Database first |
| Clinical Agent | BDI agent for clinical evaluation and severity scoring | `agents/clinical_agent.py` | `class ClinicalAgent(Agent)` (line 24) | `JID_CLINICAL`, `PWD_CLINICAL` | Uses BeliefBase for state management |
| Triage Behaviour | Evaluates patient symptoms and generates clinical options | `agents/clinical_agent.py` | `class TriageBehaviour(CyclicBehaviour)` (line 30) | none | Calls compute_score from utils |
| Resource Agent | Goal-based agent for resource allocation | `agents/resource_agent.py` | `class ResourceAgent(Agent)` (line 26) | `JID_RESOURCE`, `PWD_RESOURCE` | Reads Google Sheets Resources sheet |
| Check Resources Behaviour | Monitors resource status and responds to queries | `agents/resource_agent.py` | `class CheckResourcesBehaviour(CyclicBehaviour)` (line 31) | none | Internal caching to avoid API saturation |
| Allocate Resource Behaviour | Allocates beds/specialists to patients | `agents/resource_agent.py` | `class AllocateResourceBehaviour(OneShotBehaviour)` (line 145) | none | Updates Google Sheets |
| Meta Agent | Coordination agent for decision arbitration | `agents/meta_agent.py` | `class MetaAgent(Agent)` (line 20) | `JID_META`, `PWD_META` | Collects clinical and resource data |
| Decision Behaviour | Makes final triage decisions based on all inputs | `agents/meta_agent.py` | `class DecisionBehaviour(CyclicBehaviour)` (line 22) | none | Uses specialty_router for doctor assignment |
| Base Agent | Common base class for all SPADE agents | `agents/base_agent.py` | `class BaseAgent(Agent)` (line 1) | none | Provides common initialization |

### Database

| Feature | Purpose | Files | Signatures | Config / Env | Notes |
|---------|---------|-------|------------|--------------|-------|
| Database Connection | PostgreSQL connection management | `database/connection.py` | `def init_app(app)` (line 1) | `DATABASE_URL` | Flask-SQLAlchemy integration |
| Patient Model | SQLAlchemy model for patient records | `database/models.py` | `class Patient(db.Model)` (line 9) | `DATABASE_URL` | JSON column for symptoms |
| Decision Model | SQLAlchemy model for triage decisions | `database/models.py` | `class Decision(db.Model)` (line 33) | `DATABASE_URL` | Foreign key to Patient |
| Resource Model | SQLAlchemy model for hospital resources | `database/models.py` | `class Resource(db.Model)` (line 49) | `DATABASE_URL` | Beds, specialists, equipment |
| Log Model | SQLAlchemy model for agent activity logs | `database/models.py` | `class Log(db.Model)` (line 63) | `DATABASE_URL` | Audit trail |
| Doctor Model | SQLAlchemy model for doctor records | `database/models.py` | `class Doctor(db.Model)` (line 78) | `DATABASE_URL` | Specialty and availability |
| User Model | SQLAlchemy model for user accounts | `database/models.py` | `class User(db.Model)` (line 92) | `DATABASE_URL` | Authentication and roles |
| Archived Patient Model | SQLAlchemy model for archived patients | `database/models.py` | `class ArchivedPatient(db.Model)` (line 104) | `DATABASE_URL` | Historical records |
| Patient Repository | CRUD operations for patients | `database/repositories/patient_repository.py` | `class PatientRepository` (line 1) | `DATABASE_URL` | SQLAlchemy ORM queries |
| Decision Repository | CRUD operations for decisions | `database/repositories/decision_repository.py` | `class DecisionRepository` (line 1) | `DATABASE_URL` | Query with patient joins |
| Resource Repository | CRUD operations for resources | `database/repositories/resource_repository.py` | `class ResourceRepository` (line 1) | `DATABASE_URL` | Availability filtering |
| Log Repository | CRUD operations for logs | `database/repositories/log_repository.py` | `class LogRepository` (line 1) | `DATABASE_URL` | Timestamp ordering |
| Doctor Repository | CRUD operations for doctors | `database/repositories/doctor_repository.py` | `class DoctorRepository` (line 1) | `DATABASE_URL` | Specialty filtering |
| Archived Patient Repository | CRUD operations for archived patients | `database/repositories/archived_patient_repository.py` | `class ArchivedPatientRepository` (line 1) | `DATABASE_URL` | Query by patient_id |
| User Repository | CRUD operations for users | `database/repositories/user_repository.py` | `class UserRepository` (line 1) | `DATABASE_URL` | Role-based queries |

### Core

| Feature | Purpose | Files | Signatures | Config / Env | Notes |
|---------|---------|-------|------------|--------------|-------|
| SheetsDB Adapter | Google Sheets as database adapter | `core/sheets_db.py` | `class SheetsDB` (line 1) | `GOOGLE_CREDENTIALS_PATH`, `SPREADSHEET_NAME` | gspread library, retry logic |
| Patient CRUD | Create, read, update patients in Sheets | `core/sheets_db.py` | `def upsert_patient()` (line 350) | `SPREADSHEET_NAME` | Handles both insert and update |
| Doctor Assignment | Assign patient to doctor in Sheets | `core/sheets_db.py` | `def assign_doctor()` (line 616) | `SPREADSHEET_NAME` | Updates patient_assigne column |
| Doctor Selection | Find available doctor by specialty | `core/sheets_db.py` | `def find_available_doctor()` (line 576) | `SPREADSHEET_NAME` | Chooses doctor with minimum patients |
| Patient Decision Update | Update patient decision and status | `core/sheets_db.py` | `def update_patient_decision()` (line 404) | `SPREADSHEET_NAME` | Default status "en_attente" |
| PostgreSQL SheetsDB | PostgreSQL-based implementation of SheetsDB interface | `core/postgres_db.py` | `class PGSheetsDB` (line 1) | `DATABASE_URL` | Provides same API as SheetsDB |
| Message Ontology | Message types and performative definitions | `core/message.py` | `class MessageType(Enum)` (line 1) | none | SYMPTOM_REPORT, CLINICAL_OPTIONS, etc. |
| Message Builder | Build SPADE messages with ontology | `core/message.py` | `def build_message()` (line 1) | none | Handles patient_id, thread, performative |
| Message Parser | Parse SPADE message body | `core/message.py` | `def parse_body()` (line 1) | none | Extracts patient_id, msg_type |
| Message Bus | Async message passing between agents | `core/message_bus.py` | `class MessageBus` (line 1) | none | Asyncio-based pub/sub |
| Belief Base | BDI belief storage for agents | `core/belief_base.py` | `class BeliefBase` (line 1) | none | Key-value store with update/get |
| Environment | Agent lifecycle management | `core/environment.py` | `def start_agents()` (line 1) | `XMPP_SERVER` | Coordinates agent startup/shutdown |
| LLM Engine | Large Language Model integration (optional) | `core/llm_engine.py` | `class LLMEngine` (line 1) | `OPENAI_API_KEY` | OpenAI GPT integration for triage |
| Specialty Router | Route patients to appropriate specialty | `core/specialty_router.py` | `def route()` (line 1) | none | Maps symptoms to medical specialties |
| Write Queue | Async write queue for database operations | `core/write_queue.py` | `class WriteQueue` (line 1) | none | Batches writes to reduce API calls |

### Utilities

| Feature | Purpose | Files | Signatures | Config / Env | Notes |
|---------|---------|-------|------------|--------------|-------|
| Severity Calculator | Calculate medical severity score from symptoms | `utils/severity_calculator.py` | `def compute_score()` (line 1) | none | Rule-based v2.0 algorithm |
| Severity Label | Convert score to severity category | `utils/severity_calculator.py` | `def severity_label()` (line 1) | none | léger, modéré, urgent, critique |
| Logger | Centralized logging for agents | `utils/logger.py` | `def log_agent_state()` (line 1) | `LOG_LEVEL`, `LOG_FILE` | Writes to logs/triage.log |
| Log Decision | Log triage decisions with details | `utils/logger.py` | `def log_decision()` (line 1) | `LOG_LEVEL`, `LOG_FILE` | Includes rationale and score |
| Log Warning | Log warning messages | `utils/logger.py` | `def log_warning()` (line 1) | `LOG_LEVEL`, `LOG_FILE` | For degraded mode situations |
| Metrics | System performance metrics collection | `utils/metrics.py` | `class Metrics` (line 1) | none | Tracks cycles, reevaluations, errors |
| UUID Generator | Generate unique identifiers | `utils/helpers.py` | `def uuid_gen()` (line 1) | none | Returns string UUID |

### Simulation

| Feature | Purpose | Files | Signatures | Config / Env | Notes |
|---------|---------|-------|------------|--------------|-------|
| Patient Generator | Generate random patient data for testing | `simulation/patient_generator.py` | `def generate_batch()` (line 1) | `MAX_PATIENTS` | Creates realistic symptom combinations |
| Simulator | Run simulation scenarios | `simulation/simulator.py` | `def run_simulation()` (line 1) | `SIMULATION_SPEED` | Controls simulation timing |
| Run Scenarios | Execute predefined test scenarios | `simulation/run_scenarios.py` | `def run_scenario()` (line 1) | none | Loads from scenarios/*.json |
| Default Scenario | Default 3-patient test scenario | `simulation/scenarios/scenario_default.json` | JSON file | none | Representative test cases |
| Surcharge Scenario | 10 critical patients stress test | `simulation/scenarios/scenario_surcharge.json` | JSON file | none | Tests system under load |

### Models

| Feature | Purpose | Files | Signatures | Config / Env | Notes |
|---------|---------|-------|------------|--------------|-------|
| Patient Model | Pydantic model for patient data | `models/patient.py` | `class Patient(BaseModel)` (line 1) | none | Validation and serialization |
| Clinical Option Model | Pydantic model for clinical decision options | `models/clinical_option.py` | `class ClinicalOption(BaseModel)` (line 1) | none | ActionType enum (hospitaliser, surveiller, transferer) |
| Resource State Model | Pydantic model for resource constraints | `models/resource_state.py` | `class ResourceState(BaseModel)` (line 1) | none | Beds, specialists availability |
| Triage Decision Model | Pydantic model for triage decisions | `models/triage_decision.py` | `class TriageDecision(BaseModel)` (line 1) | none | Includes rationale and cycle count |
| ORM Models | SQLAlchemy ORM models | `models/orm.py` | `class PatientORM(Base)` (line 1) | `DATABASE_URL` | Alternative ORM definitions |

### Tests

| Feature | Purpose | Files | Signatures | Config / Env | Notes |
|---------|---------|-------|------------|--------------|-------|
| Integration Tests | End-to-end system testing | `tests/test_integration.py` | `def test_full_triage_flow()` (line 1) | `DATABASE_URL` | Tests agent coordination |
| Agent Communication Tests | Test message passing between agents | `test_agent_communication.py` | `def test_message_passing()` (line 1) | `XMPP_SERVER` | SPADE message testing |
| API Tests | Test Flask API endpoints | `test_api.py` | `def test_symptoms_endpoint()` (line 1) | `DATABASE_URL` | HTTP request/response testing |
| Calculation Tests | Test severity calculation logic | `test_calculation.py` | `def test_severity_calculation()` (line 1) | none | Unit tests for compute_score |
| Severity Calculator Tests | Comprehensive severity calculator testing | `test_severity_calculator.py` | `def test_compute_score()` (line 1) | none | Tests all symptom combinations |
| System Tests | Full system workflow testing | `test_system.py` | `def test_system_workflow()` (line 1) | `DATABASE_URL`, `XMPP_SERVER` | Integration test suite |

## Cross-Cutting Concerns

| Concern | Details |
|---------|---------|
| **Logging** | `utils/logger.py` – config via `LOG_LEVEL`, `LOG_FILE` – writes to logs/triage.log – centralized log_agent_state, log_decision, log_warning functions |
| **Error Handling** | Global exception handling in API endpoints – retry logic in SheetsDB with exponential backoff – degraded mode fallback when Google Sheets unavailable |
| **Authentication** | JWT-based authentication via Flask-JWT-Extended – bcrypt password hashing – role-based access control (secretaire, medical, admin) – token stored in sessionStorage/localStorage |
| **Security** | Environment variable configuration for secrets – XMPP TLS verification configurable – password validation required – admin-only endpoints protected |
| **Scheduling** | WatchPatientsBehaviour polls database every 10s – WriteQueue batches database operations – ResourceAgent uses internal caching (5s TTL) |
| **Configuration** | Central `config.py` – reads all `.env` vars – XMPP server settings, hospital configuration, simulation parameters, logging settings |
| **Metrics** | `utils/metrics.py` – tracks total_patients, cycles, reevaluations, errors – performance monitoring for triage cycles |
| **Internationalization** | Symptom translation (French ↔ English) in API and Doctor endpoints – French UI labels – SYMPTOMS_FR mapping in doctor.py |
| **Database** | Dual database support: PostgreSQL (primary) and Google Sheets (legacy) – PGSheetsDB provides unified interface – SQLAlchemy ORM with repository pattern |
| **Message Passing** | SPADE FIPA-compliant messages – Message ontology defines types and performatives – Async message bus for inter-agent communication |
| **Caching** | ResourceAgent internal cache for availability summary (5s TTL) – reduces Google Sheets API calls – fallback to stale cache on errors |
| **Quota Management** | Google Sheets API quota handling with retry logic – exponential backoff (2s, 3s, 5s, 9s, 17s) – degraded mode when quota exceeded |
| **Real-time Mode** | `--realtime` flag in main.py – agents listen for new patients in Google Sheets – graceful shutdown with Ctrl+C |
| **Simulation Mode** | Scenario-based testing – random patient generation – configurable simulation speed – stress testing with surcharge scenario |

## Configuration Files

| File | Purpose |
|------|---------|
| `.env.example` | Template for environment variables (XMPP, database, Google Sheets, JWT) |
| `requirements.txt` | Python dependencies (SPADE, Flask, SQLAlchemy, gspread, etc.) |
| `package.json` | Node.js dependencies for React frontend |
| `vite.config.ts` | Vite build configuration for React app |
| `tsconfig.json` | TypeScript configuration |
| `pytest.ini` | Pytest configuration |
| `.gitignore` | Git ignore patterns |
| `prosody.cfg.lua` | XMPP server configuration (Prosody) |
| `setup_xmpp.md` | Instructions for XMPP server setup |

## Entry Points

| File | Purpose |
|------|---------|
| `main.py` | Main entry point for SPADE agents – supports simulation and real-time modes |
| `api/app.py` | Flask API server entry point – registers blueprints, initializes database |
| `interface/src/main.tsx` | React application entry point – mounts App component |
| `run_realtime.ps1` | PowerShell script to start real-time mode agents |

## Key Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| `spade` | 4.x | Multi-agent platform (XMPP-based) |
| `Flask` | Latest | Web framework for API |
| `Flask-JWT-Extended` | Latest | JWT authentication |
| `SQLAlchemy` | Latest | ORM for PostgreSQL |
| `gspread` | Latest | Google Sheets API client |
| `React` | 18+ | Frontend framework |
| `TypeScript` | 5+ | Type-safe JavaScript |
| `Vite` | 5+ | Build tool for React |
| `Recharts` | Latest | Chart library for visualizations |
| `TailwindCSS` | Latest | CSS framework |
| `bcrypt` | Latest | Password hashing |
| `pytest` | Latest | Testing framework |
