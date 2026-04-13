"""
core/llm_engine.py - LLM Engine for intelligent medical triage dialogue.

Integrates OpenAI GPT to:
  1. Analyze free-text patient input
  2. Extract structured clinical data
  3. Generate context-aware follow-up questions

Usage:
    from core.llm_engine import analyze_patient_input, LLMEngine

    engine = LLMEngine()
    result = engine.analyze(
        message="I have chest pain and feel dizzy",
        history=[]  # list of {"role": "user"/"assistant", "content": "..."}
    )
"""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def _parse_json_from_text(raw_text: str) -> dict:
    """
    Parse JSON robustly from model output.
    Handles plain JSON, fenced blocks, and extra text before/after JSON.
    """
    text = (raw_text or "").strip()
    if not text:
        raise json.JSONDecodeError("Empty model response", "", 0)

    if text.startswith("```"):
        lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start_candidates = [i for i in (text.find("{"), text.find("[")) if i >= 0]
    if not start_candidates:
        raise json.JSONDecodeError("No JSON object/array found in model response", text, 0)
    start = min(start_candidates)

    end_candidates = [i for i in (text.rfind("}"), text.rfind("]")) if i >= 0]
    if not end_candidates:
        raise json.JSONDecodeError("No JSON object/array end found in model response", text, 0)
    end = max(end_candidates) + 1

    json_text = text[start:end]
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Failed to parse extracted JSON: {e}", json_text, 0)


# OpenAI client
_openai_available = False
_openai_client = None

try:
    from openai import OpenAI
    _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    _openai_available = True
    logger.info("OpenAI client initialized")
except ImportError:
    logger.warning("OpenAI package not installed")
except Exception as e:
    logger.warning(f"OpenAI client initialization failed: {e}")

# Groq client
_groq_available = False
_groq_client = None

try:
    from groq import Groq
    _groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    _groq_available = True
    logger.info("Groq client initialized")
except ImportError:
    logger.warning("Groq package not installed")
except Exception as e:
    logger.warning(f"Groq client initialization failed: {e}")

# Gemini client
_gemini_available = False
_gemini_module = None

try:
    import google.genai as _gemini_module
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    _gemini_available = True
    logger.info("Gemini client initialized")
except ImportError:
    logger.warning("Google GenAI package not installed")
except Exception as e:
    logger.warning(f"Gemini client initialization failed: {e}")


# System prompt: medical triage nurse persona
TRIAGE_SYSTEM_PROMPT = """You are an experienced AI medical triage nurse assistant in an emergency department.

Your responsibilities:
1. Conduct a structured medical interview with the patient
2. Gather key clinical information through natural, compassionate dialogue
3. Ask ONE focused follow-up question per turn - never multiple questions at once
4. Extract structured clinical data from everything the patient tells you
5. DIFFERENTIATE between similar symptoms with proper medical reasoning

Information to collect (in order of priority):
- Chief complaint and primary symptoms (be specific about location, type, and severity)
- Pain characteristics: sharp vs dull, burning vs pressure, constant vs intermittent
- Onset, duration, and progression (sudden vs gradual? getting worse?)
- Severity rating - pain scale 0-10, be specific about what this means for their condition
- Associated symptoms (nausea, sweating, shortness of breath, etc.)
- Level of consciousness (alert, confused, drowsy?)
- Relevant history (similar episodes, medications, allergies)
- Aggravating or relieving factors

CRITICAL: Differentiate between symptoms properly:
- "Headache" vs "head pain": Ask about location, radiation, accompanying symptoms
- "Hand pain": Ask about which hand, specific fingers/joints, mechanism of injury
- "Chest pain": Ask about exertion relation, breathing difficulty, radiation
- "Abdominal pain": Ask about location, guarding, nausea/vomiting

Conversation guidelines:
- Use plain, compassionate language - not medical jargon
- Show empathy: "I'm sorry to hear that", "That sounds concerning"
- Ask ONE precise question based on what you've learned so far
- If patient describes life-threatening symptoms (chest pain + sweating,
  difficulty breathing, loss of consciousness, severe trauma), respond with
  urgency and tell them help is coming immediately
- After 3-4 exchanges OR when you have: symptoms + pain level + consciousness status, signal that assessment is complete

IMPORTANT - You MUST respond ONLY with valid JSON in this exact format:
{
  "reply": "Your spoken response to the patient (empathetic, professional)",
  "extracted_data": {
    "symptoms": ["list of all identified symptoms so far"],
    "pain_level": <integer 0-10, 0 if no pain or not yet known>,
    "urgency": "<low|medium|high|critical>",
    "is_conscious": <true|false>,
    "notes": "Key clinical observations and context",
    "confidence": <float 0.0-1.0, increases as more data is gathered>
  },
  "next_question": "The single follow-up question you will ask (empty if assessment complete)",
  "is_complete": <true when enough information gathered for clinical handoff, false otherwise>
}

Urgency classification:
- critical: life-threatening (chest pain + diaphoresis, respiratory distress,
            unconscious/unresponsive, major trauma, stroke symptoms)
- high:     needs immediate attention (severe pain 8-10/10, high fever >39.5°C,
            confusion, rapid deterioration, chest pain alone)
- medium:   needs prompt evaluation (moderate pain 4-7/10, persistent symptoms,
            concerning history but stable)
- low:      non-urgent (mild symptoms <4/10, stable, no red flags, chronic conditions)

MEDICAL DIFFERENTIATION EXAMPLES:
- For "headache": Ask about location (unilateral vs bilateral), duration, aura, photophobia
- For "hand pain": Ask about dominant hand, specific joints affected, mechanism
- For "chest pain": Ask about exertion relation, breathing difficulty, arm radiation
- For "abdominal pain": Ask about quadrant, guarding, bowel sounds"""


