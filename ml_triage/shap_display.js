/**
 * shap_display.js — Affichage des résultats ML + SHAP dans le frontend
 *
 * À intégrer dans script.js (fonction submitTriage existante).
 * Remplace ou complète la section "showDecisionResult".
 *
 * Dépendance Chart.js déjà présente dans index.html.
 */

/* ══════════════════════════════════════════════════════
   FONCTION PRINCIPALE : Soumet les symptômes + affiche SHAP
══════════════════════════════════════════════════════ */

async function submitTriage() {
  const symptoms   = [...AppState.patient.symptoms];
  const custom     = document.getElementById('custom-symptom')?.value?.trim();
  if (custom) symptoms.push(custom);

  if (!symptoms.length) {
    showToast('Attention', 'Sélectionnez au moins un symptôme.', 'warning');
    return;
  }

  const btn = document.getElementById('btn-submit');
  if (btn) { btn.disabled = true; btn.textContent = 'Analyse ML en cours...'; }

  const payload = {
    name:       AppState.username,
    age:        parseInt(document.getElementById('patient-age')?.value) || 35,
    gender:     document.getElementById('patient-gender')?.value || 'M',
    conscious:  document.getElementById('patient-conscious')?.value === 'true',
    symptoms,
    pain_level: AppState.patient.pain,
  };

  try {
    const res  = await fetch('http://localhost:5000/symptoms', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });
    const data = await res.json();

    if (data.status === 'ok') {
      AppState.patient.id = data.patient_id;
      showMLResult(data);
      showToast('Analyse terminée', `Score IA : ${data.severity_score}/100`, 'success');

      // Passe au tab statut
      const statusBtn = document.getElementById('ptab-status');
      switchPatientTab('status', statusBtn);
    } else {
      throw new Error(data.message || 'Erreur API');
    }
  } catch (err) {
    console.warn('API indisponible, simulation locale:', err);
    // Mode simulation si API non disponible
    simulateMLResult(symptoms, AppState.patient.pain);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '⬤ Soumettre au système MAS';
    }
  }
}


/* ══════════════════════════════════════════════════════
   AFFICHAGE RÉSULTAT ML + SHAP
══════════════════════════════════════════════════════ */

/**
 * Affiche le résultat complet : score, décision, graphique SHAP.
 *
 * @param {Object} data - Réponse de POST /symptoms
 * {
 *   severity_score: 78.4,
 *   decision: { action, label, color, instructions },
 *   explanation: [{ symptom, impact, present }],
 *   symptoms_found: [...],
 *   symptoms_unknown: [...],
 *   model_confidence: "élevée"
 * }
 */
