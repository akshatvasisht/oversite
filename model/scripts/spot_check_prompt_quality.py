from prompt_features import extract_prompt_quality_features

sample_prompts = [
    "fix this error",
    "can you make it faster please?",
    "Refactor `compute_metrics` to strictly use O(N) time complexity.",
    "The test fails on `calculate_discount()`. It must only return floats.",
    "Write a python script to parse a csv file."
]

print("=== Prompt Quality Feature Extractor Spot Check ===")
for p in sample_prompts:
    print(f"\nPrompt: '{p}'")
    feats = extract_prompt_quality_features(p)
    print(f"  Length: {feats['prompt_length']}")
    print(f"  Has Code Context: {feats['has_code_context']}")
    print(f"  Has Func Name: {feats['has_function_name']}")
    print(f"  Constraint Lang: {feats['has_constraint_language']}")
    print(f"  Scoped Verbs: {feats['has_scoped_verbs']}")
