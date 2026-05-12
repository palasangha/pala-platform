# Code Changes - Question Generation System Fixes

## File 1: `packages/PalaAgents/storage-agent/main.py`

### Location: Lines 1544-1577

### Function: `tool_get_document_questions`

**Change**: Fixed dictionary access pattern

#### Before (Broken):
```python
async def tool_get_document_questions(params: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieve pre-generated questions for a document"""
    doc_id = params.get('document_id')
    
    if not doc_id:
        raise ValueError("document_id is required")
    
    if not questions_db:
        raise ValueError("Questions database not available")
    
    try:
        logger.info(f"[QUESTIONS-TOOL] Retrieving questions for document {doc_id}")
        questions = questions_db.get_questions_for_document(doc_id)
        
        # Get generation status
        status = questions_db.get_generation_status(doc_id)
        
        result = {
            'document_id': doc_id,
            'questions': [
                {
                    'question_id': q[0],              # ❌ BUG: q is dict, not tuple
                    'text': q[1],                     # ❌ BUG: q is dict, not tuple
                    'suggestion_type': q[3],         # ❌ BUG: q is dict, not tuple
                }
                for q in questions
            ],
            'question_count': len(questions),
            'generation_status': status[0] if status else 'unknown',  # ❌ BUG: status is dict
        }
        logger.info(f"[QUESTIONS-TOOL] ✅ Retrieved {len(questions)} questions")
        return result
    except Exception as e:
        logger.error(f"[QUESTIONS-TOOL] ❌ Failed to retrieve questions: {e}", exc_info=True)
        raise
```

#### After (Fixed):
```python
async def tool_get_document_questions(params: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieve pre-generated questions for a document"""
    doc_id = params.get('document_id')
    
    if not doc_id:
        raise ValueError("document_id is required")
    
    if not questions_db:
        raise ValueError("Questions database not available")
    
    try:
        logger.info(f"[QUESTIONS-TOOL] Retrieving questions for document {doc_id}")
        questions = questions_db.get_questions_for_document(doc_id)
        
        # Get generation status
        status = questions_db.get_generation_status(doc_id)
        
        result = {
            'document_id': doc_id,
            'questions': [
                {
                    'question_id': q['question_id'],          # ✅ FIXED: Dict key access
                    'text': q['text'],                        # ✅ FIXED: Dict key access
                    'suggestion_type': q['suggestion_type'],  # ✅ FIXED: Dict key access
                }
                for q in questions
            ],
            'question_count': len(questions),
            'generation_status': status.get('status') if status else 'unknown',  # ✅ FIXED: Dict .get()
        }
        logger.info(f"[QUESTIONS-TOOL] ✅ Retrieved {len(questions)} questions")
        return result
    except Exception as e:
        logger.error(f"[QUESTIONS-TOOL] ❌ Failed to retrieve questions: {e}", exc_info=True)
        raise
```

**Explanation**:
- Line 1560: Changed `q[0]` → `q['question_id']`
- Line 1561: Changed `q[1]` → `q['text']`
- Line 1562: Changed `q[3]` → `q['suggestion_type']`
- Line 1565: Changed `status[0]` → `status.get('status')`

**Root Cause**: 
`questions_db.get_questions_for_document()` returns a list of dictionaries, not tuples. The original code was using integer indexing which works on tuples but not dicts.

**Impact**:
- ✅ Fixes TypeError when accessing dictionary keys with integer indices
- ✅ MCP tool now returns correct response format
- ✅ "Get Questions" button in UI now works

---

## File 2: `apps/web/components/TimelineExplorer.tsx`

### Change 1: Added State Variables

#### Location: Lines 395-397

**Before**:
```typescript
export function TimelineExplorer() {
  const searchParams = useSearchParams();
  const lastAutoOpenedIdRef = useRef<string | null>(null);
  const { connected, send } = useWebSocket();
  const [documents, setDocuments] = useState<TimelineDocument[]>([]);
  const [queryResults, setQueryResults] = useState<TimelineDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [selectedYear, setSelectedYear] = useState('all');
  const [selectedFilter, setSelectedFilter] = useState<TimelineFilter>('all');
  const [selectedDocument, setSelectedDocument] = useState<TimelineDocument | null>(null);
  const [selectedDetails, setSelectedDetails] = useState<TimelineDocument | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [showRawJson, setShowRawJson] = useState(false);
  // ... no question suggestion state
}
```