function showMLResult(data) {
  const score      = data.severity_score || 0;
  const decision   = data.decision || {};
  const explanation= data.explanation || [];
  const confidence = data.model_confidence || '?';
  const unknown    = data.symptoms_unknown || [];

  // ── Conteneur principal (dans tab-status) ─────────────────────────────────
  const container = document.getElementById('patient-tracking-timeline');
  if (!container) return;

  const scorePct = score;
  const scoreColor = score >= 70 ? '#dc2626' : score >= 40 ? '#d97706' : '#059669';
  const urgencyIcon = score >= 70 ? '🚨' : score >= 40 ? '⚠️' : '✅';

  container.innerHTML = `
    <!-- ── Score de gravité ── -->
    <div class="ml-result-card">

      <div class="ml-score-section">
        <div class="ml-score-gauge">
          <svg width="120" height="120" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="50" fill="none" stroke="#e2e8f0" stroke-width="10"/>
            <circle cx="60" cy="60" r="50" fill="none"
              stroke="${scoreColor}" stroke-width="10"
              stroke-dasharray="${2 * Math.PI * 50}"
              stroke-dashoffset="${2 * Math.PI * 50 * (1 - scorePct / 100)}"
              stroke-linecap="round"
              transform="rotate(-90 60 60)"
              style="transition: stroke-dashoffset 1s ease"/>
            <text x="60" y="55" text-anchor="middle" fill="${scoreColor}"
              style="font-size:22px;font-weight:700;font-family:JetBrains Mono">${score.toFixed(0)}</text>
            <text x="60" y="72" text-anchor="middle" fill="#94a3b8"
              style="font-size:10px">/100</text>
          </svg>
        </div>

        <div class="ml-score-info">
          <div class="ml-urgency-badge" style="background:${scoreColor}20;color:${scoreColor};
            border:1px solid ${scoreColor}40;border-radius:8px;padding:6px 14px;
            font-weight:700;font-size:13px;display:inline-block;margin-bottom:8px">
            ${urgencyIcon} ${decision.label || decision.action?.toUpperCase() || '?'}
          </div>
          <div style="font-size:13px;color:#64748b;line-height:1.5">
            ${decision.instructions || ''}
          </div>
          <div style="margin-top:8px;font-size:11px;color:#94a3b8">
            Confiance du modèle : <strong>${confidence}</strong>
          </div>
        </div>
      </div>

      <!-- ── Graphique SHAP ── -->
      ${explanation.length > 0 ? `
        <div class="ml-shap-section">
          <h4 class="ml-section-title">
            🔍 Facteurs déterminants — Analyse SHAP
            <span style="font-size:10px;font-weight:400;color:#94a3b8">
              (impact sur le score de gravité)
            </span>
          </h4>
          <div class="ml-shap-chart-wrap">
            <canvas id="shap-chart" height="200"></canvas>
          </div>

          <!-- Liste des symptômes critiques -->
          <div class="ml-factors-list">
            ${explanation.map(f => `
              <div class="ml-factor-row">
                <div class="ml-factor-name ${f.present ? 'present' : 'absent'}">
                  ${f.present ? '●' : '○'} ${f.symptom}
                </div>
                <div class="ml-factor-bar-wrap">
                  <div class="ml-factor-bar"
                    style="width:${Math.min(Math.abs(f.impact), 50) * 2}%;
                           background:${f.impact > 0 ? '#ef4444' : '#22c55e'};
                           height:6px;border-radius:3px;transition:width .6s ease">
                  </div>
                </div>
                <div class="ml-factor-impact" style="color:${f.impact > 0 ? '#ef4444' : '#22c55e'}">
                  ${f.impact > 0 ? '+' : ''}${f.impact.toFixed(1)}
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      <!-- Symptômes inconnus -->
      ${unknown.length > 0 ? `
        <div style="margin-top:12px;padding:8px 12px;background:#fff7ed;
          border:1px solid #fed7aa;border-radius:6px;font-size:12px;color:#c2410c">
          ⚠️ Symptômes non reconnus par le modèle : ${unknown.join(', ')}
        </div>
      ` : ''}
    </div>
  `;

  // ── Dessin du graphique Chart.js ──────────────────────────────────────────
  if (explanation.length > 0) {
    setTimeout(() => renderSHAPChart(explanation), 100);
  }

  // ── Mise à jour badge statut ───────────────────────────────────────────────
  const badge = document.getElementById('current-patient-status');
  if (badge) {
    badge.textContent = 'Analyse IA terminée';
    badge.style.background = scoreColor + '20';
    badge.style.color = scoreColor;
  }
}


/* ══════════════════════════════════════════════════════
   GRAPHIQUE SHAP — Chart.js
══════════════════════════════════════════════════════ */

let _shapChart = null;

function renderSHAPChart(explanation) {
  const canvas = document.getElementById('shap-chart');
  if (!canvas || typeof Chart === 'undefined') return;

  if (_shapChart) {
    _shapChart.destroy();
    _shapChart = null;
  }

  const isDark  = document.documentElement.getAttribute('data-theme') === 'dark';
  const gridClr = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)';
  const txtClr  = isDark ? '#94a3b8' : '#64748b';

  // Trie par impact décroissant pour le graphique horizontal
  const sorted  = [...explanation].sort((a, b) => b.impact - a.impact);
  const labels  = sorted.map(f => f.symptom);
  const impacts = sorted.map(f => f.impact);
  const colors  = impacts.map(v => v > 0 ? 'rgba(239,68,68,0.8)' : 'rgba(34,197,94,0.8)');
  const borders = impacts.map(v => v > 0 ? 'rgba(220,38,38,1)' : 'rgba(22,163,74,1)');

  _shapChart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label:           'Impact SHAP',
        data:            impacts,
        backgroundColor: colors,
        borderColor:     borders,
        borderWidth:     1.5,
        borderRadius:    4,
        borderSkipped:   false,
      }]
    },
    options: {
      indexAxis:    'y',        // Graphique horizontal
      responsive:   true,
      maintainAspectRatio: false,
      animation:    { duration: 800, easing: 'easeOutQuart' },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => {
              const v = ctx.raw;
              return ` ${v > 0 ? '+' : ''}${v.toFixed(2)} points sur le score`;
            }
          }
        }
      },
      scales: {
        x: {
          grid:  { color: gridClr },
          ticks: { color: txtClr },
          title: {
            display: true, text: 'Impact sur le score de gravité',
            color: txtClr, font: { size: 11 }
          }
        },
        y: {
          grid:  { display: false },
          ticks: { color: txtClr, font: { size: 11 } },
        }
      }
    }
  });
}


