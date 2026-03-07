"""
Integration Examples: Using LangChain with Your GVPOCR Application
This file shows practical examples of how to integrate LangChain with OCR workflows
"""

# Example 1: Using LangChain in Flask Routes
# ============================================

from flask import Blueprint, request, jsonify
from app.services.langchain_service import get_langchain_service

def example_ocr_analysis_route():
    """
    Example: Analyze OCR results with LangChain LLM
    Use case: Extracting insights from scanned documents
    """
    data = request.json
    ocr_text = data.get('ocr_text')
    
    service = get_langchain_service()
    
    # Ask LLM to summarize OCR results
    prompt = f"""Summarize the following OCR text in 3 sentences:
    
    {ocr_text}"""
    
    summary = service.invoke(prompt)
    return jsonify({'summary': summary})


# Example 2: Batch Processing with LangChain
# ===========================================

def example_batch_ocr_analysis():
    """
    Example: Analyze multiple OCR results in parallel
    Use case: Processing bulk scanned documents
    """
    ocr_texts = [
        "OCR text from document 1...",
        "OCR text from document 2...",
        "OCR text from document 3..."
    ]
    
    service = get_langchain_service()
    
    # Create prompts for each OCR text
    prompts = [
        f"Extract the main subject from: {text}"
        for text in ocr_texts
    ]
    
    # Get all responses at once
    subjects = service.batch_invoke(prompts)
    return {'subjects': subjects}


# Example 3: Search with Embeddings
# ==================================

def example_semantic_search():
    """
    Example: Search OCR documents using semantic similarity
    Use case: Finding documents similar to a search query
    """
    # Sample OCR texts from documents
    documents = [
        "Invoice for services rendered on January 15",
        "Employee payroll summary for Q1",
        "Customer receipt from retail purchase"
    ]
    
    # User search query
    search_query = "financial documents"
    
    service = get_langchain_service()
    
    # Get embeddings for documents and query
    doc_embeddings = service.get_embeddings(documents)
    query_embedding = service.get_embedding(search_query)
    
    # Simple cosine similarity search
    import numpy as np
    similarities = []
    for doc_emb in doc_embeddings:
        similarity = np.dot(query_embedding, doc_emb)
        similarities.append(similarity)
    
    # Return top matches
    top_indices = np.argsort(similarities)[::-1][:2]
    return {
        'query': search_query,
        'results': [documents[i] for i in top_indices]
    }


# Example 4: Interactive Document Q&A
# ====================================

def example_document_qa():
    """
    Example: Ask questions about OCR document content
    Use case: Interactive chatbot for document review
    """
    service = get_langchain_service()
    
    # Create conversation for analyzing a document
    service.create_conversation_chain()
    
    # Simulate conversation flow
    document_content = """
    Annual Report 2023
    Revenue: $1.5M
    Profit: $300K
    Employees: 50
    """
    
    # First message sets context
    response1 = service.chat(f"""
    I'm showing you an annual report:
    {document_content}
    
    What is the profit margin?
    """)
    
    # Second message uses context from conversation memory
    response2 = service.chat("What about employee productivity?")
    
    return {
        'context': document_content,
        'qa': [
            {'q': 'What is the profit margin?', 'a': response1},
            {'q': 'What about employee productivity?', 'a': response2}
        ]
    }


# Example 5: Real-time Streaming Analysis
# ========================================

def example_streaming_analysis():
    """
    Example: Stream OCR analysis results as they're being generated
    Use case: Real-time user feedback in web interface
    """
    from flask import Response
    
    service = get_langchain_service()
    
    ocr_text = """
    Detailed document content that needs real-time analysis...
    This could be a long document that takes time to analyze.
    """
    
    prompt = f"Provide detailed analysis of: {ocr_text}"
    
    def generate():
        for chunk in service.stream_invoke(prompt):
            yield f"data: {chunk}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


# Example 6: Integration with Bulk Jobs
# ======================================

def example_bulk_ocr_with_langchain(job_id: str):
    """
    Example: Integrate LangChain analysis into bulk OCR processing
    Use case: Enhance bulk jobs with LLM analysis
    
    This would be called from your bulk processing service:
    from app.services.langchain_service import get_langchain_service
    """
    from pymongo import MongoClient
    import os
    
    service = get_langchain_service()
    
    # Connect to MongoDB (already done in your app)
    # Get OCR results from bulk job
    # Process with LangChain
    # Store enhanced results
    
    sample_flow = """
    1. Get OCR text from processed file
    2. Create analysis prompt
    3. Get LLM response
    4. Store results back in MongoDB
    5. Update job progress
    
    Example implementation:
    """
    
    prompt = "Analyze this scanned document for key information"
    analysis = service.invoke(prompt)
    
    return analysis


