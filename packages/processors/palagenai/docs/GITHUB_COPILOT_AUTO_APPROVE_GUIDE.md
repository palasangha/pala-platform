# 🤖 GitHub Copilot Auto-Approve Commands Configuration

## 📍 Overview

GitHub Copilot has auto-approve settings that control which commands it can automatically execute without requiring user confirmation. This guide explains how to configure these settings.

---

## 🎯 Where to Find Settings

### Option 1: VS Code Settings UI (Easiest)

1. **Open VS Code Settings**
   - Press `Ctrl + ,` (Windows/Linux) or `Cmd + ,` (Mac)
   - Or go to File → Preferences → Settings

2. **Search for Copilot**
   - In the search box at the top, type: `copilot`
   - You'll see Copilot-related settings appear

3. **Look for Auto-Approve Settings**
   - Search for: `copilot auto approve`
   - Or: `github.copilot`

### Option 2: Edit settings.json Directly

1. **Open settings.json**
   - Press `Ctrl + Shift + P` (Windows/Linux) or `Cmd + Shift + P` (Mac)
   - Type: `Preferences: Open Settings (JSON)`
   - Press Enter

2. **Add Copilot Configuration**
   ```json
   {
     "github.copilot.enable": {
       "*": true,
       "plaintext": false,
       "markdown": true
     },
     "github.copilot.chat.commandAutoApprove": [
       "explain"
     ]
   }
   ```

---

## 🔑 Key Copilot Settings

### Main Settings

| Setting | Type | Description |
|---------|------|-------------|
| `github.copilot.enable` | Object | Enable/disable Copilot for file types |
| `github.copilot.chat.enabled` | Boolean | Enable Copilot Chat |
| `github.copilot.autoSave` | Boolean | Auto-save files after Copilot suggestions |
| `github.copilot.commandAutoApprove` | Array | Commands that auto-approve without confirmation |

### Auto-Approve Commands

Commands that can be auto-approved:
- `"explain"` - Auto-approve explain suggestions
- `"tests"` - Auto-approve test generation
- `"fix"` - Auto-approve fix suggestions
- `"docs"` - Auto-approve documentation
- `"code"` - Auto-approve code generation

---

## 📝 Complete Configuration Example

Here's a comprehensive settings.json configuration:

```json
{
  // Copilot Enabled/Disabled per file type
  "github.copilot.enable": {
    "*": true,
    "plaintext": false,
    "markdown": false,
    "scminput": false
  },

  // Chat settings
  "github.copilot.chat.enabled": true,

  // Auto-save after Copilot edits
  "github.copilot.autoSave": true,

  // Commands that auto-approve (no confirmation needed)
  "github.copilot.chat.commandAutoApprove": [
    "explain",
    "docs",
    "tests"
  ],

  // Inline suggestions settings
  "github.copilot.inlineSuggest.enabled": true,

  // Keyboard shortcuts for Copilot
  "github.copilot.chat.openSymbolFromEditor.experimental": true
}
```

---

## 🎮 Command Abbreviations

You can use Copilot chat with these commands:

| Command | Abbreviation | Effect |
|---------|--------------|--------|
| `/explain` | `/exp` | Explain the selected code |
| `/tests` | `/test` | Generate tests for code |
| `/fix` | `/fix` | Fix bugs in code |
| `/docs` | `/doc` | Generate documentation |
| `/generate` | `/gen` | Generate code |

**Example in Copilot Chat:**
```
/explain - Explains selected code
/tests - Auto-generates tests (if in auto-approve list)
/fix - Auto-applies fixes (if in auto-approve list)
```

---

## ⚙️ Step-by-Step: Enable Auto-Approve for Specific Commands

### Method 1: Using Settings UI

1. Open VS Code Settings (Ctrl + ,)
2. Search: `github.copilot.chat.commandAutoApprove`
3. Click "Edit in settings.json"
4. Add commands to the array:
   ```json
   "github.copilot.chat.commandAutoApprove": [
     "explain",
     "docs",
     "tests"
   ]
   ```
5. Save the file
6. Reload VS Code window (Ctrl + R)

### Method 2: Direct JSON Edit

1. Press `Ctrl + Shift + P`
2. Type: `Preferences: Open Settings (JSON)`
3. Find or add the section:
   ```json
   "github.copilot.chat.commandAutoApprove": ["explain", "docs", "tests"]
   ```
4. Save (Ctrl + S)
5. Reload window (Ctrl + R)

---

## 🔍 Common Auto-Approve Scenarios

### Scenario 1: Auto-Approve Explanations Only
```json
"github.copilot.chat.commandAutoApprove": ["explain"]
```
- Use `/explain` - Will auto-approve without confirmation
- Use `/tests` - Will ask for confirmation

### Scenario 2: Auto-Approve All Safe Commands
```json
"github.copilot.chat.commandAutoApprove": [
  "explain",
  "docs",
  "tests"
]
```
- Safe commands auto-approve
- `fix` still requires confirmation (safety)

### Scenario 3: Disable Auto-Approve (Safest)
```json
"github.copilot.chat.commandAutoApprove": []
```
- All commands require confirmation
- More control but slower workflow

### Scenario 4: Auto-Approve Everything (Fastest)
```json
"github.copilot.chat.commandAutoApprove": [
  "explain",
  "docs",
  "tests",
  "fix",
  "generate"
]
```
⚠️ **Warning:** Be careful with this - fixes and generation will apply without review