/* ══════════════════════════════════════════════════════
   MODE SIMULATION (sans backend)
══════════════════════════════════════════════════════ */

function simulateMLResult(symptoms, painLevel) {
  // Calcul approximatif côté client (règles métier)
  const weights = {
    'chest_pain': 35, 'douleur thoracique': 35,
    'shortness_of_breath': 30, 'difficulté respiratoire': 30,
    'loss_of_consciousness': 40, 'perte de conscience': 40,
    'seizures': 38, 'convulsions': 38,
    'bleeding': 35, 'hémorragie': 35,
    'fever': 12, 'fièvre': 12, 'high_fever': 22, 'fièvre élevée': 22,
    'cough': 8, 'toux': 8,
    'nausea': 7, 'nausée': 7,
    'headache': 8, 'mal de tête': 8,
  };

  let score = painLevel * 2.5;
  const norm = symptoms.map(s => s.toLowerCase().trim());
  norm.forEach(s => { score += weights[s] || 6; });
  score = Math.min(Math.round(score), 100);

  const decision = score >= 70
    ? { action: 'hospitaliser', label: 'HOSPITALISATION IMMÉDIATE', color: '#dc2626',
        instructions: 'Prise en charge immédiate requise.' }
    : score >= 40
    ? { action: 'surveiller', label: 'SURVEILLANCE MÉDICALE', color: '#d97706',
        instructions: 'Mise en observation — réévaluation dans 30 min.' }
    : { action: 'retour_domicile', label: 'RETOUR À DOMICILE', color: '#059669',
        instructions: 'Traitement symptomatique. Consulter si aggravation.' };

  const explanation = norm.slice(0, 5).map(s => ({
    symptom: s,
    impact:  weights[s] || 6,
    present: true,
  })).sort((a, b) => b.impact - a.impact);

  showMLResult({
    severity_score:    score,
    decision,
    explanation,
    symptoms_found:    norm,
    symptoms_unknown:  [],
    model_confidence:  'simulation locale',
  });

  AppState.patient.id = 'SIM-' + Math.random().toString(36).slice(2, 8).toUpperCase();
  showToast('Mode simulation', `Score estimé : ${score}/100`, 'info');
}


/* ══════════════════════════════════════════════════════
   CSS À AJOUTER DANS style.css
══════════════════════════════════════════════════════ */

/*
.ml-result-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.5rem;
  animation: fadeIn .4s ease;
}

.ml-score-section {
  display: flex;
  align-items: flex-start;
  gap: 1.5rem;
  margin-bottom: 1.25rem;
}

.ml-score-gauge { flex-shrink: 0; }

.ml-score-info { flex: 1; padding-top: .5rem; }

.ml-shap-section { margin-top: 1.25rem; padding-top: 1.25rem; border-top: 1px solid var(--border); }

.ml-section-title {
  font-size: .85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .5px;
  color: var(--text-dimmed);
  margin-bottom: 1rem;
}

.ml-shap-chart-wrap { height: 200px; margin-bottom: 1rem; }

.ml-factors-list { display: flex; flex-direction: column; gap: .5rem; }

.ml-factor-row {
  display: flex;
  align-items: center;
  gap: .75rem;
  font-size: .85rem;
}

.ml-factor-name { min-width: 160px; font-weight: 500; }
.ml-factor-name.absent { color: var(--text-dimmed); font-style: italic; }
.ml-factor-name.present { color: var(--text-main); }

.ml-factor-bar-wrap { flex: 1; background: var(--bg-inset); border-radius: 3px; height: 6px; overflow: hidden; }

.ml-factor-impact {
  min-width: 48px;
  text-align: right;
  font-family: 'JetBrains Mono', monospace;
  font-size: .8rem;
  font-weight: 600;
}
*/
