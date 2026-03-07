# ⚙️ Complete VS Code & Project Settings Guide

## 📋 Overview

This guide covers all settings for your VS Code workspace and GitHub Copilot configuration.

---

## 🤖 GitHub Copilot Settings

### Quick Reference Table

| Setting | Value | Description |
|---------|-------|-------------|
| `github.copilot.enable` | `{"*": true}` | Enable Copilot for all file types |
| `github.copilot.chat.enabled` | `true` | Enable Copilot Chat feature |
| `github.copilot.inlineSuggest.enabled` | `true` | Show inline code suggestions |
| `github.copilot.chat.commandAutoApprove` | `["explain"]` | Auto-approve explain command |
| `github.copilot.autoSave` | `true` | Auto-save after Copilot edits |

### Recommended Configuration

```json
{
  // === COPILOT CORE SETTINGS ===
  "github.copilot.enable": {
    "*": true,                    // Enable for all files
    "plaintext": false,           // Disable for plaintext
    "markdown": false,            // Disable for markdown
    "scminput": false             // Disable for git commits
  },

  // === COPILOT CHAT SETTINGS ===
  "github.copilot.chat.enabled": true,
  "github.copilot.chat.commandAutoApprove": [
    "explain",
    "docs"
  ],

  // === INLINE SUGGESTIONS ===
  "github.copilot.inlineSuggest.enabled": true,
  "github.copilot.inlineSuggest.asQuickSuggest": false,

  // === AUTO-SAVE ===
  "github.copilot.autoSave": true
}
```

---

## 💻 Editor Settings

### Essential Editor Configuration

```json
{
  // === APPEARANCE ===
  "editor.theme": "One Dark Pro",
  "editor.fontSize": 14,
  "editor.lineHeight": 1.6,
  "editor.fontFamily": "Fira Code, 'Courier New'",
  "editor.fontLigatures": true,

  // === INDENTATION ===
  "editor.tabSize": 2,
  "editor.insertSpaces": true,
  "editor.autoIndent": "full",

  // === WORD WRAP ===
  "editor.wordWrap": "on",
  "editor.wordWrapColumn": 100,

  // === FORMATTING ===
  "editor.formatOnSave": true,
  "editor.formatOnPaste": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",

  // === SUGGESTIONS ===
  "editor.quickSuggestionsDelay": 300,
  "editor.suggestSelection": "first",
  "editor.acceptSuggestionOnCommitCharacter": true,

  // === CODE FOLDING ===
  "editor.foldingStrategy": "indentation",
  "editor.unfoldOnClickAfterEndOfLine": true,

  // === RULERS & GUIDES ===
  "editor.rulers": [80, 100, 120],
  "editor.renderIndentGuides": true,
  "editor.renderWhitespace": "selection",

  // === MINIMAP ===
  "editor.minimap.enabled": true,
  "editor.minimap.maxColumn": 120
}
```

---

## 🎨 Theme & Appearance Settings

### Recommended Themes

```json
{
  // Color theme
  "workbench.colorTheme": "One Dark Pro",
  
  // Icon theme
  "workbench.iconTheme": "vs-code-icons",
  
  // Font settings
  "editor.fontFamily": "Fira Code",
  "editor.fontSize": 14,
  "editor.fontWeight": "500",
  "editor.fontLigatures": true,

  // Bracket colors
  "editor.bracketPairColorization.enabled": true,
  "editor.guides.bracketPairs": "active"
}
```

---

## 🧹 Format & Lint Settings

### Prettier Configuration

```json
{
  "[javascript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[json]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.python"
  },

  "prettier.semi": true,
  "prettier.singleQuote": true,
  "prettier.trailingComma": "es5",
  "prettier.printWidth": 100,
  "prettier.tabWidth": 2
}
```

### ESLint Configuration

```json
{
  "eslint.enable": true,
  "eslint.run": "onSave",
  "eslint.validate": [
    "javascript",
    "typescript",
    "javascriptreact",
    "typescriptreact"
  ],
  "eslint.format.enable": true,
  "eslint.codeActionsOnSave": {
    "source.fixAll.eslint": "explicit"
  }
}
```

---

## 🐍 Python Settings

### Python Extension Configuration

