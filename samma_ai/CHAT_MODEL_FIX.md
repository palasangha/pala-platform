# Chat Model Selection & Persistence — Fix Summary

## Issues Fixed

### 1. **Hardcoded Claude Model in Chat**
**Problem:** The `/api/chat` endpoint was hardcoded to use `ClaudeService`, ignoring the new multi-model infrastructure.

**Fix:**
- Updated `backend/app/routes/chat.py` to use `ModelRouterService` instead of `ClaudeService`
- Added `model_id` parameter to chat request (defaults to Claude if not specified)
- Added `model_used` field to response so frontend knows which model answered

**Files changed:**
- `/mnt/sda1/mango1_home/pala-platform/samma_ai/backend/app/routes/chat.py`
- `/mnt/sda1/mango1_home/pala-platform/samma_ai/backend/app/services/model_router_service.py` (added `generate_dhamma_response` method)

---

### 2. **No Model Selector in Chat UI**
**Problem:** Users had no way to choose which AI model to use for chat (Claude/OpenAI/Ollama).

**Fix:**
- Added a **brain icon (🧠) dropdown** in the chat screen AppBar
- Shows checkmark next to currently selected model
- Options: Claude Sonnet 4, GPT-4o, Ollama (Llama 2)
- Shows snackbar confirmation when switching models

**Files changed:**
- `/mnt/sda1/mango1_home/pala-platform/samma_ai/frontend/lib/screens/chat_screen.dart`
- `/mnt/sda1/mango1_home/pala-platform/samma_ai/frontend/lib/providers/chat_provider.dart` (added `selectedModelId` and `setModel()`)

---

### 3. **Chat History Not Persisted**
**Problem:** Messages were stored in memory only — navigating away and back cleared the entire conversation.

**Fix:**
- Integrated `shared_preferences` for local storage
- Chat history now auto-saves after every message
- Conversation ID and selected model also persisted
- History auto-loads when ChatProvider initializes
- Clear chat button now also clears storage

**Files changed:**
- `/mnt/sda1/mango1_home/pala-platform/samma_ai/frontend/lib/providers/chat_provider.dart`
- `/mnt/sda1/mango1_home/pala-platform/samma_ai/frontend/lib/models/chat_message.dart` (added `toJson()` methods)
- `/mnt/sda1/mango1_home/pala-platform/samma_ai/frontend/lib/services/api_service.dart` (added `modelId` parameter)

---

## How It Works Now

### Backend Flow
```
User sends message
  ↓
POST /api/chat { message, conversation_id, model_id }
  ↓
ModelRouterService.generate_dhamma_response(model_id)
  ↓
Routes to: Claude | OpenAI | Ollama | Copilot
  ↓
Returns 4-part Dhamma response + model_used
```

### Frontend Flow
```
User types message
  ↓
ChatProvider.sendMessage(content)
  ↓
ApiService.sendChatMessage(message, conversationId, selectedModelId)
  ↓
Response received → add to _messages
  ↓
_saveChatHistory() → SharedPreferences
  ↓
UI updates (persisted across navigation)
```

### Model Selection
```
User clicks brain icon (🧠)
  ↓
Popup shows: [✓ Claude] [○ GPT-4o] [○ Ollama]
  ↓
User selects model
  ↓
ChatProvider.setModel(modelId)
  ↓
Saves to SharedPreferences
  ↓
Next message uses new model
```

---

## Testing

1. **Model switching:**
   - Click brain icon in chat AppBar
   - Select different model
   - Send a message → backend should use selected model

2. **Persistence:**
   - Send some messages
   - Navigate to Agents tab
   - Navigate back to Chat
   - Messages should still be there

3. **Multi-model support:**
   - Try Claude (default)
   - Try GPT-4o (if `OPENAI_API_KEY` set)
   - Try Ollama (if Ollama running locally)

---

## Agent Direct Messages

**Note:** Agent direct messages in the Agent Dashboard → Direct tab are still using mock responses. To fix this, you would need to:

1. Create a new backend route `/api/agents/<agent_name>/message`
2. Update `direct_message_view.dart` to call the API instead of showing hardcoded "I received your message..."
3. Route agent messages through Pala-Jarvis orchestrator for proper delegation

This is a separate feature from the main chat and can be implemented as a follow-up task.
