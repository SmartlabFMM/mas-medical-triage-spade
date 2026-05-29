"""
scripts/migrate_sheets_to_pg.py
Migration complète Google Sheets → PostgreSQL
Usage: python scripts/migrate_sheets_to_pg.py
"""
import sys, os, uuid
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
import gspread

stats = {
    "resources":         {"migrated": 0, "skipped": 0, "errors": 0},
    "doctors":           {"migrated": 0, "skipped": 0, "errors": 0},
    "patients":          {"migrated": 0, "skipped": 0, "errors": 0},
    "decisions":         {"migrated": 0, "skipped": 0, "errors": 0},
    "logs":              {"migrated": 0, "skipped": 0, "errors": 0},
    "users":             {"migrated": 0, "skipped": 0, "errors": 0},
    "archived_patients": {"migrated": 0, "skipped": 0, "errors": 0},
}

def safe_bool(val):
    if isinstance(val, bool): return val
    return str(val).strip().upper() in ("TRUE","VRAI","1","OUI","YES")

def safe_float(val, default=None):
    try: return float(str(val).replace(',','.').strip()) if val not in (None,'','None') else default
    except: return default

def safe_int(val, default=None):
    try: return int(str(val).strip()) if val not in (None,'','None') else default
    except: return default

def safe_str(val):
    return str(val).strip() if val not in (None,'','None') else None

def safe_uuid(val):
    try: return str(uuid.UUID(str(val).strip()))
    except: return str(uuid.uuid4())

def safe_datetime(val):
    if not val or str(val).strip() in ('','None'): return datetime.now()
    for fmt in ('%Y-%m-%d %H:%M:%S','%Y-%m-%dT%H:%M:%S','%d/%m/%Y %H:%M:%S','%d/%m/%Y','%Y-%m-%d'):
        try: return datetime.strptime(str(val).strip(), fmt)
        except: continue
    return datetime.now()

def safe_list(val):
    if not val or str(val).strip() in ('','None','[]'): return []
    s = str(val).strip()
    if s.startswith('['):
        try:
            import ast; return ast.literal_eval(s)
        except: pass
    return [x.strip() for x in s.split(',') if x.strip()]

def rows_to_dicts(ws):
    return [r for r in ws.get_all_records(default_blank='') if any(str(v).strip() for v in r.values())]

print("\n🔗 Connecting to Google Sheets...")
gc = gspread.service_account(filename='credentials/credentials.json')
sh = gc.open_by_key(os.getenv('GOOGLE_SPREADSHEET_ID'))
print("✅ Google Sheets OK\n")

print("🔗 Connecting to PostgreSQL...")
from api.app import app
from database.connection import db
from database.models import Patient, Decision, Resource, Log, Doctor, User, ArchivedPatient
print("✅ PostgreSQL OK\n")

def migrate_resources(ws):
    print("🛏️  Migrating Resources...")
    with app.app_context():
        for row in rows_to_dicts(ws):
            nom = safe_str(row.get('nom_ressource'))
            if not nom: stats['resources']['skipped'] += 1; continue
            try:
                if db.session.query(Resource).filter_by(nom_ressource=nom).first():
                    stats['resources']['skipped'] += 1; continue
                db.session.add(Resource(
                    nom_ressource=nom,
                    disponibilite=safe_bool(row.get('disponibilite', True)),
                    charge_percent=safe_float(row.get('charge_%')),
                    patient_assigne=safe_str(row.get('patient_assigne')),
                    statut=safe_str(row.get('statut')) or 'disponible',
                    derniere_maj=safe_datetime(row.get('derniere_maj')),
                ))
                db.session.commit(); stats['resources']['migrated'] += 1
                print(f"   ✅ {nom}")
            except Exception as e:
                db.session.rollback(); stats['resources']['errors'] += 1
                print(f"   ❌ {nom}: {e}")

def migrate_doctors(ws):
    print("\n👨‍⚕️  Migrating Doctors...")
    with app.app_context():
        for row in rows_to_dicts(ws):
            nom = safe_str(row.get('nom'))
            if not nom: stats['doctors']['skipped'] += 1; continue
            try:
                if db.session.query(Doctor).filter_by(nom=nom).first():
                    stats['doctors']['skipped'] += 1; continue
                db.session.add(Doctor(
                    doctor_id=safe_uuid(row.get('doctor_id')),
                    nom=nom,
                    specialite=safe_str(row.get('specialite')) or 'general',
                    disponible=safe_bool(row.get('disponible', True)),
                    patient_assigne=safe_str(row.get('patient_assigne')),
                    derniere_maj=safe_datetime(row.get('derniere_maj')),
                ))
                db.session.commit(); stats['doctors']['migrated'] += 1
                print(f"   ✅ {nom}")
            except Exception as e:
                db.session.rollback(); stats['doctors']['errors'] += 1
                print(f"   ❌ {nom}: {e}")

