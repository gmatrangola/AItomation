import json

def extract_json_from_string(text: str) -> dict:
    """Finds and extracts the first valid JSON object from a string."""
    try:
        start_index = text.find('{')
        end_index = text.rfind('}')
        if start_index != -1 and end_index != -1 and end_index > start_index:
            json_str = text[start_index : end_index + 1]
            return json.loads(json_str)
        else:
            raise ValueError("No valid JSON object found in the string.")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[ERROR] Failed to extract JSON. Error: {e}.")
        print(f"[TRACE] Raw text for JSON extraction failure:\n---\n{text}\n---")
        raise