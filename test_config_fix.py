#!/usr/bin/env python3
"""Test AI Providers configuration after fix."""

from cyclisme_training_logs.config import get_ai_config

def test_config():
    """Test configuration loads correctly."""
    config = get_ai_config()

    print("✅ Config loaded successfully")
    print("\n📋 API Keys:")

    # Test Mistral
    assert hasattr(config, 'mistral_api_key'), "Missing mistral_api_key"
    if config.mistral_api_key:
        print(f"   ✅ Mistral: {config.mistral_api_key[:10]}...")
    else:
        print("   ⚠️  Mistral: Not configured")

    # Test Claude
    assert hasattr(config, 'claude_api_key'), "Missing claude_api_key"
    if config.claude_api_key:
        print(f"   ✅ Claude: {config.claude_api_key[:10]}...")
    else:
        print("   ⚠️  Claude: Not configured")

    # Test OpenAI
    assert hasattr(config, 'openai_api_key'), "Missing openai_api_key"
    if config.openai_api_key:
        print(f"   ✅ OpenAI: {config.openai_api_key[:10]}...")
    else:
        print("   ⚠️  OpenAI: Not configured (optional)")

    print("\n🔧 Settings:")
    print(f"   Default provider: {config.default_provider}")
    print(f"   Enable fallback: {config.enable_fallback}")
    print(f"   Mistral model: {config.mistral_model}")
    print(f"   Claude model: {config.claude_model}")

    # Test Mistral parameters
    print("\n🎛️  Mistral Parameters:")
    print(f"   Temperature: {config.mistral_temperature}")
    print(f"   Max tokens: {config.mistral_max_tokens}")
    print(f"   Timeout: {config.mistral_timeout}s")

    # Test provider detection
    print("\n🔍 Available Providers:")
    available = config.get_available_providers()
    for provider in available:
        print(f"   ✅ {provider}")

    print("\n✅ All tests passed!")

if __name__ == '__main__':
    test_config()
