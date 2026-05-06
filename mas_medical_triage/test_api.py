#!/usr/bin/env python3
"""Test direct de l'API."""

import urllib.request
import json

url = "http://127.0.0.1:5000/symptoms"

data = {
    "age": 22,
    "gender": "M",
    "symptoms": ["fievre_elevee", "mal_de_tete"],
    "pain_level": 0,
    "conscious": True,
    "symptoms_details": [
        {"name": "Fièvre élevée", "intensity": 2, "duration": "recente"},
        {"name": "Mal de tête", "intensity": 3, "duration": "recente"}
    ]
}

try:
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=10) as response:
        result = json.loads(response.read().decode())
        print(f"\nScore brut: {result.get('severity_score')}")
        print(f"Décision: {result.get('decision')}")
        print(f"Explication: {result.get('explanation')}")
        
        if 'severity_result' in result:
            print(f"\nDétails complets:")
            print(json.dumps(result['severity_result'], indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Erreur: {e}")
