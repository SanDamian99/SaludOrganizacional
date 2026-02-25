#!/usr/bin/env python3
"""Test script to verify all imports work correctly."""

print("Testing imports...")

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    print("1. Testing src.core.config...")
    from src.core.config import DATA_DICTIONARY, get_gemini_api_key, get_supabase_url
    print("   ✓ src.core.config OK")
except Exception as e:
    print(f"   ✗ ERROR: {e}")

try:
    print("2. Testing src.core.state...")
    from src.core.state import init_session_state
    print("   ✓ src.core.state OK")
except Exception as e:
    print(f"   ✗ ERROR: {e}")

try:
    print("3. Testing src.data.processor...")
    from src.data.processor import DataCleaner
    print("   ✓ src.data.processor OK")
except Exception as e:
    print(f"   ✗ ERROR: {e}")

try:
    print("4. Testing src.data.supabase_client...")
    from src.data.supabase_client import SupabaseManager
    print("   ✓ src.data.supabase_client OK")
except Exception as e:
    print(f"   ✗ ERROR: {e}")

try:
    print("5. Testing src.ai.gemini_client...")
    from src.ai.gemini_client import GeminiClient
    print("   ✓ src.ai.gemini_client OK")
except Exception as e:
    print(f"   ✗ ERROR: {e}")

print("\n✅ All imports successful!")