def migrate_patients(ws):
    print("\n🏥  Migrating Patients...")
    with app.app_context():
        for row in rows_to_dicts(ws):
            nom = safe_str(row.get('nom'))
            if not nom: stats['patients']['skipped'] += 1; continue
            pid = safe_uuid(row.get('patient_id'))
            try:
                if db.session.query(Patient).filter_by(patient_id=pid).first():
                    stats['patients']['skipped'] += 1; continue
                db.session.add(Patient(
                    patient_id=pid, nom=nom,
                    age=safe_int(row.get('age')),
                    genre=safe_str(row.get('genre')),
                    symptomes=safe_list(row.get('symptomes')),
                    symptoms_details=safe_str(row.get('symptoms_details')),
                    action_finale=safe_str(row.get('action_finale')) or '',
                    heure_arrivee=safe_datetime(row.get('heure_arrivée') or row.get('heure_arrivee')),
                    statut=safe_str(row.get('statut')) or 'en_attente',
                    specialite_assignee=safe_str(row.get('specialite_assignee')) or '',
                    medecin_assigne=safe_str(row.get('medecin_assigne')) or '',
                    lit_assigne=safe_str(row.get('lit_assigne')) or '',
                    mode_affectation=safe_str(row.get('mode_affectation')) or '',
                ))
                db.session.commit(); stats['patients']['migrated'] += 1
                print(f"   ✅ {nom} ({pid[:8]}...)")
            except Exception as e:
                db.session.rollback(); stats['patients']['errors'] += 1
                print(f"   ❌ {nom}: {e}")

def migrate_decisions(ws):
    print("\n📋  Migrating Decisions...")
    with app.app_context():
        for row in rows_to_dicts(ws):
            raw_pid = safe_str(row.get('patient_id'))
            if not raw_pid: stats['decisions']['skipped'] += 1; continue
            try: pid = str(uuid.UUID(raw_pid))
            except: stats['decisions']['skipped'] += 1; continue
            did = safe_uuid(row.get('decision_id'))
            try:
                if db.session.query(Decision).filter_by(decision_id=did).first():
                    stats['decisions']['skipped'] += 1; continue
                if not db.session.query(Patient).filter_by(patient_id=pid).first():
                    stats['decisions']['skipped'] += 1; continue
                db.session.add(Decision(
                    decision_id=did, patient_id=pid,
                    score_gravite=safe_float(row.get('score_gravite')),
                    action=safe_str(row.get('action')) or 'surveiller',
                    raisonnement=safe_str(row.get('raisonnement')) or '',
                    nb_cycles=safe_int(row.get('nb_cycles')) or 1,
                    timestamp=safe_datetime(row.get('timestamp')),
                    agent_decideur=safe_str(row.get('agent_decideur')) or 'MetaAgent',
                ))
                db.session.commit(); stats['decisions']['migrated'] += 1
            except Exception as e:
                db.session.rollback(); stats['decisions']['errors'] += 1
                print(f"   ❌ Decision: {e}")
    print(f"   ✅ Decisions migrated: {stats['decisions']['migrated']}")

def migrate_logs(ws):
    print("\n📝  Migrating Logs...")
    with app.app_context():
        for row in rows_to_dicts(ws):
            agent = safe_str(row.get('agent'))
            if not agent: stats['logs']['skipped'] += 1; continue
            try:
                # ✅ patient_id = None if not valid UUID or patient doesn't exist
                patient_id = None
                raw_pid = safe_str(row.get('patient_id'))
                if raw_pid:
                    try:
                        pid_uuid = str(uuid.UUID(raw_pid))
                        if db.session.query(Patient).filter_by(patient_id=pid_uuid).first():
                            patient_id = pid_uuid
                    except: pass

                db.session.add(Log(
                    timestamp=safe_datetime(row.get('timestamp')),
                    agent=agent,
                    action=safe_str(row.get('action')) or '',
                    details=safe_str(row.get('details')) or '',
                    patient_id=patient_id,
                    niveau=safe_str(row.get('niveau')) or 'INFO',
                ))
                db.session.commit(); stats['logs']['migrated'] += 1
            except Exception as e:
                db.session.rollback(); stats['logs']['errors'] += 1
                print(f"   ❌ Log: {e}")
    print(f"   ✅ Logs migrated: {stats['logs']['migrated']}")

