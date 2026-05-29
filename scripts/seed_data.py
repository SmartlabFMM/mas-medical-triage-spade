"""Seed initial resources (beds + doctors) into PostgreSQL."""
import sys
sys.path.append('.')

from database.connection import init_app, db
from database.models import Resource, Doctor
from flask import Flask

app = Flask(__name__)
init_app(app)

with app.app_context():
    # Seed Beds
    beds = [
        ("Lit-01", "Lit", True),
        ("Lit-02", "Lit", True),
        ("Lit-03", "Lit", True),
        ("Lit-04", "Lit", True),
        ("Lit-05", "Lit", True),
        ("Lit-06", "Lit", True),
        ("Lit-07", "Lit", True),
        ("Lit-08", "Lit", True),
        ("Lit-09", "Lit", True),
        ("Lit-10", "Lit", True),
    ]
    for nom, rtype, disponible in beds:
        existing = db.session.get(Resource, nom)
        if not existing:
            r = Resource(
                nom_ressource=nom,
                disponibilite=disponible,
                statut='disponible' if disponible else 'occupe',
                derniere_maj=db.func.now()
            )
            db.session.add(r)
    print("[OK] Beds seeded")

    # Seed Specialists
    specialists = [
        ("Dr. Martin Dubois", "cardiologie", True),
        ("Dr. Sophie Laurent", "cardiologie", True),
        ("Dr. Pierre Moreau", "neurologie", True),
        ("Dr. Isabelle Bernard", "neurologie", True),
        ("Dr. Jean-Luc Petit", "traumatologie", True),
        ("Dr. Catherine Roux", "traumatologie", True),
        ("Dr. Philippe Durand", "general", True),
        ("Dr. Marie Lefebvre", "general", True),
        ("Dr. Ayoub", "general", True),
        ("Dr. Hassin", "general", True),
    ]
    for nom, spec, disponible in specialists:
        existing = db.session.query(Doctor).filter(Doctor.nom == nom).first()
        if not existing:
            d = Doctor(
                nom=nom,
                specialite=spec,
                disponible=disponible,
                derniere_maj=db.func.now()
            )
            db.session.add(d)
    print("[OK] Specialists seeded")

    try:
        db.session.commit()
        print("[OK] All data committed successfully")
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] {e}")
        raise
