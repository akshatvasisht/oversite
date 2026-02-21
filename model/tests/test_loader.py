import pandas as pd
from loader import load_cups, load_wildchat, passes_wildchat_filters

def test_passes_wildchat_filters():
    # Valid
    conv1 = [
        {"role": "user", "content": "write code"},
        {"role": "assistant", "content": "```python\nprint(1)\n```"},
        {"role": "user", "content": "thanks"}
    ]
    assert passes_wildchat_filters(conv1) == True
    
    # Invalid: no code block
    conv2 = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
        {"role": "user", "content": "bye"}
    ]
    assert passes_wildchat_filters(conv2) == False
    
    # Invalid: too short
    conv3 = [
        {"role": "user", "content": "write code"},
        {"role": "assistant", "content": "```python\nprint(1)\n```"}
    ]
    assert passes_wildchat_filters(conv3) == False

def test_load_cups_returns_dataframe():
    df = load_cups()
    assert isinstance(df, pd.DataFrame)
    if not df.empty:
        assert 'acceptance_rate' in df.columns

def test_load_wildchat_returns_dataframe():
    df = load_wildchat(max_records=2)
    assert isinstance(df, pd.DataFrame)
    if not df.empty:
        assert len(df) <= 2
