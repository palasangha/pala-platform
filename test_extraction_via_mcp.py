#!/usr/bin/env python3
"""Test metadata extraction via MCP server."""

import json
import asyncio
import websockets
import uuid

async def test_metadata_extraction():
    """Test metadata extraction through MCP server."""
    
    # Connect to MCP server
    uri = "ws://localhost:3010"
    
    sample_text = """From Refusals to Last-Minute Rescue
29 September 1969
New Delhi

Ministry of External Affairs
Government of India

To: The Foreign Secretary

Subject: Vietnam Negotiations - Recent Developments

The attached documents chronicle recent diplomatic communications regarding the Vietnam War negotiations. Ambassador Johnson has indicated that significant progress may be possible in the coming weeks.

Key Points:
- Paris Peace Talks continuing
- Soviet Union offering limited support
- US government considering new proposals
- Indian delegation recommends cautious optimism

Prepared by: Dr. Ashok Mehta
Date: 29 September 1969
Confidentiality: Limited Distribution"""

    try:
        async with websockets.connect(uri) as ws:
            print(f"Connected to MCP server at {uri}\n")
            
            # Create extraction request
            request_id = str(uuid.uuid4())
            request = {
                "jsonrpc": "2.0",
                "method": "call_tool",
                "params": {
                    "agent_id": "metadata-extraction-agent",
                    "tool_name": "extract_metadata",
                    "tool_params": {
                        "text": sample_text,
                        "model": "ollama",
                        "output_type": "pala"
                    }
                },
                "id": request_id
            }
            
            print("Sending request:")
            print(json.dumps(request, indent=2))
            print("\nWaiting for response...\n")
            
            await ws.send(json.dumps(request))
            
            # Receive response
            response = await ws.recv()
            response_data = json.loads(response)
            
            print("Response received:")
            print(json.dumps(response_data, indent=2))
            
            if "result" in response_data:
                result = response_data["result"]
                if isinstance(result, dict) and "pala_metadata" in result:
                    pala = result["pala_metadata"]
                    print("\n\n=== EXTRACTED METADATA ===")
                    print(f"Document Type: {pala['document_metadata']['type'].get('value', 'unknown')}")
                    print(f"Document Date: {pala['document_metadata']['date'].get('value', 'unknown')}")
                    print(f"\nPeople: {len(pala['parties']['people'])} found")
                    for person in pala['parties']['people']:
                        print(f"  - {person['name']} ({person['role']}, confidence: {person['confidence']})")
                    print(f"\nOrganizations: {len(pala['parties']['organizations'])} found")
                    for org in pala['parties']['organizations']:
                        print(f"  - {org['name']} ({org.get('role', 'unknown')})")
                    print(f"\nLocations: {len(pala['places']['locations'])} found")
                    for loc in pala['places']['locations']:
                        print(f"  - {loc['name']} ({loc.get('role', 'mentioned')})")
                    print(f"\nSummary: {pala['content']['summary']['text'][:200]}...")
                    print(f"Topics: {pala['content']['topics']['topics']}")
                    print(f"Tone: {pala['content']['tone_sentiment']['tone']}")
                    print(f"Overall Confidence: {pala['quality_metrics']['overall_confidence']}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_metadata_extraction())