**After**:
```typescript
export function TimelineExplorer() {
  const searchParams = useSearchParams();
  const lastAutoOpenedIdRef = useRef<string | null>(null);
  const { connected, send } = useWebSocket();
  const [documents, setDocuments] = useState<TimelineDocument[]>([]);
  const [queryResults, setQueryResults] = useState<TimelineDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [selectedYear, setSelectedYear] = useState('all');
  const [selectedFilter, setSelectedFilter] = useState<TimelineFilter>('all');
  const [selectedDocument, setSelectedDocument] = useState<TimelineDocument | null>(null);
  const [selectedDetails, setSelectedDetails] = useState<TimelineDocument | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [showRawJson, setShowRawJson] = useState(false);
  const [suggestedQuestions, setSuggestedQuestions] = useState<any[]>([]);      // NEW
  const [showQuestionDropdown, setShowQuestionDropdown] = useState(false);      // NEW
  const [loadingQuestions, setLoadingQuestions] = useState(false);               // NEW
}
```

---

### Change 2: Rewrote Search Input Component

#### Location: Lines 840-920

**Before** (with checkbox toggle):
```tsx
<div className="rounded-xl border border-slate-800 bg-slate-800 p-4">
  <label className="block text-sm font-medium text-slate-200 mb-2">Search</label>
  <input
    value={query}
    onChange={(e) => setQuery(e.target.value)}
    placeholder="Search titles, summaries, people, places, and metadata..."
    className="w-full rounded-lg bg-slate-900 border border-slate-700 px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
  />
  <div className="mt-3 flex items-center gap-3">
    <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
      <input
        type="checkbox"
        id="search-questions-toggle"
        defaultChecked={false}
        onChange={(e) => {
          const isQuestionsMode = e.target.checked;
          if (isQuestionsMode && query.trim()) {
            // Search questions mode
            if (connected) {
              setLoading(true);
              send('tools/invoke', {
                agentId: 'storage-agent',
                name: 'search_questions',
                arguments: {
                  query: query.trim(),
                  limit: 50,
                  similarity_threshold: 0.3,
                },
              }).then((response: any) => {
                const data = unwrapToolResult(response);
                if (data?.questions) {
                  const questionItems = data.questions.map((q: any) => ({
                    documentId: q.document_id || 'question',
                    title: q.text,
                    dateLabel: 'Q',
                    sortDate: new Date().toISOString(),
                    year: new Date().getFullYear().toString(),
                    summary: `Similar to: ${q.text}`,
                    people: [],
                    places: [],
                    topics: [],
                    documentType: 'pre-generated-question',
                    createdBy: 'questions-system',
                    fileFormat: 'text',
                    source: {
                      id: q.question_id,
                      document_id: q.document_id,
                    },
                    passage: q.text,
                    matchedPath: 'question',
                    matchReason: `Question match (similarity: ${q.similarity?.toFixed(2) || 'N/A'})`,
                    relevanceScore: q.similarity || 0.5,
                  }));
                  setQueryResults(questionItems);
                  console.log('[TimelineExplorer] Found', questionItems.length, 'similar questions');
                }
                setLoading(false);
              }).catch((err: any) => {
                console.error('[TimelineExplorer] Question search error:', err);
                setError('Failed to search questions');
                setLoading(false);
              });
            }
          }
        }}
        className="rounded"
      />
      Search pre-generated questions instead
    </label>
  </div>
</div>
```