def migrate_users(ws):
    print("\n👤  Migrating Users...")
    with app.app_context():
        for row in rows_to_dicts(ws):
            username = safe_str(row.get('username'))
            if not username: stats['users']['skipped'] += 1; continue
            try:
                if db.session.query(User).filter_by(username=username).first():
                    stats['users']['skipped'] += 1; continue
                db.session.add(User(
                    id=safe_uuid(row.get('user_id')),  # ✅ model column is 'id' not 'user_id'
                    username=username,
                    password_hash=safe_str(row.get('password_hash')) or '',
                    role=safe_str(row.get('role')) or 'doctor',
                    created_at=safe_datetime(row.get('created_at')),
                    active=safe_bool(row.get('active', True)),
                ))
                db.session.commit(); stats['users']['migrated'] += 1
                print(f"   ✅ User: {username}")
            except Exception as e:
                db.session.rollback(); stats['users']['errors'] += 1
                print(f"   ❌ User {username}: {e}")

def migrate_archived_patients(ws):
    print("\n📦  Migrating Archived Patients...")
    with app.app_context():
        for row in rows_to_dicts(ws):
            nom = safe_str(row.get('nom'))
            if not nom: stats['archived_patients']['skipped'] += 1; continue
            pid = safe_uuid(row.get('patient_id'))
            try:
                if db.session.query(ArchivedPatient).filter_by(patient_id=pid).first():
                    stats['archived_patients']['skipped'] += 1; continue
                db.session.add(ArchivedPatient(
                    patient_id=pid, nom=nom,
                    age=safe_int(row.get('age')),
                    genre=safe_str(row.get('genre')),
                    symptomes=safe_list(row.get('symptomes')),
                    symptoms_details=safe_str(row.get('symptoms_details')),
                    action_finale=safe_str(row.get('action_finale')) or '',
                    heure_arrivee=safe_datetime(row.get('heure_arrivée') or row.get('heure_arrivee')),
                    statut=safe_str(row.get('statut')) or 'archive',
                    specialite_assignee=safe_str(row.get('specialite_assignee')) or '',
                    medecin_assigne=safe_str(row.get('medecin_assigne')) or '',
                    lit_assigne=safe_str(row.get('lit_assigne')) or '',
                    mode_affectation=safe_str(row.get('mode_affectation')) or '',
                    archived_at=safe_datetime(row.get('archived_at')),
                    archived_reason=safe_str(row.get('archived_reason')) or '',
                ))
                db.session.commit(); stats['archived_patients']['migrated'] += 1
            except Exception as e:
                db.session.rollback(); stats['archived_patients']['errors'] += 1
                print(f"   ❌ {nom}: {e}")
    print(f"   ✅ Archived migrated: {stats['archived_patients']['migrated']}")

# ── RUN ──────────────────────────────────────────────────────────────────────
print("=" * 60)
print("  MIGRATION GOOGLE SHEETS → POSTGRESQL")
print("=" * 60)

migrate_resources(sh.worksheet('Resources'))
migrate_doctors(sh.worksheet('Doctors'))
migrate_patients(sh.worksheet('Patients'))
migrate_decisions(sh.worksheet('Decisions'))
migrate_logs(sh.worksheet('Logs'))
migrate_users(sh.worksheet('Users'))
migrate_archived_patients(sh.worksheet('ArchivedPatients'))

print("\n" + "=" * 60)
print("  RÉSUMÉ MIGRATION")
print("=" * 60)
tm = ts = te = 0
for table, s in stats.items():
    m,sk,e = s['migrated'],s['skipped'],s['errors']
    tm+=m; ts+=sk; te+=e
    print(f"  {'✅' if e==0 else '⚠️'} {table:<22} migrated={m:>4}  skipped={sk:>4}  errors={e:>3}")
print("-" * 60)
print(f"  TOTAL                    migrated={tm:>4}  skipped={ts:>4}  errors={te:>3}")
print("=" * 60)
print("\n🎉 Migration completed!" if te==0 else f"\n⚠️  {te} errors — check output above.")