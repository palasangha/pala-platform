#!/usr/bin/env python3
"""
Direct test to show what questions would pass the new 0.75 quality gate
without needing to regenerate via Ollama
"""

import sys
from pathlib import Path

agent_dir = Path(__file__).parent / 'packages' / 'PalaAgents' / 'storage-agent'
sys.path.insert(0, str(agent_dir))

import asyncio

async def main():
    from provider_factory import get_provider
    
    storage_provider = get_provider()
    all_docs = await storage_provider.list_documents()
    
    if isinstance(all_docs, dict):
        documents = all_docs.get('documents', [])
    else:
        documents = all_docs
    
    if not documents:
        print("No documents found")
        return
    
    doc_id = documents[0].get('id') if isinstance(documents[0], dict) else getattr(documents[0], 'id', None)
    doc = await storage_provider.retrieve_document(doc_id)
    
    app_data = getattr(doc, 'app_data', {}) or {}
    questions_payload = app_data.get('questions_payload', {})
    stored_questions = questions_payload.get('questions', [])
    
    print("\n" + "="*100)
    print("QUALITY GATE SIMULATION: 0.75 threshold + duplicate detection")
    print("="*100)
    print(f"Input: {len(stored_questions)} questions from database")
    print(f"Threshold: confidence >= 0.75")
    print(f"Minimum after filtering: 5 questions")
    print()
    
    # Simulate new quality gate logic
    CONFIDENCE_FLOOR = 0.75
    MIN_QUESTIONS = 5
    
    quality_filtered = []
    seen_snippets = set()
    rejected = []
    
    for q in stored_questions:
        evidence = q.get('evidence', [])
        conf = float(evidence[0].get('confidence', 0.0)) if evidence else 0.0
        snippet = evidence[0].get('snippet', '').strip() if evidence else ''
        q_text = q.get('text', 'N/A')
        
        # Check for duplicate snippets
        if snippet:
            snippet_key = snippet[:100].lower()
            if snippet_key in seen_snippets:
                rejected.append({
                    'text': q_text[:70],
                    'reason': 'duplicate snippet',
                    'confidence': conf
                })
                continue
            seen_snippets.add(snippet_key)
        
        # Check confidence threshold
        if conf >= CONFIDENCE_FLOOR:
            quality_filtered.append(q)
            print(f"✅ ACCEPT  Q: {q_text[:70]}")
            print(f"           Conf: {conf:.2f} (>= {CONFIDENCE_FLOOR})")
            print(f"           Snippet: {snippet[:60]}...\n")
        else:
            rejected.append({
                'text': q_text[:70],
                'reason': f'low confidence ({conf:.2f} < {CONFIDENCE_FLOOR})',
                'confidence': conf
            })
            print(f"❌ REJECT  Q: {q_text[:70]}")
            print(f"           Conf: {conf:.2f} (< {CONFIDENCE_FLOOR})")
            print(f"           Snippet: {snippet[:60]}...\n")
    
    print("\n" + "="*100)
    print("RESULTS")
    print("="*100)
    print(f"✅ ACCEPTED: {len(quality_filtered)} questions")
    print(f"❌ REJECTED: {len(rejected)} questions")
    print()
    
    if rejected:
        print("REJECTED QUESTIONS:")
        for r in rejected:
            print(f"  - {r['text']}")
            print(f"    Reason: {r['reason']}")
            print()
    
    print("="*100)
    print("FILTERED QUESTIONS (what would be stored):")
    print("="*100)
    for idx, q in enumerate(quality_filtered, 1):
        evidence = q.get('evidence', [])
        conf = float(evidence[0].get('confidence', 0.0)) if evidence else 0.0
        print(f"\n{idx}. {q.get('text', 'N/A')}")
        print(f"   Confidence: {conf:.2f}")
    
    print(f"\n\nFINAL: {len(quality_filtered)} high-quality questions (filtered from {len(stored_questions)})")
    print("These are the questions that will be kept with the new quality gate.\n")

asyncio.run(main())