```json
{
  "[python]": {
    "editor.defaultFormatter": "ms-python.python",
    "editor.formatOnSave": true,
    "editor.rulers": [79, 120],
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    }
  },

  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.pylintPath": "pylint",
  "python.formatting.provider": "black",
  "python.formatting.blackPath": "black",

  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.inlayHints.functionReturnTypes": true,
  "python.analysis.inlayHints.variableTypes": true
}
```

---

## 🔧 Language-Specific Settings

### TypeScript Settings

```json
{
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit",
      "source.fixAll.eslint": "explicit"
    }
  },

  "typescript.tsdk": "node_modules/typescript/lib",
  "typescript.enablePromptUseWorkspaceTsdk": true,
  "typescript.preferences.quotePreference": "single",
  "typescript.preferences.importModuleSpecifierEnding": "auto"
}
```

### React Settings

```json
{
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  },

  "extensions.recommendations": [
    "ES7-React-JS-Snippets",
    "ES7-React-Redux-GraphQL-React-Native-Snippets"
  ]
}
```

### JSON Settings

```json
{
  "[json]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true,
    "editor.tabSize": 2
  },

  "[jsonc]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  }
}
```

---

## 📁 Files & Folders Settings

### File Explorer Configuration

```json
{
  // Hide unnecessary files
  "files.exclude": {
    "**/.DS_Store": true,
    "**/.git": false,
    "**/.gitignore": false,
    "**/__pycache__": true,
    "**/*.pyc": true,
    "**/node_modules": true,
    "**/.env": false,
    "**/dist": false,
    "**/build": false
  },

  // File associations
  "files.associations": {
    "*.env.example": "env",
    "*.tsx": "typescriptreact",
    "*.jsx": "javascriptreact",
    "Dockerfile*": "dockerfile"
  },

  // Auto-save
  "files.autoSave": "afterDelay",
  "files.autoSaveDelay": 1000,

  // Default encoding
  "files.encoding": "utf8",
  "files.eol": "\n"
}
```

---

## 🔍 Search & Replace Settings

### Search Configuration

```json
{
  "search.include": [
    "**/*.ts",
    "**/*.tsx",
    "**/*.py",
    "**/*.json",
    "**/*.md"
  ],
  "search.exclude": [
    "**/node_modules": true,
    "**/.git": true,
    "**/__pycache__": true,
    "**/venv": true,
    "**/.env": true,
    "**/dist": true,
    "**/build": true
  },
  "search.smartCase": true,
  "search.followSymlinks": true
}
```

---

## 🖥️ Terminal Settings

### Terminal Configuration

```json
{
  "terminal.integrated.defaultProfile.linux": "bash",
  "terminal.integrated.defaultProfile.windows": "PowerShell",
  "terminal.integrated.defaultProfile.osx": "bash",
  "terminal.integrated.fontSize": 14,
  "terminal.integrated.lineHeight": 1.4,
  "terminal.integrated.inheritEnv": true,
  "terminal.integrated.scrollback": 1000,
  "terminal.integrated.copyOnSelection": true,
  "terminal.integrated.enableMultiLinePasteWarning": false
}
```

---

## 🔐 Security & Privacy Settings

### Security Configuration

```json
{
  // Telemetry
  "telemetry.telemetryLevel": "off",

  // Security
  "security.workspace.trust.untrustedFiles": "open",
  "extensions.verifySignature": true,

  // Git
  "git.autofetch": true,
  "git.confirmSync": false,
  "git.ignoreLimitWarning": true
}
```

---

## 🚀 Performance Settings

### Optimization Configuration

```json
{
  // File watching
  "files.watcherExclude": {
    "**/.git/objects/**": true,
    "**/.git/subtree-cache/**": true,
    "**/node_modules/**": true,
    "**/.venv/**": true,
    "**/venv/**": true,
    "**/__pycache__/**": true
  },

  // Search limits
  "search.maxResults": 1000,

  // Rendering
  "editor.experimental.asyncTokenization": true,
  "editor.codeActionsOnSaveTimeout": 750
}
```

---

## 🔗 Extension Settings

### Recommended Extensions

```json
{
  "extensions.ignoreRecommendations": false,
  "extensions.recommendations": [
    "GitHub.copilot",
    "GitHub.copilot-chat",
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-vscode-remote.remote-containers",
    "Docker",
    "ms-vscode.makefile-tools",
    "eamodio.gitlens"
  ]
}
```

