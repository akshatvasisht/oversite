import pytest
import os
import joblib
from prompt_features import extract_c2_features, score_prompts

def test_c2_model_loads():
    model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "component2_xgboost.joblib")
    model = joblib.load(model_path)
    feats = extract_c2_features("fix this")
    
    # Needs to match the 5 features used in training, ignoring the 6th "weak supervision" label
    feature_vector = [[
        feats['prompt_length'],
        feats['has_code_context'],
        feats['has_function_name'],
        feats['has_constraint_language'],
        feats['has_scoped_verbs']
    ]]
    
    score = model.predict(feature_vector)[0]
    # Prediction is either 0 or 1.
    assert score in [0, 1]

def test_specific_prompt_scores_higher_than_vague():
    vague_prompt = "fix this function"
    specific_prompt = "The `calculate_discount` fn on line 42 returns None when rate=0. Modify it to default to 0."
    
    scores = score_prompts([vague_prompt, specific_prompt])
    
    v = scores[0]
    s = scores[1]
    
    assert 1.0 <= v <= 5.0
    assert 1.0 <= s <= 5.0
    
    # We expect the structured prompt to score higher (or equal) than the vague one
    # given our C2 structural heuristics.
    assert s > v
