from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

Base = declarative_base()

class Patient(Base):
    __tablename__ = 'patients'
    patient_id = Column(String, primary_key=True)
    nom = Column(String)
    age = Column(String)
    genre = Column(String)
    symptomes = Column(Text)
    symptoms_details = Column(Text)
    score_gravite = Column(Float, default=0.0)
    action_finale = Column(String)
    heure_arrivee = Column(String)
    statut = Column(String, default='en_attente')
    pain_level = Column(Integer, default=0)
    specialite_assignee = Column(String)
    medecin_assigne = Column(String)
    lit_assigne = Column(String)
    mode_affectation = Column(String)

class Resource(Base):
    __tablename__ = 'resources'
    nom_ressource = Column(String, primary_key=True)
    disponibilite = Column(Boolean, default=True)
    charge_percent = Column(Integer, default=0)
    patient_assigne = Column(String)
    statut = Column(String, default='disponible')
    derniere_maj = Column(String)

class Decision(Base):
    __tablename__ = 'decisions'
    decision_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4())[:8])
    patient_id = Column(String)
    score_gravite = Column(Float)
    action = Column(String)
    raisonnement = Column(Text)
    nb_cycles = Column(Integer, default=1)
    timestamp = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    agent_decideur = Column(String)

class Log(Base):
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    agent = Column(String)
    action = Column(String)
    details = Column(Text)
    patient_id = Column(String)
    niveau = Column(String, default='INFO')

class Doctor(Base):
    __tablename__ = 'doctors'
    doctor_id = Column(String, primary_key=True)
    nom = Column(String)
    specialite = Column(String)
    disponible = Column(Boolean, default=True)
    patient_assigne = Column(String) # Comma separated IDs
    derniere_maj = Column(String)

class User(Base):
    __tablename__ = 'users'
    user_id = Column(String, primary_key=True)
    username = Column(String, unique=True)
    password_hash = Column(String)
    role = Column(String)
    created_at = Column(String)
    active = Column(Boolean, default=True)

class ArchivedPatient(Base):
    __tablename__ = 'archived_patients'
    patient_id = Column(String, primary_key=True)
    nom = Column(String)
    age = Column(String)
    genre = Column(String)
    symptomes = Column(Text)
    symptoms_details = Column(Text)
    score_gravite = Column(Float)
    action_finale = Column(String)
    heure_arrivee = Column(String)
    statut = Column(String)
    pain_level = Column(Integer)
    specialite_assignee = Column(String)
    medecin_assigne = Column(String)
    lit_assigne = Column(String)
    mode_affectation = Column(String)
    archived_at = Column(String)
    archived_reason = Column(String)