---

## 🎯 Workspace-Specific Settings

### For Your GVPOCR Project

Create `.vscode/settings.json` in your project:

```json
{
  // === PROJECT-SPECIFIC SETTINGS ===
  "folders": [
    {
      "path": "."
    }
  ],

  // === FRONTEND (React/TypeScript) ===
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  },

  // === BACKEND (Python) ===
  "[python]": {
    "editor.defaultFormatter": "ms-python.python",
    "editor.formatOnSave": true
  },

  // === PROJECT FILES ===
  "files.exclude": {
    "**/__pycache__": true,
    "**/node_modules": true,
    "**/.env": false,
    "backend/uploads/**": false
  }
}
```

---

## ✅ Complete settings.json Template

Here's a complete settings file you can copy:

```json
{
  // === COPILOT ===
  "github.copilot.enable": {
    "*": true,
    "plaintext": false,
    "markdown": false
  },
  "github.copilot.chat.enabled": true,
  "github.copilot.chat.commandAutoApprove": ["explain", "docs"],
  "github.copilot.inlineSuggest.enabled": true,
  "github.copilot.autoSave": true,

  // === EDITOR ===
  "editor.fontSize": 14,
  "editor.tabSize": 2,
  "editor.insertSpaces": true,
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.wordWrap": "on",
  "editor.rulers": [80, 100],
  "editor.fontFamily": "Fira Code",
  "editor.fontLigatures": true,

  // === FILES ===
  "files.autoSave": "afterDelay",
  "files.autoSaveDelay": 1000,
  "files.encoding": "utf8",
  "files.eol": "\n",

  // === PRETTIER ===
  "prettier.semi": true,
  "prettier.singleQuote": true,
  "prettier.trailingComma": "es5",
  "prettier.printWidth": 100,

  // === ESLINT ===
  "eslint.enable": true,
  "eslint.run": "onSave",

  // === PYTHON ===
  "[python]": {
    "editor.defaultFormatter": "ms-python.python",
    "editor.formatOnSave": true
  },

  // === TERMINAL ===
  "terminal.integrated.fontSize": 14,

  // === SECURITY ===
  "telemetry.telemetryLevel": "off"
}
```

---

## 📊 Settings Priority

Settings are applied in this order (highest to lowest priority):

1. **User Settings** - Your personal VS Code settings
2. **Remote Settings** - Settings on remote machine
3. **Workspace Settings** - Project-specific settings
4. **Folder Settings** - Individual folder settings
5. **Default Settings** - VS Code defaults

---

## 🔄 Syncing Settings Across Devices

### Enable Settings Sync

1. Press `Ctrl + Shift + P`
2. Type: `Settings Sync: Turn On`
3. Sign in with GitHub
4. Choose what to sync:
   - ✅ Settings
   - ✅ Extensions
   - ✅ Keybindings
   - ✅ Snippets

---

## 📝 Useful Commands

```bash
# Open settings
Ctrl + ,

# Open settings.json
Ctrl + Shift + P → Preferences: Open Settings (JSON)

# Format document
Ctrl + Shift + F

# Fix all ESLint issues
Ctrl + Shift + P → ESLint: Fix all auto-fixable problems

# Python format
Ctrl + Shift + P → Python: Format document
```

---

## ✅ Settings Checklist

- [ ] Copilot enabled
- [ ] Copilot Chat enabled
- [ ] Auto-approve configured
- [ ] Editor settings configured
- [ ] Formatter set to Prettier
- [ ] ESLint enabled
- [ ] Python formatter configured
- [ ] Auto-save enabled
- [ ] File encoding set to UTF-8
- [ ] Telemetry disabled (privacy)

---

## 📚 Additional Resources

- [VS Code Settings Documentation](https://code.visualstudio.com/docs/getstarted/settings)
- [Prettier Configuration](https://prettier.io/docs/en/options.html)
- [ESLint Configuration](https://eslint.org/docs/rules/)
- [Python Extension Guide](https://code.visualstudio.com/docs/languages/python)

---

**Status:** ✅ Complete Reference Guide

**Last Updated:** November 15, 2025