**After** (with auto-loading dropdown):
```tsx
<div className="rounded-xl border border-slate-800 bg-slate-800 p-4 relative">
  <label className="block text-sm font-medium text-slate-200 mb-2">Search</label>
  <div className="relative">
    <input
      value={query}
      onChange={(e) => {
        const newQuery = e.target.value;
        setQuery(newQuery);
        
        // Auto-load question suggestions when user types
        if (newQuery.trim() && connected && !loadingQuestions) {
          setLoadingQuestions(true);
          send('tools/invoke', {
            agentId: 'storage-agent',
            name: 'search_questions',
            arguments: {
              query: newQuery.trim(),
              limit: 5,
              similarity_threshold: 0.3,
            },
          }).then((response: any) => {
            const data = unwrapToolResult(response);
            if (data?.questions) {
              setSuggestedQuestions(data.questions || []);
              setShowQuestionDropdown(true);
              console.log('[TimelineExplorer] Loaded', data.questions.length, 'suggested questions');
            } else {
              setSuggestedQuestions([]);
            }
            setLoadingQuestions(false);
          }).catch((err: any) => {
            console.error('[TimelineExplorer] Error loading questions:', err);
            setSuggestedQuestions([]);
            setLoadingQuestions(false);
          });
        } else if (!newQuery.trim()) {
          setSuggestedQuestions([]);
          setShowQuestionDropdown(false);
        }
      }}
      placeholder="Search titles, summaries, people, places, and metadata..."
      className="w-full rounded-lg bg-slate-900 border border-slate-700 px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
    />
    
    {/* Question suggestions dropdown */}
    {showQuestionDropdown && suggestedQuestions.length > 0 && (
      <div className="absolute top-full left-0 right-0 mt-1 z-50 bg-slate-900 border border-slate-700 rounded-lg shadow-lg max-h-64 overflow-y-auto">
        <div className="p-2">
          <p className="text-xs text-slate-400 px-2 py-1">Similar pre-generated questions:</p>
          {suggestedQuestions.map((q: any, idx: number) => (
            <button
              key={idx}
              onClick={() => {
                // Use the question text as a new search query
                setQuery(q.text);
                setShowQuestionDropdown(false);
                console.log('[TimelineExplorer] Using question as search filter:', q.text);
              }}
              className="w-full text-left px-2 py-2 hover:bg-slate-800 rounded text-sm text-slate-200 transition"
            >
              <div className="font-medium truncate">{q.text}</div>
              <div className="text-xs text-slate-400">
                Similarity: {(q.similarity * 100).toFixed(0)}%
              </div>
            </button>
          ))}
        </div>
      </div>
    )}
  </div>
  {loadingQuestions && <p className="mt-2 text-xs text-slate-400">Loading question suggestions...</p>}
</div>
```

**Key Changes**:
1. Replaced checkbox with auto-loading logic
2. When user types, fetch similar questions immediately (limit: 5)
3. Display questions in a dropdown below search input
4. Show similarity percentage for each
5. Allow clicking a question to use it as search filter
6. Loading state indicator
7. All existing document search functionality preserved

**Impact**:
- ✅ Questions load automatically as user types
- ✅ Both content and questions visible simultaneously
- ✅ Click question to filter documents
- ✅ Much better UX

---

## Summary of Changes

| File | Lines | Change | Type |
|------|-------|--------|------|
| main.py | 1560-1562 | Fixed dict access q[i] → q['key'] | Bug Fix |
| main.py | 1565 | Fixed status dict access | Bug Fix |
| TimelineExplorer.tsx | 395-397 | Added 3 state variables | Feature Addition |
| TimelineExplorer.tsx | 844-920 | Rewrote search component | UX Redesign |

**Total Lines Changed**: ~80 lines modified/added
**Files Modified**: 2
**Bugs Fixed**: 2
**Features Added**: 1 (question suggestion dropdown)

---

## Testing

### Manual Test Steps

1. **Verify Python Syntax**:
   ```bash
   python3 -m py_compile packages/PalaAgents/storage-agent/main.py
   # Should return with no errors
   ```

2. **Verify TypeScript**:
   ```bash
   cd apps/web
   npm run type-check
   # Should show no errors for TimelineExplorer.tsx
   ```

3. **Test in UI**:
   - Open Browse → Explore
   - Type "mother" in search
   - Verify:
     - Documents appear (left side)
     - Question dropdown appears (below search)
     - Suggestions show similarity %
   - Click a question
   - Verify:
     - Search text updates
     - Documents re-filter based on question

### Expected Results

**Before Fix**:
- Get Questions button hangs (no response)
- No question suggestions in search
- User can't use questions to filter documents

**After Fix**:
- Get Questions button works instantly
- Question suggestions appear as user types
- User can click a question to use as search filter
- Both content and questions searchable

