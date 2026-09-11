import json
import random
import re

def extract_and_parse_json(raw_response: str) -> dict:
    """
    Cleans unstructured LLM responses containing markdown blocks or junk characters,
    repairs broken JSON string ends, and returns a parsed Python dictionary.
    """
    if not raw_response or not isinstance(raw_response, str):
        raise ValueError("Input response must be a non-empty string.")

    # 1. Strip markdown code blocks (```json ... ```)
    cleaned = re.sub(r'```(?:json)?', '', raw_response, flags=re.IGNORECASE)

    # 2. Extract content starting from the first '{'
    match = re.search(r'\{', cleaned)
    if not match:
        raise ValueError("No JSON object starting with '{' found in response.")

    cleaned = cleaned[match.start():]

    # 3. Locate the last valid structural closing brace '}'
    last_brace = cleaned.rfind('}')
    if last_brace != -1:
        cleaned = cleaned[:last_brace + 1]
    else:
        # If the trailing quote/brace was cut off (e.g. '*]]]]'), repair it manually
        cleaned = re.sub(r'[\*\]\s]+$', '"\n}', cleaned)

    # 4. Parse into valid dictionary
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        # Fallback attempt: auto-close dangling string quotes if broken mid-string
        try:
            repaired = cleaned.strip() + '"}'
            return json.loads(repaired)
        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse repaired JSON: {e}")

def generar_numero_10():
    return ''.join(str(random.randint(0, 9)) for _ in range(10))