"""
Tests du nouveau calculateur de score de gravité (v2.0)
"""
import sys
sys.path.insert(0, r'c:\Users\MSI\Downloads\mas_medical_triage_spade\mas_medical_triage')

from utils.severity_calculator import (
    compute_score, 
    severity_label, 
    get_recommended_action,
    INTENSITY_FACTORS,
    DURATION_FACTORS
)

def test_case_1_fever_headache():
    """Test: Patient 22 ans, Fièvre modérée + Maux de tête élevés"""
    print("\n" + "="*70)
    print("TEST 1: Patient 22 ans, conscient")
    print("Symptômes: Fièvre (modéré), Maux de tête (élevé), Durée: récente")
    print("="*70)
    
    symptoms = [
        {'name': 'fièvre', 'intensity': 2, 'duration': 'recente'},  # 15 × 2/3 × 1 = 10
        {'name': 'mal de tête', 'intensity': 3, 'duration': 'recente'},  # 12 × 1 × 1 = 12
    ]
    
    result = compute_score(symptoms, pain_level=0, age=22, is_conscious=True)
    
    print(f"\n📊 RÉSULTAT:")
    print(f"   Score brut: {result['raw_score']}")
    print(f"   Score final: {result['score']}")
    print(f"   Classification: {result['classification'].upper()}")
    print(f"   Action recommandée: {get_recommended_action(result['classification'])}")
    print(f"   Multiplicateur: {result['multiplier']}")
    print(f"\n📝 Détails par symptôme:")
    for detail in result['details']:
        print(f"   - {detail['name']}: {detail['base_weight']} × {detail['intensity_factor']:.2f} × {detail['duration_factor']:.1f} = {detail['score']}")
    
    # Vérification
    expected_score = (15 * 2/3 * 1.0) + (12 * 1.0 * 1.0)  # = 10 + 12 = 22
    assert result['score'] == expected_score, f"Score attendu: {expected_score}, obtenu: {result['score']}"
    assert result['classification'] == 'modéré', f"Classification attendue: modéré, obtenue: {result['classification']}"
    print(f"\n✅ TEST 1 RÉUSSI!")
    return result


def test_case_2_critical_unconscious():
    """Test: Cas critique - Perte de conscience"""
    print("\n" + "="*70)
    print("TEST 2: Cas CRITIQUE - Perte de conscience")
    print("Patient 45 ans + Perte de conscience + Douleur thoracique")
    print("="*70)
    
    symptoms = [
        {'name': 'perte de conscience', 'intensity': 3, 'duration': 'recente'},
        {'name': 'douleur thoracique', 'intensity': 3, 'duration': 'persistante'},
    ]
    
    result = compute_score(symptoms, pain_level=8, age=45, is_conscious=False)
    
    print(f"\n📊 RÉSULTAT:")
    print(f"   Score: {result['score']}")
    print(f"   Classification: {result['classification'].upper()}")
    print(f"   Cas critique: {result['is_critical']}")
    print(f"   Symptômes critiques: {result.get('critical_symptoms', [])}")
    print(f"   Message: {result.get('message', 'N/A')}")
    
    # Vérification - doit être court-circuité
    assert result['score'] == 100.0, f"Score attendu: 100, obtenu: {result['score']}"
    assert result['is_critical'] == True, f"is_critical attendu: True, obtenu: {result['is_critical']}"
    assert result['classification'] == 'critique', f"Classification attendue: critique, obtenue: {result['classification']}"
    print(f"\n✅ TEST 2 RÉUSSI! (Court-circuit critique)")
    return result


def test_case_3_high_fever_critical():
    """Test: Fièvre très élevée > 40°C (critique)"""
    print("\n" + "="*70)
    print("TEST 3: Cas CRITIQUE - Fièvre > 40°C")
    print("Patient 30 ans, Fièvre 40.5°C")
    print("="*70)
    
    symptoms = [
        {'name': 'fièvre', 'intensity': 3, 'duration': 'persistante'},
    ]
    
    result = compute_score(symptoms, pain_level=3, age=30, is_conscious=True, temperature=40.5)
    
    print(f"\n📊 RÉSULTAT:")
    print(f"   Score: {result['score']}")
    print(f"   Classification: {result['classification'].upper()}")
    print(f"   Cas critique: {result['is_critical']}")
    print(f"   Symptômes critiques: {result.get('critical_symptoms', [])}")
    
    assert result['score'] == 100.0, f"Score attendu: 100, obtenu: {result['score']}"
    assert result['is_critical'] == True, f"is_critical attendu: True, obtenu: {result['is_critical']}"
    print(f"\n✅ TEST 3 RÉUSSI! (Fièvre critique)")
    return result