---

## 🔐 Safety Recommendations

### Recommended Settings (Balanced)
```json
{
  "github.copilot.chat.enabled": true,
  "github.copilot.inlineSuggest.enabled": true,
  "github.copilot.chat.commandAutoApprove": [
    "explain",
    "docs"
  ]
}
```

**Why this is safe:**
- ✅ `explain` - Non-modifying, safe to auto-approve
- ✅ `docs` - Non-modifying, safe to auto-approve
- ❌ `tests` - Requires confirmation (can change code)
- ❌ `fix` - Requires confirmation (important changes)
- ❌ `generate` - Requires confirmation (new code)

### Conservative Settings (Safest)
```json
{
  "github.copilot.chat.commandAutoApprove": [
    "explain"
  ]
}
```

Only auto-approve the safest operations.

---

## 🖱️ Manual vs Auto-Approve Workflow

### Without Auto-Approve
```
1. Type /explain
2. Copilot generates explanation
3. Click "Apply" button to confirm
4. Explanation appears
```

### With Auto-Approve
```
1. Type /explain
2. Copilot generates explanation
3. Automatically applies (no click needed)
4. Explanation appears
```

---

## 🔧 Advanced Configuration

### Disable Copilot for Specific File Types
```json
{
  "github.copilot.enable": {
    "*": true,
    "plaintext": false,
    "markdown": false,
    "scminput": false,
    "gitcommit": false
  }
}
```

### Keyboard Shortcuts for Quick Access
```json
{
  "key": "ctrl+k ctrl+/",
  "command": "github.copilot.chat.toggleChatPanel"
},
{
  "key": "ctrl+shift+/",
  "command": "github.copilot.chat.explainSelection"
}
```

### Inline Suggestion Settings
```json
{
  "github.copilot.inlineSuggest.enabled": true,
  "github.copilot.inlineSuggest.asQuickSuggest": false,
  "editor.inlineSuggest.enabled": true
}
```

---

## 🆘 Troubleshooting

### Auto-Approve Not Working?

1. **Check if Copilot is enabled:**
   ```json
   "github.copilot.enable": {
     "*": true
   }
   ```

2. **Check chat is enabled:**
   ```json
   "github.copilot.chat.enabled": true
   ```

3. **Verify command list syntax:**
   ```json
   "github.copilot.chat.commandAutoApprove": [
     "explain",
     "docs"
   ]
   ```
   (Must be array with lowercase command names)

4. **Reload VS Code:**
   - Press `Ctrl + R` (Windows/Linux)
   - Or `Cmd + Shift + P` then type "Reload Window"

5. **Check Copilot Chat panel:**
   - Look for Chat icon in left sidebar
   - Verify Copilot Chat is enabled

### Commands Not Appearing?

1. Make sure you have Copilot Chat extension installed
2. Verify you're authenticated with GitHub
3. Check that chat.enabled is true
4. Check command spelling (must be lowercase)

---

## 📚 Related Settings

### Editor Suggestions
```json
{
  "editor.inlineSuggest.enabled": true,
  "editor.quickSuggestionsDelay": 300,
  "editor.acceptSuggestionOnCommitCharacter": true
}
```

### Performance
```json
{
  "github.copilot.advanced": {
    "debug.overrideCopilotOfferingId": "ghcopilot-user"
  }
}
```

### Privacy
```json
{
  "telemetry.telemetryLevel": "off"
}
```

---

## 🎯 Quick Setup Guide

### For Development Teams

**Recommended settings.json:**
```json
{
  "github.copilot.enable": {
    "*": true,
    "markdown": false,
    "plaintext": false
  },
  "github.copilot.chat.enabled": true,
  "github.copilot.inlineSuggest.enabled": true,
  "github.copilot.chat.commandAutoApprove": [
    "explain",
    "docs"
  ],
  "github.copilot.autoSave": true
}
```

**Benefits:**
- ✅ Copilot enabled for code files
- ✅ Disabled for docs/plaintext (less useful)
- ✅ Chat enabled
- ✅ Inline suggestions enabled
- ✅ Safe commands auto-approve
- ✅ Auto-save enabled

---

## 📋 Settings Checklist

- [ ] Copilot extension installed
- [ ] Authenticated with GitHub account
- [ ] `github.copilot.enable` set to true for desired file types
- [ ] `github.copilot.chat.enabled` set to true
- [ ] `github.copilot.chat.commandAutoApprove` configured
- [ ] Changes saved to settings.json
- [ ] VS Code reloaded (Ctrl + R)
- [ ] Chat panel visible in left sidebar
- [ ] Commands working in chat

---

## 🔗 Useful Resources

- [GitHub Copilot Documentation](https://docs.github.com/en/copilot)
- [VS Code Settings Reference](https://code.visualstudio.com/docs/getstarted/settings)
- [Copilot Chat Commands](https://github.com/github/copilot-docs)

---

## Summary

To edit GitHub Copilot auto-approve commands:

1. **Open Settings:** `Ctrl + ,`
2. **Search:** `copilot auto approve`
3. **Find:** `github.copilot.chat.commandAutoApprove`
4. **Edit:** Add command names to the array
5. **Save:** File saves automatically
6. **Reload:** `Ctrl + R` to apply changes

Example safe configuration:
```json
"github.copilot.chat.commandAutoApprove": ["explain", "docs"]
```

**Status:** ✅ Ready to Configure

---

**Last Updated:** November 15, 2025