# Fallback response when LLM is unavailable
def _fallback_response(message: str, history: list[dict]) -> dict:
    """Rule-based fallback when the LLM is unavailable."""
    text_lower = message.lower()

    # Detect critical keywords
    critical_keywords = ["chest pain", "can't breathe", "unconscious",
                         "not breathing", "heart attack", "stroke",
                         "douleur thoracique", "ne respire pas"]
    high_keywords = ["severe", "severe pain", "8/10", "9/10", "10/10",
                     "fever", "confusion", "bleeding heavily"]

    urgency = "medium"
    symptoms = []

    if any(keyword in text_lower for keyword in critical_keywords):
        urgency = "critical"
        symptoms.append("critical symptoms detected")
    elif any(keyword in text_lower for keyword in high_keywords):
        urgency = "high"

    # Basic symptom extraction
    if "headache" in text_lower or "mal de tête" in text_lower:
        symptoms.append("headache")
    if "pain" in text_lower and "hand" in text_lower:
        symptoms.append("pain in hand")
    if "chest" in text_lower and ("pain" in text_lower or "douleur" in text_lower):
        symptoms.append("chest pain")
    if "fever" in text_lower or "fievre" in text_lower:
        symptoms.append("fever")

    pain = 0
    for n in range(10, -1, -1):
        if f"{n}/10" in text_lower or f"pain is {n}" in text_lower:
            pain = n
            break

    is_complete = len(symptoms) > 0 and (urgency in ["critical", "high"] or pain > 0 or len(history) >= 2)

    next_q = "" if is_complete else "On a scale from 0 to 10, how severe is your pain?"
    reply = (
        "Thank you. I have enough information and I am forwarding your case to the clinical team now."
        if is_complete
        else "I understand. To complete your triage quickly, please tell me your pain score from 0 to 10."
    )

    return {
        "reply": reply,
        "extracted_data": {
            "symptoms": symptoms,
            "pain_level": pain,
            "urgency": urgency,
            "is_conscious": "unconscious" not in text_lower,
            "notes": "Rule-based fallback chat mode",
            "confidence": 0.45 if is_complete else 0.3,
        },
        "next_question": next_q,
        "is_complete": is_complete,
    }


