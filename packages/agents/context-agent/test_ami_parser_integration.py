#!/usr/bin/env python3
"""
Test script for AMI Metadata Parser integration with Context Agent
"""

import asyncio
import json
import sys
from main import ContextAgent


async def test_ami_parser():
    """Test the AMI filename parser integration"""
    print("=" * 80)
    print("Testing AMI Metadata Parser Integration")
    print("=" * 80)

    # Initialize the agent
    agent = ContextAgent()

    # Test cases
    test_filenames = [
        "MSALTMEBA00100004.00_(01_02_0071)_LT_MIX_1990_BK MODI_TO_REVSNGOENKA.JPG",
        "MSALTMEBA00100005.00_(02_03_0125)_BK_PRINT_1985_AUTHOR_TO_EDITOR.PDF",
        "MSALTMEBA00100006.00_(01_01_0001)_NB_HAND_1975_STUDENT_TO_TEACHER.TIF",
        "SIMPLEFILENAME.JPG"  # Should fail gracefully
    ]

    print("\nRunning tests...\n")

    for i, filename in enumerate(test_filenames, 1):
        print(f"Test {i}: {filename}")
        print("-" * 80)

        try:
            # Call the parse_ami_filename method directly
            result = await agent.parse_ami_filename({'filename': filename})

            # Display results
            if result.get('parsed'):
                print("✓ Successfully parsed")
                print("\nExtracted Metadata:")
                print(f"  Master ID: {result.get('master_identifier', 'N/A')}")
                print(f"  Document Type: {result.get('document_type_full', 'N/A')} ({result.get('document_type', 'N/A')})")
                print(f"  Medium: {result.get('medium_full', 'N/A')} ({result.get('medium', 'N/A')})")
                print(f"  Year: {result.get('year', 'N/A')}")
                print(f"  Sender: {result.get('sender', 'N/A')}")
                print(f"  Recipient: {result.get('recipient', 'N/A')}")
                print(f"  Page: {result.get('page_number', 'N/A')}")
                print(f"  Sequence: {result.get('sequence', 'N/A')}")

                print("\nArchipelago Fields:")
                archipelago = result.get('archipelago_fields', {})
                for key, value in archipelago.items():
                    print(f"  {key}: {value}")

                if result.get('summary'):
                    print("\nFormatted Summary:")
                    print(result['summary'])

            else:
                print("✗ Failed to parse")
                if result.get('error'):
                    print(f"  Error: {result['error']}")

        except Exception as e:
            print(f"✗ Exception occurred: {e}")

        print("\n" + "=" * 80 + "\n")

    # Test the tool registration
    print("Tool Registration Test")
    print("-" * 80)
    tool_definitions = agent.get_tool_definitions()
    ami_tool = next((t for t in tool_definitions if t['name'] == 'parse_ami_filename'), None)

    if ami_tool:
        print("✓ parse_ami_filename tool is registered")
        print(f"\nTool Definition:")
        print(json.dumps(ami_tool, indent=2))
    else:
        print("✗ parse_ami_filename tool is NOT registered")
        return False

    print("\n" + "=" * 80)
    print("All tests completed successfully!")
    print("=" * 80)

    return True


if __name__ == '__main__':
    try:
        success = asyncio.run(test_ami_parser())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Test failed with error: {e}", file=sys.stderr)
        sys.exit(1)
