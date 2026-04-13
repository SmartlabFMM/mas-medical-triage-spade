# AI Multi-Agent Medical Triage System — PFE 2026

Système Multi-Agents Coopératif de Tri Médical (SMACTM)  
**Smart Lab FMM** | Architecture distribuée coopérative | Python 3.11+

---

## Installation

```bash
git clone <repo>
cd mas_medical_triage
pip install -r requirements.txt
cp .env.example .env      # puis ajuste les valeurs
```

## Lancement

```bash
# Scénario par défaut (3 patients)
python main.py

# Scénario de surcharge (10 patients critiques)
python main.py --scenario surcharge

# 20 patients aléatoires
python main.py --random 20
```

## Tests

```bash
pytest tests/ -v
pytest tests/test_integration.py -v    # tests d'intégration
```

## Architecture

```
mas_medical_triage/
├── agents/        # 4 agents spécialisés
│   ├── base_agent.py
│   ├── conversational_agent.py   # Dialogue structuré
│   ├── clinical_agent.py         # BDI
│   ├── resource_agent.py         # Goal-Based
│   └── meta_agent.py             # Coordination
├── core/          # Infrastructure MAS
│   ├── message.py                # Ontologie messages
│   ├── message_bus.py            # Bus async (asyncio)
│   ├── belief_base.py            # BDI BeliefBase
│   └── environment.py            # Cycle de vie agents
├── models/        # Structures de données Pydantic
├── utils/         # Logger, métriques, calculs
├── simulation/    # Simulateur + scénarios JSON
└── tests/         # Tests unitaires + intégration
```

## Exigences satisfaites

| ID | Exigence | Fichier |
|----|----------|---------|
| EF-CLI-01 | Score de gravité | `utils/severity_calculator.py` |
| EF-CLI-02 | BeliefBase BDI | `core/belief_base.py` |
| EF-META-04 | Décision traçable | `models/triage_decision.py` |
| ENF-PERF-01 | Cycle ≤ 5s | `config.py TRIAGE_TIMEOUT` |
| ENF-PERF-02 | 20 patients simultanés | `tests/test_integration.py` |
| ENF-PERF-03 | Async inter-agents | `core/message_bus.py` |
| ENF-FIAB-03 | Audit trail | `utils/logger.py` |
