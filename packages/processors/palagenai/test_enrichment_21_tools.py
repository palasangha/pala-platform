#!/usr/bin/env python3
"""
Test script to verify inline enrichment service calls all 21 MCP tools
and produces complete enriched output with raw MCP responses
"""
import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from app.services.inline_enrichment_service import MCPEnrichmentClient


async def test_enrichment():
    """Test enrichment with sample OCR result"""

    # Sample OCR text from actual document
    sample_text = """--- Page 1 ---
Guidance for Future Meditators
28th January 1971 , Bodh Gaya
Dear Babu bhaiya , Respectful salutations
I felt happy sharing merits last evening with Ma Sayama and , along with you all , the
other family members , the centre residents , and meditators at the conclusion of the course .
This retreat has been significant in many ways . Revered Sayagyi , upon leaving his phys-
ical form , not only entrusted me with a great responsibility but also endowed me with the
spiritual strength to bear it . Now , I clearly understand that it is imperative to become worthy
of this in order to utilize that incalculable Dhamma treasury so that we may take joy in it .
Now I have to remain firm on this Dhamma journey under his protective umbrella .
Due to the passing away of Respected Sayagyi , a number of meditators who were to
journey to Rangoon to meditate with him will not be able to do so now . Still , if a student
happens to decide to go there , upon receiving a telegram to that effect, you should make
arrangements for him to be picked up from the airport and taken to the meditation centre .
Sitting in the centre , whatever unwholesome kammas can be washed away will be beneficial
to all . Hence , all required comforts and arrangements for these students should be taken care
of . If they cannot carry their bedding while travelling , then this should be provided from
our home . Their meals , etc. , should also be arranged and paid for by us . Put Banwari ( Goen-
kaji's son ) in charge of taking them around the main sites of Rangoon . And should any one
of them be returning to India , then if possible , send a few Dhamma books from our library
with them ; if not , then never mind .
Your Younger Brother ,
Satyanarayan
VIPASSANA RESEARCH INSTITUTE"""

    print("=" * 80)
    print("TESTING ENRICHMENT SERVICE WITH ALL 21 MCP TOOLS")
    print("=" * 80)
    print(f"\nSample text length: {len(sample_text)} characters")
    print("\nInitializing MCP Enrichment Client...")

    client = MCPEnrichmentClient(mcp_url="ws://localhost:3003")

    print("\nStarting enrichment (this will call all 21 MCP tools)...")
    print("-" * 80)

    try:
        enriched_data = await client.enrich_document(
            ocr_text=sample_text,
            filename="test_document.pdf"
        )

        print("\n" + "=" * 80)
        print("ENRICHMENT COMPLETED SUCCESSFULLY!")
        print("=" * 80)

        # Verify all 21 tools were called
        raw_responses = enriched_data.get("raw_mcp_responses", {})
        expected_tools = [
            # Metadata agent (4 tools)
            "extract_document_type",
            "extract_storage_info",
            "extract_digitization_metadata",
            "determine_access_level",
            # Entity agent (5 tools)
            "extract_people",
            "extract_organizations",
            "extract_locations",
            "extract_events",
            "generate_relationships",
            # Structure agent (6 tools)
            "extract_salutation",
            "parse_letter_body",
            "extract_closing",
            "extract_signature",
            "identify_attachments",
            "parse_correspondence",
            # Content agent (3 tools)
            "generate_summary",
            "extract_keywords",
            "classify_subjects",
            # Context agent (3 tools)
            "research_historical_context",
            "assess_significance",
            "generate_biographies"
        ]

        print(f"\n📊 TOOL CALL SUMMARY:")
        print(f"   Expected tools: {len(expected_tools)}")
        print(f"   Tools called: {len(raw_responses)}")

        # Check which tools were called
        tools_called = set(raw_responses.keys())
        tools_expected = set(expected_tools)

        missing_tools = tools_expected - tools_called
        extra_tools = tools_called - tools_expected

        if missing_tools:
            print(f"\n❌ MISSING TOOLS ({len(missing_tools)}):")
            for tool in sorted(missing_tools):
                print(f"   - {tool}")

        if extra_tools:
            print(f"\n➕ EXTRA TOOLS ({len(extra_tools)}):")
            for tool in sorted(extra_tools):
                print(f"   - {tool}")

        if len(raw_responses) == len(expected_tools) and not missing_tools:
            print(f"\n✅ SUCCESS: All {len(expected_tools)} tools were called!")

        # Show success/failure for each tool
        print(f"\n📝 TOOL CALL RESULTS:")
        successful = 0
        failed = 0

        for tool_name in sorted(expected_tools):
            result = raw_responses.get(tool_name, {})
            success = result.get("success", False)
            if success:
                successful += 1
                status = "✓"
            else:
                failed += 1
                status = "✗"
                error = result.get("error", "Unknown error")
                print(f"   {status} {tool_name}: FAILED - {error}")

            if success:
                print(f"   {status} {tool_name}")

        print(f"\n📈 RESULTS:")
        print(f"   Successful: {successful}/{len(expected_tools)}")
        print(f"   Failed: {failed}/{len(expected_tools)}")
        print(f"   Success rate: {(successful/len(expected_tools)*100):.1f}%")

        # Show structure of merged result
        merged = enriched_data.get("merged_result", {})
        print(f"\n📦 MERGED RESULT STRUCTURE:")
        print(f"   metadata: {list(merged.get('metadata', {}).keys())}")
        print(f"   document: {list(merged.get('document', {}).keys())}")
        print(f"   content: {list(merged.get('content', {}).keys())}")
        print(f"   analysis: {list(merged.get('analysis', {}).keys())}")

        # Show sample data from merged result
        print(f"\n🔍 SAMPLE EXTRACTED DATA:")
        print(f"   Document type: {merged.get('metadata', {}).get('document_type', 'N/A')}")
        print(f"   Access level: {merged.get('metadata', {}).get('access_level', 'N/A')}")
        print(f"   People found: {len(merged.get('analysis', {}).get('people', []))}")
        print(f"   Organizations found: {len(merged.get('analysis', {}).get('organizations', []))}")
        print(f"   Locations found: {len(merged.get('analysis', {}).get('locations', []))}")
        print(f"   Events found: {len(merged.get('analysis', {}).get('events', []))}")
        print(f"   Keywords found: {len(merged.get('analysis', {}).get('keywords', []))}")
        print(f"   Relationships found: {len(merged.get('analysis', {}).get('relationships', []))}")

        # Save enriched output to file
        output_file = Path(__file__).parent / "test_enrichment_output.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(enriched_data, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Full enriched output saved to: {output_file}")
        print(f"   File size: {output_file.stat().st_size:,} bytes")

        print("\n" + "=" * 80)
        print("TEST COMPLETED!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ ERROR: Enrichment failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    print("\nStarting enrichment test...")
    print("Make sure MCP server is running on ws://localhost:3003\n")

    success = asyncio.run(test_enrichment())

    sys.exit(0 if success else 1)
