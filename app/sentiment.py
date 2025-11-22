# Rule-based simple intent detection for Spanish.
# All comments in English.

NEGATIVE_KEYWORDS = [
    "no estoy interesado",
    "no me interesa",
    "no quiero",
    "no gracias",
    "no por ahora",
    "no tengo plata",
    "no tengo dinero",
    "muy caro",
    "demasiado caro",
]

POSITIVE_KEYWORDS = [
    "sí me interesa",
    "si me interesa",
    "me interesa",
    "suena bien",
    "me gusta",
    "quisiera saber más",
    "quisiera saber mas",
    "quiero más información",
    "quiero mas informacion",
]

FOLLOW_UP_KEYWORDS = [
    "llámame luego",
    "llamame luego",
    "más tarde",
    "mas tarde",
    "otro día",
    "otro dia",
    "en otro momento",
]


def analyze_intent(text: str) -> str:
    """
    Analyze Spanish text to detect a simple intent:
    - NOT_INTERESTED
    - FOLLOW_UP
    - INTERESTED
    - NEUTRAL
    """
    if not text:
        return "NEUTRAL"

    t = text.lower().strip()

    for phrase in NEGATIVE_KEYWORDS:
        if phrase in t:
            return "NOT_INTERESTED"

    for phrase in FOLLOW_UP_KEYWORDS:
        if phrase in t:
            return "FOLLOW_UP"

    for phrase in POSITIVE_KEYWORDS:
        if phrase in t:
            return "INTERESTED"

    # Fallback quick heuristics
    if "no " in t and "me interesa" in t:
        return "NOT_INTERESTED"

    if "interesa" in t or "más información" in t or "mas informacion" in t:
        return "INTERESTED"

    return "NEUTRAL"