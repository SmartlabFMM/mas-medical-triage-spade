"""
models/patient.py — Modèle de données d'un patient.
Structure Pydantic : validation automatique des champs.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class Patient(BaseModel):
    """Représente un patient arrivant aux urgences."""

    id: str = Field(..., description="Identifiant unique UUID")
    name: str = Field(..., min_length=2, max_length=100, description="Nom complet du patient")
    age: int = Field(..., ge=0, le=150, description="Âge du patient en années")
    gender: str = Field(..., pattern="^(M|F|autre)$", description="Genre du patient")
    symptoms: list[str] = Field(..., min_items=1, description="Liste des symptômes (minimum 1)")
    arrival_time: datetime = Field(default_factory=datetime.now, description="Heure d'arrivée")
    is_conscious: bool = Field(default=True, description="État de conscience")
    pain_level: int = Field(default=0, ge=0, le=10, description="Niveau de douleur (0-10)")
    
    # Champs médicaux additionnels pour meilleure validation
    blood_pressure: Optional[str] = Field(None, pattern=r"^(\d{2,3})/(\d{2,3})$", description="Pression artérielle (ex: 120/80)")
    heart_rate: Optional[int] = Field(None, ge=30, le=200, description="Fréquence cardiaque (bpm)")
    temperature: Optional[float] = Field(None, ge=35.0, le=42.0, description="Température corporelle (°C)")
    oxygen_saturation: Optional[float] = Field(None, ge=70.0, le=100.0, description="Saturation en oxygène (%)")

    @field_validator("symptoms")
    @classmethod
    def validate_symptoms(cls, v: list[str]) -> list[str]:
        """Validation des symptômes avec nettoyage."""
        if not v:
            raise ValueError("La liste de symptômes ne peut pas être vide.")
        
        # Nettoyage et validation
        cleaned_symptoms = []
        for symptom in v:
            if isinstance(symptom, str):
                symptom = symptom.strip()
                if symptom and len(symptom) >= 2:
                    cleaned_symptoms.append(symptom)
        
        if not cleaned_symptoms:
            raise ValueError("Aucun symptôme valide trouvé après nettoyage.")
        
        return cleaned_symptoms
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validation du nom du patient."""
        if not v or len(v.strip()) < 2:
            raise ValueError("Le nom doit contenir au moins 2 caractères.")
        
        # Nettoyage du nom
        return v.strip().title()
    
    def get_age_category(self) -> str:
        """Retourne la catégorie d'âge pour évaluation médicale."""
        if self.age < 1:
            return "nouveau-né"
        elif self.age < 5:
            return "nourrisson"
        elif self.age < 12:
            return "enfant"
        elif self.age < 18:
            return "adolescent"
        elif self.age < 65:
            return "adulte"
        else:
            return "personne âgée"
    
    def has_vital_signs(self) -> bool:
        """Vérifie si les signes vitaux sont disponibles."""
        return all([
            self.blood_pressure is not None,
            self.heart_rate is not None,
            self.temperature is not None,
            self.oxygen_saturation is not None
        ])
    
    def is_critical_vital_signs(self) -> bool:
        """Vérifie si les signes vitaux indiquent un état critique."""
        if not self.has_vital_signs():
            return False
        
        # Critères de criticité basés sur les signes vitaux
        systolic = int(self.blood_pressure.split('/')[0]) if self.blood_pressure else 0
        diastolic = int(self.blood_pressure.split('/')[1]) if self.blood_pressure else 0
        
        return (
            systolic < 90 or systolic > 180 or  # Hypotension/Hypertension sévère
            diastolic > 120 or  # Hypertension diastolique sévère
            self.heart_rate < 40 or self.heart_rate > 150 or  # Bradycardie/Tachycardie
            self.temperature < 35.0 or self.temperature > 40.5 or  # Hypothermie/Hyperthermie
            self.oxygen_saturation < 90  # Hypoxie
        )

    def summary(self) -> str:
        return (
            f"Patient {self.name} ({self.age} ans) — "
            f"Symptômes: {', '.join(self.symptoms)} — "
            f"Douleur: {self.pain_level}/10"
        )
