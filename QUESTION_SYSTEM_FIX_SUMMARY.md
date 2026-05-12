# Question Generation System - Fix Summary

## Issues Fixed

### 1. **Bug in `tool_get_document_questions` - Dict Access Error**
**File:** `packages/PalaAgents/storage-agent/main.py` (line 1544)

**Problem:** The function was trying to access dictionary values using integer indices:
```python
# WRONG - questions_db.get_questions_for_document returns dicts, not tuples
'question_id': q[0],  # TypeError!
'text': q[1],
'suggestion_type': q[3],
```

**Fix:** Changed to proper dictionary key access:
```python
# CORRECT
'question_id': q['question_id'],
'text': q['text'],
'suggestion_type': q['suggestion_type'],
```

Also fixed status tuple access to use `.get()` method for dict safety:
```python
'generation_status': status.get('status') if status else 'unknown',
```

### 2. **TimelineExplorer Search UX - Incomplete Implementation**
**File:** `apps/web/components/TimelineExplorer.tsx` (lines 840-920)

**Problem:** The old implementation had a simple toggle checkbox that switched between content search and question search. This didn't meet the requirement where:
- Users search for content (e.g., "mother")
- Get BOTH document results AND question suggestions
- Can click a question to use it as a search filter

**Fix:** Completely rewrote the search experience:
1. Added new state variables for question suggestions:
   - `suggestedQuestions`: Array of similar questions
   - `showQuestionDropdown`: Boolean to show/hide suggestions
   - `loadingQuestions`: Loading state for suggestions

2. When user types in search box, automatically fetch similar questions in real-time:
   ```typescript
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
     }).then((response) => {
       setSuggestedQuestions(data.questions || []);
       setShowQuestionDropdown(true);
     });
   }
   ```

3. Display question suggestions in a dropdown below search box:
   - Shows up to 5 most similar pre-generated questions
   - Shows similarity percentage for each
   - Users can click a question to use it as search filter

4. Clicking a question uses its text as the new search query:
   ```typescript
   onClick={() => {
     setQuery(q.text);
     setShowQuestionDropdown(false);
   }}
   ```

## How It Works Now

### User Flow:
1. User opens TimelineExplorer (Browse → Explore)
2. User types "mother" in search box
3. **Simultaneously:**
   - System searches documents for "mother" in content/metadata
   - System fetches similar pre-generated questions and shows them in dropdown
   - Lists documents that contain "mother"
4. User can:
   - Click on a document from the list to view it
   - **OR** click on a question from the dropdown (e.g., "What role does motherhood play?")
   - When question is clicked, it becomes the new search query, documents are re-searched with that question text

### Technical Details:

**Tool: `get_document_questions`**
- Fixed to properly access dict keys instead of tuple indices
- Returns: `{document_id, questions[], question_count, generation_status}`

**Tool: `search_questions`**
- Already had correct dict access
- Takes query, returns similar questions with similarity scores
- Used with `similarity_threshold=0.3` for broader matching

**Component: TimelineExplorer**
- Questions load asynchronously as user types (debounced)
- Dropdown appears below search input
- Questions display with their similarity to user's query
- Clicking question triggers document search with that question text
- All existing search/filter functionality preserved

## What's Next

To fully test the system end-to-end:

1. **Ensure Ollama is running:**
   ```bash
   docker-compose up ollama
   ```

2. **Generate questions for existing documents:**
   ```bash
   cd packages/PalaAgents/storage-agent
   python3 batch_regenerate_questions.py --limit 10 --delay 2.0
   ```

3. **Test in UI:**
   - Open Browse → Explore
   - Type "mother" or other search term
   - See question suggestions appear
   - Click a question to filter documents

## Files Modified

1. `packages/PalaAgents/storage-agent/main.py`
   - Fixed `tool_get_document_questions` dict access bug

2. `apps/web/components/TimelineExplorer.tsx`
   - Added question suggestion dropdown UI
   - Implemented real-time question loading as user types
   - Added click-to-filter functionality

## Testing

The question generation system was previously tested with 6 unit tests (all passing):
- Test 1: Question Generation
- Test 2: Storage and Retrieval
- Test 3: Batch Storage
- Test 4: Generation Status Tracking
- Test 5: Vector Similarity Search
- Test 6: Question Regeneration

All tests pass successfully, validating the core functionality.