# Example 7: Content Classification
# ==================================

def example_document_classification():
    """
    Example: Classify OCR documents by type
    Use case: Auto-categorization of scanned documents
    """
    service = get_langchain_service()
    
    documents = [
        "Invoice #12345 dated 2024-01-15 for consulting services",
        "Employee W-4 form with tax withholding information",
        "Product return authorization and RMA number"
    ]
    
    # Batch classify documents
    prompts = [
        f"""Classify this document in one word (invoice/form/receipt/letter/other):
        {doc}"""
        for doc in documents
    ]
    
    classifications = service.batch_invoke(prompts)
    
    return {
        'documents': documents,
        'classifications': classifications
    }


# Example 8: Custom Flask Route with LangChain
# =============================================

from flask import Blueprint

analyze_bp = Blueprint('analyze', __name__, url_prefix='/api/analyze')

@analyze_bp.route('/ocr-text', methods=['POST'])
def analyze_ocr():
    """
    Endpoint: POST /api/analyze/ocr-text
    Body: {"ocr_text": "...", "analysis_type": "summary|extract|classify"}
    """
    data = request.json
    ocr_text = data.get('ocr_text')
    analysis_type = data.get('analysis_type', 'summary')
    
    service = get_langchain_service()
    
    if analysis_type == 'summary':
        prompt = f"Summarize: {ocr_text}"
    elif analysis_type == 'extract':
        prompt = f"Extract key information: {ocr_text}"
    elif analysis_type == 'classify':
        prompt = f"Classify document type: {ocr_text}"
    else:
        return {'error': 'Invalid analysis_type'}, 400
    
    result = service.invoke(prompt)
    return jsonify({'result': result, 'type': analysis_type})


# Example 9: Error Handling and Retry Logic
# ==========================================

def example_robust_invocation():
    """
    Example: Robust error handling for production use
    """
    import time
    import logging
    
    logger = logging.getLogger(__name__)
    service = get_langchain_service()
    
    def invoke_with_retry(prompt: str, max_retries: int = 3):
        """Invoke with automatic retry on failure"""
        for attempt in range(max_retries):
            try:
                return service.invoke(prompt)
            except Exception as e:
                logger.error(f"Attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
    
    try:
        result = invoke_with_retry("Your OCR analysis prompt")
        return {'status': 'success', 'result': result}
    except Exception as e:
        logger.error(f"Failed after retries: {e}")
        return {'status': 'error', 'message': str(e)}, 500


# Example 10: Using with Existing OCR Providers
# ==============================================

def example_combine_with_ocr_providers():
    """
    Example: Combine traditional OCR with LLM analysis
    """
    service = get_langchain_service()
    
    # Pseudo-code showing integration with your OCR providers
    
    def process_document_with_ai(file_path):
        # Step 1: Run traditional OCR (your existing code)
        # ocr_results = ocr_provider.extract_text(file_path)
        
        # Step 2: Enhance with LLM analysis
        ocr_text = "OCR extracted text..."  # from step 1
        
        # Step 3: Get embeddings for similarity search
        embedding = service.get_embedding(ocr_text)
        
        # Step 4: Get structured analysis
        prompt = f"""Extract structured information from this OCR text:
        {ocr_text}
        
        Return JSON with: document_type, key_fields, confidence"""
        
        analysis = service.invoke(prompt)
        
        # Step 5: Combine results
        return {
            'ocr_text': ocr_text,
            'embedding': embedding,
            'analysis': analysis
        }
    
    return process_document_with_ai("sample.pdf")


# Quick Integration Checklist
# ============================

INTEGRATION_CHECKLIST = """
✅ LangChain Setup Complete

To integrate into your application:

1. [ ] Install dependencies: pip install -r backend/requirements.txt
2. [ ] Test health check: curl http://localhost:5000/api/langchain/health
3. [ ] Import service: from app.services.langchain_service import get_langchain_service
4. [ ] Create routes that call service methods
5. [ ] Add error handling for production
6. [ ] Test with real OCR data
7. [ ] Monitor performance and adjust models if needed
8. [ ] Document API changes for frontend team

Use Cases to Implement:
- [ ] Document classification/categorization
- [ ] Content summarization
- [ ] Key information extraction
- [ ] Semantic search across documents
- [ ] Interactive Q&A about documents
- [ ] Automated tagging/labeling
- [ ] Content quality assessment
- [ ] Duplicate detection (using embeddings)

Testing:
- [ ] Unit tests for langchain_service
- [ ] Integration tests with Flask routes
- [ ] Load tests for batch operations
- [ ] Error scenario tests (Ollama down, etc.)
"""

if __name__ == '__main__':
    print(INTEGRATION_CHECKLIST)
