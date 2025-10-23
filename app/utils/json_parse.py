import logging
import re
import json
logger = logging.getLogger('uvicorn.error')

def gemini_json_parse(text: str):
    """
    Gemini api returns json in the formof
    ```json
    {}
    ```
    need to be parsed
    """
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            logger.exception("Malformed/unrecognized gemini response")

    raise ValueError("Unable to parse gemini response, not match for regex search")
