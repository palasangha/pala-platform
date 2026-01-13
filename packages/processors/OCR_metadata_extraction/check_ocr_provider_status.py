#!/usr/bin/env python3
"""
OCR Provider Status Checker
Quick diagnostic tool to check the status of all OCR providers
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def check_providers():
    """Check status of all OCR providers"""

    try:
        from app import create_app
        from app.services import ocr_service
        from app.config import Config
    except ImportError as e:
        print(f"❌ Error importing Flask app: {e}")
        print("Make sure you're running this from the project root directory")
        return

    print("\n" + "="*80)
    print("OCR PROVIDER STATUS CHECKER")
    print("="*80 + "\n")

    app = create_app()

    with app.app_context():
        print("📋 ENVIRONMENT CONFIGURATION\n")

        # Check key environment variables
        checks = [
            ("LMSTUDIO_ENABLED", Config.LMSTUDIO_ENABLED),
            ("LMSTUDIO_HOST", Config.LMSTUDIO_HOST),
            ("OLLAMA_ENABLED", Config.OLLAMA_ENABLED),
            ("OLLAMA_HOST", Config.OLLAMA_HOST),
            ("VLLM_ENABLED", Config.VLLM_ENABLED),
            ("LLAMACPP_ENABLED", Config.LLAMACPP_ENABLED),
            ("CLAUDE_ENABLED", Config.CLAUDE_ENABLED),
            ("GOOGLE_VISION_ENABLED", getattr(Config, 'GOOGLE_VISION_ENABLED', True)),
            ("GOOGLE_LENS_ENABLED", getattr(Config, 'GOOGLE_LENS_ENABLED', True)),
            ("TESSERACT_ENABLED", getattr(Config, 'TESSERACT_ENABLED', True)),
            ("EASYOCR_ENABLED", getattr(Config, 'EASYOCR_ENABLED', True)),
        ]

        for key, value in checks:
            if isinstance(value, bool):
                status = "✅" if value else "❌"
                print(f"{status} {key:<30} = {value}")
            else:
                print(f"ℹ️  {key:<30} = {value}")

        print("\n" + "="*80)
        print("🔍 PROVIDER AVAILABILITY STATUS\n")

        # Get provider list with availability
        try:
            providers = ocr_service.get_available_providers()

            enabled_count = 0
            disabled_count = 0

            for provider in providers:
                status = "✅ ENABLED " if provider['available'] else "❌ DISABLED"
                print(f"{status}: {provider['display_name']:<50} ({provider['name']})")

                if provider['available']:
                    enabled_count += 1
                else:
                    disabled_count += 1

            print("\n" + "-"*80)
            print(f"\nSummary: {enabled_count} enabled, {disabled_count} disabled out of {len(providers)} providers\n")

        except Exception as e:
            print(f"❌ Error getting provider list: {e}")
            return

        # Detailed analysis of disabled providers
        print("="*80)
        print("📝 DETAILED PROVIDER ANALYSIS\n")

        disabled_providers = [p for p in providers if not p['available']]

        if disabled_providers:
            print(f"Found {len(disabled_providers)} disabled provider(s):\n")

            for provider in disabled_providers:
                name = provider['name']
                print(f"❌ {provider['display_name']}")
                print(f"   Internal name: {name}")

                # Provider-specific diagnostics
                if name == 'lmstudio':
                    print(f"   Fix: Check if LM Studio is running at {Config.LMSTUDIO_HOST}")
                    print(f"        Or set LMSTUDIO_ENABLED=true in .env if LM Studio is running")

                elif name == 'ollama':
                    print(f"   Fix: Check if Ollama server is running at {Config.OLLAMA_HOST}")
                    print(f"        Verify with: curl {Config.OLLAMA_HOST}/api/tags")

                elif name == 'vllm':
                    print(f"   Fix: Set VLLM_ENABLED=true in .env and start vLLM server")
                    print(f"        Configure VLLM_HOST={Config.VLLM_HOST}")

                elif name == 'llamacpp':
                    print(f"   Fix: Set LLAMACPP_ENABLED=true in .env and start llama.cpp server")
                    print(f"        Configure LLAMACPP_HOST={Config.LLAMACPP_HOST}")

                elif name == 'google_vision' or name == 'google_lens':
                    has_creds = hasattr(Config, 'GOOGLE_APPLICATION_CREDENTIALS') and Config.GOOGLE_APPLICATION_CREDENTIALS
                    print(f"   Fix: Set GOOGLE_APPLICATION_CREDENTIALS in .env")
                    print(f"        Place credentials JSON file in backend directory")
                    print(f"        Current: {Config.GOOGLE_APPLICATION_CREDENTIALS if has_creds else 'NOT SET'}")

                elif name == 'serpapi_google_lens':
                    print(f"   Fix: Set SERPAPI_API_KEY in .env")

                elif name == 'azure':
                    print(f"   Fix: Set AZURE_VISION_ENDPOINT and AZURE_VISION_KEY in .env")

                elif name == 'claude':
                    print(f"   Fix: Install anthropic package: pip install anthropic")
                    print(f"        Set ANTHROPIC_API_KEY in .env")

                elif name == 'tesseract':
                    print(f"   Fix: Install pytesseract: pip install pytesseract")
                    print(f"        Install tesseract binary (apt-get/brew/windows)")

                elif name == 'easyocr':
                    print(f"   Fix: Install easyocr: pip install easyocr")

                elif name == 'chrome_lens':
                    print(f"   Fix: Install chrome-lens-py: pip install chrome-lens-py")

                print()
        else:
            print("✅ All providers are enabled!\n")

        # Recommendations
        print("="*80)
        print("💡 RECOMMENDATIONS\n")

        if disabled_count == 0:
            print("✅ All providers are configured and ready to use!")
        else:
            print(f"ℹ️  You have {disabled_count} disabled provider(s).")
            print("   To enable a provider:")
            print("   1. Read the OCR_PROVIDER_DIAGNOSTIC_GUIDE.md for detailed instructions")
            print("   2. Configure the required environment variables in .env")
            print("   3. Restart the backend: docker-compose restart backend")
            print("   4. Re-run this script to verify\n")

        print("📖 For detailed help, see: OCR_PROVIDER_DIAGNOSTIC_GUIDE.md\n")
        print("="*80 + "\n")


if __name__ == '__main__':
    check_providers()
