# ⚡ GitHub Copilot Auto-Approve - Quick Setup

## 🎯 Quick Steps (2 Minutes)

### Step 1: Open Settings
Press `Ctrl + ,` (or `Cmd + ,` on Mac)

### Step 2: Go to settings.json
Press `Ctrl + Shift + P` and type:
```
Preferences: Open Settings (JSON)   
```

### Step 3: Add This Configuration
```json
"github.copilot.chat.commandAutoApprove": [
  "explain",
  "docs"
]
```

### Step 4: Save & Reload
- Save: `Ctrl + S`
- Reload: `Ctrl + R`

**Done!** ✅

---

## 📍 Complete Example

Copy-paste this into your `settings.json`:

```json
{
  // Enable Copilot for code files
  "github.copilot.enable": {
    "*": true,
    "plaintext": false,
    "markdown": false
  },

  // Enable Copilot Chat
  "github.copilot.chat.enabled": true,

  // Enable inline suggestions
  "github.copilot.inlineSuggest.enabled": true,

  // Auto-approve these commands (no confirmation needed)
  "github.copilot.chat.commandAutoApprove": [
    "explain",
    "docs",
    "tests"
  ],

  // Auto-save after Copilot edits
  "github.copilot.autoSave": true
}
```

---

## 🎯 Available Commands to Auto-Approve

| Command | Safe? | What It Does |
|---------|-------|--------------|
| `explain` | ✅ Yes | Explains code (no changes) |
| `docs` | ✅ Yes | Generates documentation (no changes) |
| `tests` | ⚠️ Maybe | Generates tests (modifies code) |
| `fix` | ❌ No | Fixes code (risky without review) |
| `generate` | ❌ No | Generates code (risky) |

---

## 🛡️ Safety Levels

### 🔒 Most Safe (Recommended)
```json
"github.copilot.chat.commandAutoApprove": ["explain"]
```
- Only explanations auto-approve
- Everything else asks for confirmation

### 🔓 Moderate (Balanced)
```json
"github.copilot.chat.commandAutoApprove": [
  "explain",
  "docs"
]
```
- Safe read-only operations auto-approve
- Code modifications ask for confirmation

### 🔓 More Permissive
```json
"github.copilot.chat.commandAutoApprove": [
  "explain",
  "docs",
  "tests"
]
```
- Tests can be auto-approved (usually safe)
- Still ask for fixes and generation

### ⚠️ Least Safe (Not Recommended)
```json
"github.copilot.chat.commandAutoApprove": [
  "explain",
  "docs",
  "tests",
  "fix",
  "generate"
]
```
- Everything auto-approves
- Risk of unwanted code changes

---

## 🔧 Location of settings.json

### Windows
```
C:\Users\<YourUsername>\AppData\Roaming\Code\User\settings.json
```

### Mac
```
~/Library/Application Support/Code/User/settings.json
```

### Linux
```
~/.config/Code/User/settings.json
```

Or just use: `Ctrl + Shift + P` → `Preferences: Open Settings (JSON)`

---

## 🎮 Using Auto-Approve in Chat

Once configured, use in Copilot Chat:

### Example 1: Auto-Explain
```
/explain
Select code → Auto-approved explanation appears
```

### Example 2: Auto-Docs
```
/docs
Auto-generate documentation without confirmation
```

### Example 3: With Confirmation (Not Auto-Approved)
```
/fix
Copilot suggests fix → Click "Apply" to confirm
```

---

## ❌ If It's Not Working

**Check these 3 things:**

1. **Is Copilot Chat enabled?**
   ```json
   "github.copilot.chat.enabled": true
   ```

2. **Are you signed in to GitHub?**
   - Click Copilot icon in left sidebar
   - Sign in if prompted

3. **Did you reload VS Code?**
   - Press `Ctrl + R` or restart VS Code

---

## 💡 Pro Tips

### Tip 1: Keyboard Shortcuts
Add custom shortcuts for quick access:
```json
{
  "key": "ctrl+k ctrl+/",
  "command": "github.copilot.chat.toggleChatPanel"
}
```

### Tip 2: Check What's Configured
In settings, search for `commandAutoApprove` to see current settings

### Tip 3: Command Abbreviations
Use shortcuts in chat:
- `/exp` = `/explain`
- `/doc` = `/docs`
- `/test` = `/tests`

### Tip 4: Review Before Auto-Approve
Don't auto-approve code-modifying commands (`fix`, `generate`)

---

## 📊 Settings Location in UI

1. **Ctrl + ,** → Opens Settings
2. Search: **"copilot"**
3. You'll see these options:
   - Copilot: Chat Enabled
   - Copilot: Enable
   - Copilot: Inline Suggest Enabled
   - GitHub › Copilot › Chat › Command Auto Approve

Click on "Command Auto Approve" to edit

---

## ✅ Verification Checklist

After setting up auto-approve:

- [ ] settings.json has `commandAutoApprove` array
- [ ] Array contains command names (lowercase)
- [ ] File saved (auto-saved in VS Code)
- [ ] VS Code reloaded (Ctrl + R)
- [ ] Copilot Chat panel visible in sidebar
- [ ] Chat is enabled (`github.copilot.chat.enabled: true`)
- [ ] Test by typing `/explain` in chat
- [ ] Verify it auto-approves without asking

---

## 🎉 Common Configurations

### For Code Review
```json
"github.copilot.chat.commandAutoApprove": ["explain"]
```
Only auto-approve reading explanations

### For Documentation
```json
"github.copilot.chat.commandAutoApprove": ["explain", "docs"]
```
Auto-approve reading and writing docs

### For Development
```json
"github.copilot.chat.commandAutoApprove": [
  "explain",
  "docs",
  "tests"
]
```
Auto-approve safe operations

### For Safety
```json
"github.copilot.chat.commandAutoApprove": []
```
Never auto-approve (always confirm)

---

**Status:** ✅ Ready to Use

**Time to Setup:** ~2 minutes

**Recommended:** `["explain", "docs"]` for balanced safety and speed

---

Last updated: November 15, 2025