# Main LLM Engine class
class LLMEngine:
    """
    Manages LLM-powered triage conversations.
    Maintains no state itself - state is passed in as history.
    """

    def __init__(self, model: str = "llama-3.1-8b-instant"):
        self.model = model

        # Default to Groq for medical triage
        if model.startswith("llama") or model.startswith("mixtral"):
            self.provider = "groq"
        elif model.startswith("gpt"):
            self.provider = "openai"
        elif model.startswith("gemini"):
            self.provider = "gemini"
        else:
            # Default to Groq if model is unrecognized
            self.provider = "groq"
            self.model = "llama-3.1-8b-instant"

        logger.info(f"LLMEngine initialized with provider={self.provider}, model={self.model}")

    def _analyze_openai(self, messages: list[dict], max_tokens: int) -> dict:
        response = _openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=max_tokens,
            temperature=0.3,
        )
        raw = response.choices[0].message.content or ""
        return _parse_json_from_text(raw)

    def _analyze_groq(self, messages: list[dict], max_tokens: int) -> dict:
        if not _groq_client:
            logger.warning("Groq client not available - using fallback")
            return _fallback_response(messages[-1].get("content", "") if messages else "", [])
        
        response = _groq_client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=max_tokens,
            temperature=0.3,
        )
        raw = (response.choices[0].message.content or "").strip()
        return _parse_json_from_text(raw)

    def _analyze_gemini(self, messages: list[dict], max_tokens: int) -> dict:
        import google.generativeai as genai
        
        # Convert messages to genai format
        genai_messages = []
        for m in messages:
            role = m.get("role", "user")
            content = str(m.get("content", ""))
            if role == "system":
                # Add system message as first user message
                genai_messages.append({"role": "user", "parts": [{"text": content}]})
                genai_messages.append({"role": "model", "parts": [{"text": "Understood. I will follow these instructions."}]})
            elif role == "user":
                genai_messages.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                genai_messages.append({"role": "model", "parts": [{"text": content}]})

        # Create model with JSON response configuration
        model = genai.GenerativeModel(
            model_name=self.model,
            generation_config={
                "temperature": 0.3,
                "max_output_tokens": max_tokens,
                "response_mime_type": "application/json",
            },
        )

        # Generate response
        response = model.generate_content(genai_messages)
        raw = (getattr(response, "text", None) or "").strip()
        return _parse_json_from_text(raw)

    def analyze(
        self,
        message: str,
        history: list[dict],
        max_tokens: int = 1024,
    ) -> dict:
        """
        Analyze patient input and generate a triage nurse response.

        Args:
            message:  The patient's latest message (free text)
            history:  List of previous turns: [{"role": "user"/"assistant", "content": "..."}]
            max_tokens: Max tokens for the response

        Returns:
            dict with keys: reply, extracted_data, next_question, is_complete
        """
        if self.provider == "fallback":
            logger.warning("LLM not available - using fallback")
            return _fallback_response(message, history)

        # Build messages for the API call
        messages = [{"role": "system", "content": TRIAGE_SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        try:
            if self.provider == "gemini":
                result = self._analyze_gemini(messages, max_tokens)
            elif self.provider == "groq":
                result = self._analyze_groq(messages, max_tokens)
            else:
                result = self._analyze_openai(messages, max_tokens)

            # Validate and sanitise the response structure
            result = _sanitize_result(result, message)

            logger.info(
                f"LLM analysis - urgency={result['extracted_data']['urgency']} "
                f"pain={result['extracted_data']['pain_level']} "
                f"symptoms={result['extracted_data']['symptoms']} "
                f"confidence={result['extracted_data']['confidence']:.2f}"
            )
            return result

        except json.JSONDecodeError as e:
            logger.error(f"LLM returned invalid JSON: {e}")
            return _fallback_response(message, history)

        except Exception as e:
            logger.error(f"LLM API error ({self.provider}/{self.model}): {e}")
            return _fallback_response(message, history)


def _sanitize_result(result: dict, original_message: str) -> dict:
    """Ensures the LLM response has all required fields with correct types."""
    ed = result.get("extracted_data", {})

    # Ensure all extracted_data fields exist
    symptoms = ed.get("symptoms", [])
    if isinstance(symptoms, str):
        symptoms = [s.strip() for s in symptoms.split(",") if s.strip()]
    elif not isinstance(symptoms, list):
        symptoms = []

    pain = ed.get("pain_level", 0)
    try:
        pain = int(float(pain))
    except (ValueError, TypeError):
        pain = 0
    pain = max(0, min(10, pain))

    urgency = ed.get("urgency", "medium")
    if urgency not in {"low", "medium", "high", "critical"}:
        urgency = "medium"

    is_conscious = ed.get("is_conscious", True)
    if isinstance(is_conscious, str):
        is_conscious = is_conscious.lower() in {"true", "yes", "1"}

    notes = str(ed.get("notes", ""))[:500]  # Limit length

    confidence = ed.get("confidence", 0.3)
    try:
        confidence = float(confidence)
    except (ValueError, TypeError):
        confidence = 0.3
    confidence = max(0.0, min(1.0, confidence))

    # Determine if assessment is complete
    is_complete = result.get("is_complete", False)
    if isinstance(is_complete, str):
        is_complete = is_complete.lower() in {"true", "yes", "1"}
    
    # Auto-complete if sufficient clinical data is gathered
    if not is_complete and symptoms and pain >= 0 and urgency != "medium":
        is_complete = True
        logger.info(f"Auto-completing assessment: symptoms={len(symptoms)}, pain={pain}, urgency={urgency}")
    
    # Force completion after 4 exchanges if we have basic data
    if not is_complete and len(history) >= 8:  # 4 exchanges = 8 messages
        is_complete = True
        logger.info(f"Auto-completing assessment after 4 exchanges")
        
    # Override LLM completion for critical cases
    if urgency == "critical" and not is_complete:
        is_complete = True
        logger.info(f"Auto-completing critical assessment")
        
    # Preserve fallback completion logic
    if not is_complete and result.get("is_complete", False):
        is_complete = result.get("is_complete", False)

    # Generate appropriate next question if not provided
    next_q = result.get("next_question", "")
    if not isinstance(next_q, str):
        next_q = ""

    # Generate appropriate reply if not provided
    reply = result.get("reply", "")
    if not isinstance(reply, str):
        reply = "Please describe your symptoms in more detail."

    # Adjust confidence based on completeness
    if is_complete:
        confidence = max(confidence, 0.7)
    elif len(symptoms) == 0:
        confidence = min(confidence, 0.2)

    return {
        "reply": str(result.get("reply", "Please describe your symptoms.")),
        "extracted_data": {
            "symptoms": symptoms,
            "pain_level": pain,
            "urgency": urgency,
            "is_conscious": is_conscious,
            "notes": notes,
            "confidence": confidence,
        },
        "next_question": next_q,
        "is_complete": is_complete,
    }


_default_engine = None


def analyze_patient_input(text: str, history: list[dict] | None = None) -> dict:
    """
    Convenience function matching the spec interface.

    Args:
        text: Patient message
        history: Conversation history

    Returns:
        Extracted clinical data dictionary
    """
    global _default_engine
    if _default_engine is None:
        _default_engine = LLMEngine()

    result = _default_engine.analyze(text, history or [])
    return result["extracted_data"]


# Conversation Memory class for maintaining chat context
class ConversationMemory:
    """
    Manages conversation history and extracted data for multiple chat sessions.
    Used by LLMDialogueBehaviour to maintain context across turns.
    """

    def __init__(self):
        self._histories = {}
        self._data = {}

    def add_user(self, session_id: str, content: str) -> None:
        """Add a user message to the conversation history."""
        self._histories.setdefault(session_id, []).append({"role": "user", "content": content})

    def add_assistant(self, session_id: str, content: str) -> None:
        """Add an assistant message to the conversation history."""
        self._histories.setdefault(session_id, []).append({"role": "assistant", "content": content})

    def get_history(self, session_id: str) -> list[dict]:
        """Get the full conversation history for a session."""
        return self._histories.get(session_id, [])

    def update_data(self, session_id: str, data: dict) -> None:
        """Update the extracted clinical data for a session."""
        self._data[session_id] = data

    def get_data(self, session_id: str) -> dict:
        """Get the current extracted clinical data for a session."""
        return self._data.get(session_id, {})

    def clear(self, session_id: str) -> None:
        """Clear all data for a session."""
        self._histories.pop(session_id, None)
        self._data.pop(session_id, None)

    def get_all_sessions(self) -> list[str]:
        """Get list of all active session IDs."""
        return list(self._histories.keys())