def test_case_4_urgent_case():
    """Test: Cas urgent avec multiplicateur"""
    print("\n" + "="*70)
    print("TEST 4: Cas URGENT - Vomissements persistants")
    print("Patient 35 ans, Traumatisme + Vomissements persistants")
    print("="*70)
    
    symptoms = [
        {'name': 'traumatisme', 'intensity': 2, 'duration': 'recente'},  # Urgent
        {'name': 'vomissements persistants', 'intensity': 3, 'duration': 'persistante'},  # Urgent
    ]
    
    result = compute_score(symptoms, pain_level=6, age=35, is_conscious=True)
    
    print(f"\n📊 RÉSULTAT:")
    print(f"   Score brut: {result['raw_score']}")
    print(f"   Score final: {result['score']}")
    print(f"   Classification: {result['classification'].upper()}")
    print(f"   Cas urgent: {result['is_urgent']}")
    print(f"   Multiplicateur: {result['multiplier']} (×1.3 pour cas urgent)")
    
    # Vérification
    # Trauma: 32 × 2/3 × 1.0 = 21.33
    # Vomissements: 18 × 1.0 × 1.2 = 21.6
    # Sous-total: 42.93 × 1.3 (urgent) = 55.81
    # Douleur: 6 × 1.5 = 9
    # Total: 64.81
    assert result['is_urgent'] == True, f"is_urgent attendu: True, obtenu: {result['is_urgent']}"
    assert result['multiplier'] == 1.3, f"Multiplicateur attendu: 1.3, obtenu: {result['multiplier']}"
    assert result['score'] > 50, f"Score attendu > 50 (Urgent), obtenu: {result['score']}"
    print(f"\n✅ TEST 4 RÉUSSI! (Multiplicateur urgent appliqué)")
    return result


def test_case_5_elderly_risk():
    """Test: Patient âgé avec multiplicateur âge"""
    print("\n" + "="*70)
    print("TEST 5: Patient ÂGÉ (75 ans) - Facteur de risque")
    print("Symptômes: Douleur abdominale (modérée), Fièvre (faible)")
    print("="*70)
    
    symptoms = [
        {'name': 'douleur abdominale', 'intensity': 2, 'duration': 'persistante'},
        {'name': 'fièvre', 'intensity': 1, 'duration': 'recente'},
    ]
    
    result = compute_score(symptoms, pain_level=4, age=75, is_conscious=True)
    
    print(f"\n📊 RÉSULTAT:")
    print(f"   Score brut: {result['raw_score']}")
    print(f"   Score final: {result['score']}")
    print(f"   Classification: {result['classification'].upper()}")
    print(f"   Multiplicateur: {result['multiplier']} (×1.2 pour âge > 70)")
    
    # Vérification
    # Douleur abdom: 28 × 2/3 × 1.2 = 22.4
    # Fièvre: 15 × 1/3 × 1.0 = 5
    # Sous-total: 27.4 × 1.2 (âge) = 32.88
    # Douleur: 4 × 1.5 = 6
    # Total: 38.88
    assert result['multiplier'] == 1.2, f"Multiplicateur attendu: 1.2, obtenu: {result['multiplier']}"
    assert result['score'] > 35, f"Score attendu > 35, obtenu: {result['score']}"
    print(f"\n✅ TEST 5 RÉUSSI! (Multiplicateur âge appliqué)")
    return result


def test_case_6_child_unconscious():
    """Test: Enfant inconscient - Multiplicateurs combinés"""
    print("\n" + "="*70)
    print("TEST 6: ENFANT (3 ans) INCONSCIENT - Multiplicateurs combinés")
    print("Symptômes: Trauma crânien (élevé), fièvre (modérée)")
    print("="*70)
    
    symptoms = [
        {'name': 'trauma crânien', 'intensity': 3, 'duration': 'recente'},
        {'name': 'fièvre', 'intensity': 2, 'duration': 'recente'},
    ]
    
    result = compute_score(symptoms, pain_level=5, age=3, is_conscious=False)
    
    print(f"\n📊 RÉSULTAT:")
    print(f"   Score brut: {result['raw_score']}")
    print(f"   Score final: {result['score']}")
    print(f"   Classification: {result['classification'].upper()}")
    print(f"   Multiplicateur: {result['multiplier']} (×1.2 âge × 1.5 inconscience = 1.8)")
    
    # Vérification
    # Multiplicateur attendu: 1.2 × 1.5 = 1.8
    assert result['multiplier'] == 1.8, f"Multiplicateur attendu: 1.8, obtenu: {result['multiplier']}"
    assert result['score'] > 60, f"Score attendu > 60 (Urgent/Critique), obtenu: {result['score']}"
    print(f"\n✅ TEST 6 RÉUSSI! (Multiplicateurs combinés)")
    return result


