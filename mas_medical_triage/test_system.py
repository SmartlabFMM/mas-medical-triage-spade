#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '.')

print('='*60)
print('TEST 1: API Flask')
print('='*60)

try:
    from api.app import app, SHEETS_AVAILABLE
    print('[OK] API Flask importee')
    print(f'     SHEETS_AVAILABLE: {SHEETS_AVAILABLE}')
except Exception as e:
    print(f'[ERREUR] API: {e}')

print()
print('='*60)
print('TEST 2: ConversationalAgent')
print('='*60)

try:
    from agents.conversational_agent import ConversationalAgent
    import inspect
    source = inspect.getsource(ConversationalAgent)
    
    llm_count = source.count('LLMEngine')
    chat_count = source.count('chat_queue')
    
    print(f'[OK] ConversationalAgent importe')
    print(f'     LLMEngine refs: {llm_count}')
    print(f'     chat_queue refs: {chat_count}')
    
    if llm_count == 0 and chat_count == 0:
        print('[OK] LLM/Chat supprime')
    else:
        print('[WARN] References encore presentes')
        
except Exception as e:
    print(f'[ERREUR] ConversationalAgent: {e}')

print()
print('='*60)
print('TEST 3: Severity Calculator')
print('='*60)

try:
    from utils.severity_calculator import compute_score, severity_label
    
    score1 = compute_score(['headache'], pain_level=5, age=35)
    label1 = severity_label(score1)
    print(f'[OK] Test headache: {score1}/100 ({label1})')
    
    score2 = compute_score(['avc'], pain_level=10, age=75, is_conscious=False)
    label2 = severity_label(score2)
    print(f'[OK] Test AVC: {score2}/100 ({label2})')
    
except Exception as e:
    print(f'[ERREUR] Severity: {e}')

print()
print('='*60)
print('TEST 4: Frontend chat.tsx')
print('='*60)

chat_file = 'interface/src/pages/chat.tsx'
if os.path.exists(chat_file):
    print(f'[ERREUR] chat.tsx existe encore')
else:
    print(f'[OK] chat.tsx supprime')

print()
print('='*60)
print('TEST 5: PatientPage.tsx')
print('='*60)

patient_page = 'interface/src/pages/PatientPage.tsx'
if os.path.exists(patient_page):
    with open(patient_page, 'r', encoding='utf-8') as f:
        content = f.read()
    
    chat_wizard = content.count('ChatWizard')
    postchat = content.count('postChat')
    
    print(f'[OK] PatientPage.tsx analyse')
    print(f'     ChatWizard: {chat_wizard}')
    print(f'     postChat: {postchat}')
    
    if chat_wizard == 0 and postchat == 0:
        print('[OK] Chat supprime de PatientPage')
    else:
        print('[WARN] Chat encore present')
else:
    print(f'[ERREUR] PatientPage.tsx introuvable')

print()
print('='*60)
print('RESUME')
print('='*60)
print('Systeme operationnel sans chat LLM!')
print('='*60)
