from prompt_features import extract_prompt_quality_features

def test_specific_prompt_scores_higher():
    vague_prompt = "fix this function"
    
    specific_prompt = (
        "The `calculate_discount` fn on line 42 currently returns None when "
        "rate is 0. We must refactor it to strictly default to 0.0 to improve performance."
    )
    
    v = extract_prompt_quality_features(vague_prompt, "")
    s = extract_prompt_quality_features(specific_prompt, "")
    
    # Specific prompt should have higher structural specificity scores
    assert s['has_function_name'] == 1.0
    assert v['has_function_name'] == 0.0
    
    assert s['prompt_length'] > v['prompt_length']
    
    assert s['has_code_context'] == 1.0
    assert v['has_code_context'] == 0.0
    
    assert s['has_constraint_language'] == 1.0
    assert v['has_constraint_language'] == 0.0
    
    assert s['has_scoped_verbs'] == 1.0 # refactor
    assert v['has_scoped_verbs'] == 0.0
    
def test_reprompt_detection():
    initial_prompt = "extract the logging logic into a helper"
    next_turn = "No, I meant extract it into a separate class, that didn't work."
    
    features = extract_prompt_quality_features(initial_prompt, next_turn)
    assert features['re_prompt_indicator'] == 1.0
    
    good_next_turn = "Great, now let's add unit tests for it."
    features_good = extract_prompt_quality_features(initial_prompt, good_next_turn)
    assert features_good['re_prompt_indicator'] == 0.0

def test_empty_input_handling():
    feats = extract_prompt_quality_features("")
    assert feats['prompt_length'] == 0.0
    assert feats['has_function_name'] == 0.0
    assert feats['re_prompt_indicator'] == 0.0
