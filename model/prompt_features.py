import re
import logging
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Constraint keywords that indicate a highly specific prompt ("must", "only", "O(N)", etc.)
CONSTRAINT_KEYWORDS = [
    r'\bmust\b', r'\bonly\b', r'\bwithout\b', r'\bperformance\b', 
    r'\bofficial\b', r'\bstrictly\b', r'\bexactly\b', r'O\([1Nn]\)', r'O\(log\s*[Nn]\)'
]

# Scoped verbs that indicate targeted modification rather than generic requests
SCOPED_VERBS = [
    r'\brefactor\b', r'\boptimize\b', r'\bextract\b', r'\bencapsulate\b', 
    r'\bdecouple\b', r'\bnormalize\b', r'\bvectorize\b', r'\babstract\b', r'\brename\b'
]

# Weak supervision labels for re-prompts
REPROMPT_INDICATORS = [
    r"no,? that's not", r"no,? i meant", r"that didn't work", 
    r"still getting an error", r"that gives me", r"what about instead"
]

def extract_c2_features(prompt_text: str, next_turn_text: str = "") -> Dict[str, float]:
    """
    Extracts Component 2 (prompt quality) features from a single prompt string.
    This serves as the scoring engine contract for assessing candidate specificity.
    
    Args:
        prompt_text: The raw text of the user's prompt to the LLM.
        next_turn_text: (Optional) The user's immediately subsequent prompt 
                        in the same session, used for weak supervision labels.
                        
    Returns:
        Dict: A dictionary of numeric feature values for LightGBM.
    """
    if not isinstance(prompt_text, str) or not prompt_text.strip():
        logger.warning("Empty or invalid prompt text passed to C2 extractor.")
        return {
            'prompt_length': 0.0,
            'has_code_context': 0.0,
            'has_function_name': 0.0,
            'has_constraint_language': 0.0,
            'has_scoped_verbs': 0.0,
            're_prompt_indicator': 0.0,
            'turns_to_resolution': 0.0 # Handled at session level usually
        }

    # 1. Prompt Length
    length = float(len(prompt_text))
    
    # 2. Code Context (backticks)
    has_code_context = 1.0 if ('`' in prompt_text or '```' in prompt_text) else 0.0
    
    # 3. Function/Variable naming (camelCase or snake_case)
    # rudimentary heuristic looking for lowercase_with_underscore or camelCase identifiers
    snake_case = bool(re.search(r'\b[a-z]+_[a-z0-9_]+\b', prompt_text))
    camel_case = bool(re.search(r'\b[a-z]+[A-Z][a-zA-Z0-9]*\b', prompt_text))
    has_func_name = 1.0 if (snake_case or camel_case) else 0.0
    
    # 4. Constraint Language
    prompt_lower = prompt_text.lower()
    has_constraint = 0.0
    for keyword in CONSTRAINT_KEYWORDS:
        if re.search(keyword, prompt_lower):
            has_constraint = 1.0
            break
            
    # 5. Scoped Verbs
    has_scoped = 0.0
    for verb in SCOPED_VERBS:
        if re.search(verb, prompt_lower):
            has_scoped = 1.0
            break

    # 6. Re-prompt indicator (Weak Supervision Label)
    re_prompt = 0.0
    if next_turn_text:
        next_lower = next_turn_text.lower()
        for indicator in REPROMPT_INDICATORS:
            if re.search(indicator, next_lower):
                re_prompt = 1.0
                break

    return {
        'prompt_length': length,
        'has_code_context': has_code_context,
        'has_function_name': has_func_name,
        'has_constraint_language': has_constraint,
        'has_scoped_verbs': has_scoped,
        're_prompt_indicator': re_prompt,
        'turns_to_resolution': 0.0 # To be calculated by iterating over the session
    }