def test_case_7_light_case():
    """Test: Cas léger"""
    print("\n" + "="*70)
    print("TEST 7: Cas LÉGER - Adulte 40 ans")
    print("Symptômes: Toux (faible), Nausée (faible)")
    print("="*70)
    
    symptoms = [
        {'name': 'toux', 'intensity': 1, 'duration': 'recente'},
        {'name': 'nausée', 'intensity': 1, 'duration': 'recente'},
    ]
    
    result = compute_score(symptoms, pain_level=1, age=40, is_conscious=True)
    
    print(f"\n📊 RÉSULTAT:")
    print(f"   Score brut: {result['raw_score']}")
    print(f"   Score final: {result['score']}")
    print(f"   Classification: {result['classification'].upper()}")
    print(f"   Action: {get_recommended_action(result['classification'])}")
    
    # Vérification
    # Toux: 5 × 1/3 × 1.0 = 1.67
    # Nausée: 10 × 1/3 × 1.0 = 3.33
    # Sous-total: 5.0 × 1.0 (pas de multiplicateur) = 5.0
    # Douleur: 1 × 1.5 = 1.5
    # Total: 6.5
    assert result['classification'] == 'léger', f"Classification attendue: léger, obtenue: {result['classification']}"
    assert result['score'] < 25, f"Score attendu < 25, obtenu: {result['score']}"
    print(f"\n✅ TEST 7 RÉUSSI! (Cas léger identifié)")
    return result


def test_case_8_duration_parsing():
    """Test: Parsing des durées"""
    print("\n" + "="*70)
    print("TEST 8: Test du parsing des durées")
    print("="*70)
    
    from utils.severity_calculator import _parse_duration
    
    test_cases = [
        ('recente', 1.0),
        ('persistante', 1.2),
        ('chronique', 1.5),
        ('2h', 1.0),      # < 24h
        ('12h', 1.0),     # < 24h
        ('1j', 1.0),      # < 24h
        ('2j', 1.2),      # 48h = persistante
        ('5j', 1.2),      # 120h = persistante
        ('1s', 1.2),      # 7j = persistante (limite)
        ('2s', 1.5),      # 14j = chronique
        ('1m', 1.5),      # 30j = chronique
        ('', 1.0),        # vide = défaut
    ]
    
    print("\n📊 RÉSULTATS DU PARSING:")
    for duration, expected in test_cases:
        result = _parse_duration(duration)
        status = "✅" if result == expected else "❌"
        print(f"   {status} '{duration}' → {result:.1f} (attendu: {expected})")
        assert result == expected, f"Erreur parsing '{duration}': {result} != {expected}"
    
    print(f"\n✅ TEST 8 RÉUSSI! (Tous les parsings corrects)")


def run_all_tests():
    """Exécute tous les tests"""
    print("\n" + "🧪"*35)
    print("   TESTS DU NOUVEAU CALCULATEUR DE SEVERITY (v2.0)")
    print("🧪"*35)
    
    try:
        test_case_1_fever_headache()
        test_case_2_critical_unconscious()
        test_case_3_high_fever_critical()
        test_case_4_urgent_case()
        test_case_5_elderly_risk()
        test_case_6_child_unconscious()
        test_case_7_light_case()
        test_case_8_duration_parsing()
        
        print("\n" + "="*70)
        print("🎉 TOUS LES TESTS ONT RÉUSSI! (8/8)")
        print("="*70)
        print("\n✅ Le nouveau calculateur fonctionne correctement!")
        print("\nPoints clés validés:")
        print("   • Calcul par symptôme: Poids × Intensité × Durée")
        print("   • Court-circuit pour cas critiques")
        print("   • Multiplicateur 1.3 pour cas urgents")
        print("   • Multiplicateur 1.2 pour âge à risque")
        print("   • Multiplicateur 1.5 pour inconscience")
        print("   • Multiplicateurs combinés (âge + inconscience)")
        print("   • Nouveaux seuils: 0-25/26-50/51-75/76-100")
        
    except AssertionError as e:
        print(f"\n❌ TEST ÉCHOUÉ: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERREUR INATTENDUE: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
