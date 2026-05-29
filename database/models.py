from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from .connection import db


class Patient(db.Model):
    __tablename__ = 'patients'
    patient_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    nom = db.Column(db.String(255))
    age = db.Column(db.Integer)
    genre = db.Column(db.String(50))
    symptomes = db.Column(db.JSON)
    symptoms_details = db.Column(db.Text)
    score_gravite = db.Column(db.Float, nullable=True)
    action_finale = db.Column(db.String(500))
    heure_arrivee = db.Column(db.DateTime)
    statut = db.Column(db.String(100), index=True)
    specialite_assignee = db.Column(db.String(255))
    medecin_assigne = db.Column(db.String(255))
    lit_assigne = db.Column(db.String(255))
    mode_affectation = db.Column(db.String(100))

    decisions = db.relationship('Decision', backref='patient', lazy=True)


    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Decision(db.Model):
    __tablename__ = 'decisions'
    decision_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    patient_id = db.Column(UUID(as_uuid=True), db.ForeignKey('patients.patient_id'), index=True)
    score_gravite = db.Column(db.Float, nullable=True)
    action = db.Column(db.String(500))
    raisonnement = db.Column(db.Text)
    nb_cycles = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    agent_decideur = db.Column(db.String(255))


    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Resource(db.Model):
    __tablename__ = 'resources'
    nom_ressource = db.Column(db.String(255), primary_key=True)
    disponibilite = db.Column(db.Boolean, default=True)
    charge_percent = db.Column(db.Float)
    patient_assigne = db.Column(db.String(255))
    statut = db.Column(db.String(100))
    derniere_maj = db.Column(db.DateTime, default=datetime.utcnow)


    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Log(db.Model):
    __tablename__ = 'logs'
    log_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    agent = db.Column(db.String(255))
    action = db.Column(db.String(255))
    details = db.Column(db.Text)
    patient_id = db.Column(UUID(as_uuid=True), db.ForeignKey('patients.patient_id'), index=True)
    niveau = db.Column(db.String(50))


    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Doctor(db.Model):
    __tablename__ = 'doctors'
    doctor_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    nom = db.Column(db.String(255), index=True)
    specialite = db.Column(db.String(255))
    disponible = db.Column(db.Boolean, default=True)
    patient_assigne = db.Column(db.Text)
    derniere_maj = db.Column(db.DateTime, default=datetime.utcnow)


    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = db.Column(db.String(255), unique=True, index=True)
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)


    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class ArchivedPatient(db.Model):
    __tablename__ = 'archived_patients'
    patient_id = db.Column(UUID(as_uuid=True), primary_key=True, index=True)
    nom = db.Column(db.String(255))
    age = db.Column(db.Integer)
    genre = db.Column(db.String(50))
    symptomes = db.Column(db.JSON)
    symptoms_details = db.Column(db.Text)
    score_gravite = db.Column(db.Float, nullable=True)
    action_finale = db.Column(db.String(500))
    heure_arrivee = db.Column(db.DateTime)
    statut = db.Column(db.String(100), index=True)
    specialite_assignee = db.Column(db.String(255))
    medecin_assigne = db.Column(db.String(255))
    lit_assigne = db.Column(db.String(255))
    mode_affectation = db.Column(db.String(100))
    archived_at = db.Column(db.DateTime, default=datetime.utcnow)
    archived_reason = db.Column(db.Text)


    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}





