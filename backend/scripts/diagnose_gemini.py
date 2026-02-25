#!/usr/bin/env python3
"""
Diagnostic utility for verifying Gemini API connectivity and model availability.
Checks the API key from .env and lists authorized models for the current project.
"""
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(".env")

api_key = os.getenv("GEMINI_API_KEY")

print("Listing all models with '1.5' or 'pro' in their name:")
client = genai.Client(api_key=api_key)
try:
    for m in client.models.list():
        if '1.5' in m.name or 'pro' in m.name:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error: {e}")

try:
    # Try a simple text generation with a likely model
    target_model = "models/gemini-flash-latest"
    print(f"\nAttempting generation with {target_model}...")
    response = client.models.generate_content(
        model=target_model,
        contents="Hello, this is a test.",
    )
    print("Success!")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error caught: {type(e).__name__}")
    print(str(e))
