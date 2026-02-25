"""
Pala Jarvis Service - AI Agent with Full Codebase Access

Provides a Claude Code-like experience in the web interface, with tools for:
- Reading/writing files
- Executing bash commands
- Searching code
- Full project context
"""

import os
import subprocess
import json
import glob as glob_module
import re
from pathlib import Path
from typing import List, Dict, Optional, Any
from flask import current_app
try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import openai
except ImportError:
    openai = None


class PalaJarvisService:
    """Pala Jarvis - Samma AI's project management assistant with full codebase access."""

    def __init__(self):
        self._claude_client = None
        self._openrouter_client = None
        self.project_root = Path(__file__).parent.parent.parent.parent  # samma_ai root
        self.max_file_size = 10 * 1024 * 1024  # 10MB max file size
        self.use_openrouter = os.environ.get('USE_OPENROUTER', 'true').lower() == 'true'

    def _get_claude_client(self):
        """Get or create Claude API client."""
        if self._claude_client is None:
            if not anthropic:
                raise RuntimeError('anthropic package not installed')
            api_key = current_app.config.get('ANTHROPIC_API_KEY')
            if not api_key:
                raise RuntimeError('ANTHROPIC_API_KEY not configured')
            self._claude_client = anthropic.Anthropic(api_key=api_key)
        return self._claude_client

    def _get_openrouter_client(self):
        """Get or create OpenRouter client (OpenAI-compatible)."""
        if self._openrouter_client is None:
            if not openai:
                raise RuntimeError('openai package not installed')
            api_key = os.environ.get('OPENROUTER_API_KEY') or current_app.config.get('OPENROUTER_API_KEY')
            if not api_key:
                raise RuntimeError('OPENROUTER_API_KEY not configured. Get one at https://openrouter.ai/keys')

            self._openrouter_client = openai.OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
                default_headers={
                    "HTTP-Referer": "https://samma-ai.local",
                    "X-Title": "Samma AI - Pala Jarvis",
                }
            )
        return self._openrouter_client

    def _create_oauth_client(self, session_token: str):
        """Create Claude client using OAuth token."""
        if not anthropic:
            raise RuntimeError('anthropic package not installed')

        # The session_token is the OAuth access token
        return anthropic.Anthropic(api_key=session_token)

    def _get_system_prompt(self) -> str:
        """Get system prompt with full project context."""
        # Read CLAUDE.md
        claude_md_path = self.project_root / '.claude' / 'CLAUDE.md'
        soul_md_path = self.project_root / 'docs' / 'SOUL.md'

        claude_md = ""
        soul_md = ""

        if claude_md_path.exists():
            with open(claude_md_path, 'r', encoding='utf-8') as f:
                claude_md = f.read()

        if soul_md_path.exists():
            with open(soul_md_path, 'r', encoding='utf-8') as f:
                soul_md = f.read()

        return f"""You are Pala Jarvis, the autonomous project management AI for Samma AI.

# Your Identity

You are an AI assistant with FULL codebase access. You can:
- Read any file in the project
- Write/edit files
- Execute bash commands
- Search code with glob/grep patterns
- Manage the entire Samma AI platform

# Project Context

{claude_md}

# Samma AI Soul (Complete Identity)

{soul_md}

# Your Capabilities

You have access to these tools:
1. **read_file** - Read any file from the codebase
2. **write_file** - Create or overwrite a file
3. **edit_file** - Make targeted edits to existing files
4. **execute_bash** - Run bash commands (be careful!)
5. **glob_search** - Find files by pattern (e.g., "**/*.py")
6. **grep_search** - Search file contents with regex

# Guidelines

- Always use tools to access/modify the codebase
- Read files before editing them
- Provide clear explanations of what you're doing
- Be cautious with bash commands (no destructive operations without confirmation)
- Focus on helping with Samma AI development and operations
- Follow the 4-part Dhamma response protocol when appropriate

Project root: {self.project_root}
"""

    def _get_tools_schema(self) -> List[Dict]:
        """Define tool schemas for Claude API."""
        return [
            {
                "name": "read_file",
                "description": "Read the contents of a file from the codebase. Returns file contents with line numbers.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Relative path from project root (e.g., 'backend/app/routes/chat.py')"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "write_file",
                "description": "Create or completely overwrite a file. Use edit_file for targeted changes.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Relative path from project root"
                        },
                        "content": {
                            "type": "string",
                            "description": "Complete file contents to write"
                        }
                    },
                    "required": ["file_path", "content"]
                }
            },
            {
                "name": "edit_file",
                "description": "Make targeted edits to an existing file by replacing specific text.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Relative path from project root"
                        },
                        "old_text": {
                            "type": "string",
                            "description": "Exact text to find and replace (must be unique in file)"
                        },
                        "new_text": {
                            "type": "string",
                            "description": "New text to insert in place of old_text"
                        }
                    },
                    "required": ["file_path", "old_text", "new_text"]
                }
            },
            {
                "name": "execute_bash",
                "description": "Execute a bash command. Be careful - this runs with full system access!",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Bash command to execute"
                        },
                        "working_dir": {
                            "type": "string",
                            "description": "Working directory (relative to project root, optional)"
                        }
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "glob_search",
                "description": "Find files matching a glob pattern (e.g., '**/*.py' for all Python files).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Glob pattern (e.g., '**/*.dart', 'backend/app/services/*.py')"
                        }
                    },
                    "required": ["pattern"]
                }
            },
            {
                "name": "grep_search",
                "description": "Search file contents using regex. Returns matching lines with file paths.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Regex pattern to search for"
                        },
                        "file_pattern": {
                            "type": "string",
                            "description": "Limit search to files matching this glob (e.g., '**/*.py')"
                        },
                        "case_sensitive": {
                            "type": "boolean",
                            "description": "Case-sensitive search (default: false)"
                        }
                    },
                    "required": ["pattern"]
                }
            }
        ]

    def _execute_tool(self, tool_name: str, tool_input: Dict) -> str:
        """Execute a tool and return result."""
        try:
            if tool_name == "read_file":
                return self._tool_read_file(tool_input["file_path"])
            elif tool_name == "write_file":
                return self._tool_write_file(tool_input["file_path"], tool_input["content"])
            elif tool_name == "edit_file":
                return self._tool_edit_file(
                    tool_input["file_path"],
                    tool_input["old_text"],
                    tool_input["new_text"]
                )
            elif tool_name == "execute_bash":
                return self._tool_execute_bash(
                    tool_input["command"],
                    tool_input.get("working_dir", "")
                )
            elif tool_name == "glob_search":
                return self._tool_glob_search(tool_input["pattern"])
            elif tool_name == "grep_search":
                return self._tool_grep_search(
                    tool_input["pattern"],
                    tool_input.get("file_pattern", "**/*"),
                    tool_input.get("case_sensitive", False)
                )
            else:
                return f"Error: Unknown tool '{tool_name}'"
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"

    def _tool_read_file(self, file_path: str) -> str:
        """Read file with line numbers."""
        full_path = self.project_root / file_path

        if not full_path.exists():
            return f"Error: File not found: {file_path}"

        if full_path.stat().st_size > self.max_file_size:
            return f"Error: File too large (>{self.max_file_size} bytes): {file_path}"

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Add line numbers
            numbered_lines = [f"{i+1:4d} | {line.rstrip()}" for i, line in enumerate(lines)]
            return f"File: {file_path}\n" + "\n".join(numbered_lines)
        except UnicodeDecodeError:
            return f"Error: Cannot read binary file: {file_path}"

    def _tool_write_file(self, file_path: str, content: str) -> str:
        """Write file (create or overwrite)."""
        full_path = self.project_root / file_path

        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote {len(content)} bytes to {file_path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"

    def _tool_edit_file(self, file_path: str, old_text: str, new_text: str) -> str:
        """Edit file by replacing text."""
        full_path = self.project_root / file_path

        if not full_path.exists():
            return f"Error: File not found: {file_path}"

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if old_text not in content:
                return f"Error: old_text not found in {file_path}"

            # Check if old_text appears multiple times
            count = content.count(old_text)
            if count > 1:
                return f"Error: old_text appears {count} times in {file_path}. Must be unique."

            new_content = content.replace(old_text, new_text)

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return f"Successfully edited {file_path} (replaced {len(old_text)} chars with {len(new_text)} chars)"
        except Exception as e:
            return f"Error editing file: {str(e)}"

    def _tool_execute_bash(self, command: str, working_dir: str = "") -> str:
        """Execute bash command."""
        # Security: Prevent some dangerous commands
        dangerous_patterns = [
            r'\brm\s+-rf\s+/',
            r'\brm\s+-rf\s+\*',
            r'>\s*/dev/sda',
            r'\bdd\s+',
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, command):
                return f"Error: Potentially dangerous command blocked: {command}"

        cwd = self.project_root / working_dir if working_dir else self.project_root

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30
            )

            output = f"Exit code: {result.returncode}\n"
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"

            return output
        except subprocess.TimeoutExpired:
            return "Error: Command timed out (>30s)"
        except Exception as e:
            return f"Error executing command: {str(e)}"

    def _tool_glob_search(self, pattern: str) -> str:
        """Search for files matching glob pattern."""
        try:
            matches = glob_module.glob(str(self.project_root / pattern), recursive=True)

            # Make paths relative to project root
            relative_matches = [
                str(Path(m).relative_to(self.project_root))
                for m in matches
                if Path(m).is_file()
            ]

            if not relative_matches:
                return f"No files found matching pattern: {pattern}"

            return f"Found {len(relative_matches)} files:\n" + "\n".join(relative_matches[:100])
        except Exception as e:
            return f"Error searching: {str(e)}"

    def _tool_grep_search(self, pattern: str, file_pattern: str = "**/*", case_sensitive: bool = False) -> str:
        """Search file contents with regex."""
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)

            # Find files to search
            files = glob_module.glob(str(self.project_root / file_pattern), recursive=True)
            files = [f for f in files if Path(f).is_file()]

            results = []
            for file_path in files[:1000]:  # Limit to first 1000 files
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                rel_path = str(Path(file_path).relative_to(self.project_root))
                                results.append(f"{rel_path}:{line_num}: {line.rstrip()}")
                                if len(results) >= 100:  # Limit results
                                    break
                except (UnicodeDecodeError, PermissionError):
                    continue

                if len(results) >= 100:
                    break

            if not results:
                return f"No matches found for pattern: {pattern}"

            return f"Found {len(results)} matches:\n" + "\n".join(results)
        except Exception as e:
            return f"Error searching: {str(e)}"

    def chat(self, message: str, conversation_history: List[Dict] = None, session_token: str = None) -> Dict:
        """
        Chat with Pala Jarvis with full codebase access.

        Args:
            message: User's message
            conversation_history: Previous messages (optional)
            session_token: OAuth session token (optional)

        Returns:
            Dict with 'response', 'tool_calls', 'conversation'
        """
        # Use OAuth token if available, otherwise fall back to API key
        if session_token:
            client = self._create_oauth_client(session_token)
        elif self.use_openrouter:
            return self._chat_with_openrouter(message, conversation_history)
        else:
            client = self._get_claude_client()

        # Build messages
        messages = conversation_history or []
        messages.append({
            "role": "user",
            "content": message
        })

        # System prompt
        system_prompt = self._get_system_prompt()

        # Tools
        tools = self._get_tools_schema()

        # Call Claude with tools (agentic loop)
        max_iterations = 10
        iteration = 0
        tool_calls_log = []

        while iteration < max_iterations:
            iteration += 1

            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",  # Sonnet 4.5
                max_tokens=4096,
                system=system_prompt,
                tools=tools,
                messages=messages
            )

            # Add assistant response to messages
            assistant_message = {
                "role": "assistant",
                "content": response.content
            }
            messages.append(assistant_message)

            # Check if Claude wants to use tools
            if response.stop_reason == "end_turn":
                # Done - extract text response
                text_content = ""
                for block in response.content:
                    if block.type == "text":
                        text_content += block.text

                return {
                    "response": text_content,
                    "tool_calls": tool_calls_log,
                    "conversation": messages,
                    "stop_reason": "complete"
                }

            elif response.stop_reason == "tool_use":
                # Execute tools
                tool_results = []

                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tool_id = block.id

                        # Execute tool
                        result = self._execute_tool(tool_name, tool_input)

                        # Log tool call
                        tool_calls_log.append({
                            "tool": tool_name,
                            "input": tool_input,
                            "result": result[:500]  # Truncate for logging
                        })

                        # Add tool result
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": result
                        })

                # Add tool results to messages
                messages.append({
                    "role": "user",
                    "content": tool_results
                })

                # Continue loop to get next response
            else:
                # Unexpected stop reason
                return {
                    "response": f"Unexpected stop reason: {response.stop_reason}",
                    "tool_calls": tool_calls_log,
                    "conversation": messages,
                    "stop_reason": response.stop_reason
                }

        return {
            "response": "Max iterations reached. Please try again with a simpler request.",
            "tool_calls": tool_calls_log,
            "conversation": messages,
            "stop_reason": "max_iterations"
        }
