import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

/// Pala Jarvis Chat View - Full codebase access
class PalaJarvisView extends StatefulWidget {
  const PalaJarvisView({super.key});

  @override
  State<PalaJarvisView> createState() => _PalaJarvisViewState();
}

class _PalaJarvisViewState extends State<PalaJarvisView> {
  final _messageController = TextEditingController();
  final _scrollController = ScrollController();
  final _messages = <_ChatMessage>[];
  String? _conversationId;
  String? _sessionId;  // OAuth session ID
  bool _isLoading = false;
  bool _isSending = false;
  bool _isAuthenticated = false;

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    _loadSessionId();
    _checkAuthStatus();
  }

  Future<void> _loadSessionId() async {
    // Load session ID from localStorage if exists
    try {
      final prefs = await SharedPreferences.getInstance();
      _sessionId = prefs.getString('claude_session_id');
    } catch (e) {
      debugPrint('Error loading session ID: $e');
    }
  }

  Future<void> _saveSessionId(String sessionId) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('claude_session_id', sessionId);
      _sessionId = sessionId;
    } catch (e) {
      debugPrint('Error saving session ID: $e');
    }
  }

  Future<void> _checkAuthStatus() async {
    if (_sessionId == null) {
      setState(() => _isAuthenticated = false);
      return;
    }

    try {
      final response = await http.get(
        Uri.parse('http://localhost:5001/api/auth/claude/status'),
        headers: {'X-Session-ID': _sessionId!},
      );

      if (response.statusCode == 200 && mounted) {
        final data = json.decode(response.body);
        setState(() {
          _isAuthenticated = data['authenticated'] == true;
        });

        if (_isAuthenticated) {
          _loadConversations();
        }
      }
    } catch (e) {
      debugPrint('Error checking auth status: $e');
      setState(() => _isAuthenticated = false);
    }
  }

  Future<void> _loginWithClaude() async {
    try {
      // Get OAuth URL from backend
      final response = await http.get(
        Uri.parse('http://localhost:5001/api/auth/claude/login'),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final authUrl = data['auth_url'] as String;

        // Open OAuth popup
        // In Flutter web, we can use url_launcher or window.open
        if (mounted) {
          _showInfo('Opening Claude login in new window...');
        }

        // For Flutter web, we need to use dart:html
        // This is a simplified version - in production use url_launcher
        await launchUrl(Uri.parse(authUrl));

        // Listen for auth success message (from postMessage in callback)
        // In Flutter web, you'd use window.addEventListener('message', ...)
        // For now, show instructions
        if (mounted) {
          _showInfo('After logging in, you\'ll be redirected back here.');
        }
      }
    } catch (e) {
      debugPrint('Login error: $e');
      _showError('Login failed: $e');
    }
  }

  Future<void> _logout() async {
    try {
      if (_sessionId != null) {
        await http.post(
          Uri.parse('http://localhost:5001/api/auth/claude/logout'),
          headers: {'X-Session-ID': _sessionId!},
        );
      }

      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('claude_session_id');

      setState(() {
        _sessionId = null;
        _isAuthenticated = false;
        _messages.clear();
        _conversationId = null;
      });
    } catch (e) {
      debugPrint('Logout error: $e');
    }
  }

  Future<void> _loadConversations() async {
    setState(() => _isLoading = true);

    try {
      final response = await http.get(
        Uri.parse('http://localhost:5001/api/agents/pala-jarvis/conversations'),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final conversations = data['conversations'] as List;

        if (conversations.isNotEmpty && mounted) {
          // Load the most recent conversation
          final mostRecent = conversations.first;
          _conversationId = mostRecent['conversation_id'] as String?;

          // TODO: Load full conversation messages if needed
        }
      }
    } catch (e) {
      debugPrint('Error loading conversations: $e');
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _sendMessage() async {
    if (_messageController.text.trim().isEmpty || _isSending) return;

    final userMessage = _messageController.text.trim();
    _messageController.clear();

    setState(() {
      _messages.add(_ChatMessage(
        role: 'user',
        content: userMessage,
        timestamp: DateTime.now(),
      ));
      _isSending = true;
    });

    // Scroll to bottom
    Future.delayed(const Duration(milliseconds: 100), () {
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    });

    try {
      final headers = {
        'Content-Type': 'application/json',
        if (_sessionId != null) 'X-Session-ID': _sessionId!,
      };

      final response = await http.post(
        Uri.parse('http://localhost:5001/api/agents/pala-jarvis/chat'),
        headers: headers,
        body: json.encode({
          'message': userMessage,
          'conversation_id': _conversationId,
        }),
      );

      if (response.statusCode == 200 && mounted) {
        final data = json.decode(response.body);
        _conversationId = data['conversation_id'] as String?;

        setState(() {
          _messages.add(_ChatMessage(
            role: 'assistant',
            content: data['response'] as String,
            timestamp: DateTime.parse(data['timestamp'] as String),
            toolCalls: (data['tool_calls'] as List?)
                ?.map((t) => _ToolCall(
                      tool: t['tool'] as String,
                      input: t['input'] as Map<String, dynamic>,
                      result: t['result'] as String,
                    ))
                .toList(),
          ));
        });

        // Scroll to bottom
        Future.delayed(const Duration(milliseconds: 100), () {
          _scrollController.animateTo(
            _scrollController.position.maxScrollExtent,
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOut,
          );
        });
      } else {
        _showError('Failed to send message: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('Error sending message: $e');
      _showError('Error: $e');
    } finally {
      if (mounted) {
        setState(() => _isSending = false);
      }
    }
  }

  void _showError(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
      ),
    );
  }

  void _showInfo(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.blue,
      ),
    );
  }

  void _newConversation() {
    setState(() {
      _messages.clear();
      _conversationId = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Header with info
        Container(
          padding: const EdgeInsets.all(16),
          color: Theme.of(context).colorScheme.primaryContainer,
          child: Row(
            children: [
              const Icon(Icons.smart_toy, size: 32),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Pala Jarvis - Full Codebase Access',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      _isAuthenticated
                          ? 'Claude Sonnet 4.5 • Can read/write files, run commands, search code'
                          : 'Login with your Claude account to get started',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              if (_isAuthenticated) ...[
                IconButton(
                  icon: const Icon(Icons.add),
                  onPressed: _newConversation,
                  tooltip: 'New Conversation',
                ),
                IconButton(
                  icon: const Icon(Icons.logout),
                  onPressed: _logout,
                  tooltip: 'Logout',
                ),
              ],
            ],
          ),
        ),

        // Messages
        Expanded(
          child: !_isAuthenticated
              ? _buildLoginPrompt()
              : _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : _messages.isEmpty
                      ? _buildEmptyState()
                      : ListView.builder(
                          controller: _scrollController,
                          padding: const EdgeInsets.all(16),
                          itemCount: _messages.length,
                          itemBuilder: (context, index) {
                            return _buildMessageBubble(_messages[index]);
                          },
                        ),
        ),

        // Loading indicator
        if (_isSending)
          const LinearProgressIndicator(),

        // Input area
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.1),
                blurRadius: 4,
                offset: const Offset(0, -2),
              ),
            ],
          ),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _messageController,
                  decoration: InputDecoration(
                    hintText: _isAuthenticated
                        ? 'Ask Pala Jarvis to help with the codebase...'
                        : 'Login to start chatting',
                    border: const OutlineInputBorder(),
                    isDense: true,
                  ),
                  maxLines: null,
                  textInputAction: TextInputAction.send,
                  onSubmitted: (_) => _sendMessage(),
                  enabled: _isAuthenticated && !_isSending,
                ),
              ),
              const SizedBox(width: 8),
              IconButton.filled(
                icon: const Icon(Icons.send),
                onPressed: _isAuthenticated && !_isSending ? _sendMessage : null,
                tooltip: 'Send (Enter)',
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildLoginPrompt() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.login,
            size: 64,
            color: Theme.of(context).colorScheme.primary,
          ),
          const SizedBox(height: 24),
          Text(
            'Login with Claude',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: 300,
            child: Text(
              'Use your claude.ai account to chat with Pala Jarvis.\n\nPala Jarvis will have full access to read, write, and execute commands in your codebase.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
          const SizedBox(height: 32),
          ElevatedButton.icon(
            onPressed: _loginWithClaude,
            icon: const Icon(Icons.login),
            label: const Padding(
              padding: EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              child: Text('Login with Claude', style: TextStyle(fontSize: 16)),
            ),
            style: ElevatedButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.primaryContainer,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'Free for Claude Pro subscribers',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.smart_toy,
            size: 64,
            color: Theme.of(context).colorScheme.primary.withOpacity(0.5),
          ),
          const SizedBox(height: 16),
          Text(
            'Chat with Pala Jarvis',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(
            'Ask me to help with tasks like:',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            alignment: WrapAlignment.center,
            children: [
              _buildSuggestionChip('Read and explain files'),
              _buildSuggestionChip('Write new features'),
              _buildSuggestionChip('Search the codebase'),
              _buildSuggestionChip('Run tests'),
              _buildSuggestionChip('Debug issues'),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSuggestionChip(String label) {
    return ActionChip(
      label: Text(label),
      onPressed: () {
        _messageController.text = label;
      },
    );
  }

  Widget _buildMessageBubble(_ChatMessage message) {
    final isUser = message.role == 'user';

    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment:
            isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        children: [
          if (!isUser) ...[
            CircleAvatar(
              backgroundColor: Theme.of(context).colorScheme.primaryContainer,
              child: const Icon(Icons.smart_toy, size: 20),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Column(
              crossAxisAlignment:
                  isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: isUser
                        ? Theme.of(context).colorScheme.primaryContainer
                        : Theme.of(context).colorScheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: SelectableText(
                    message.content,
                    style: const TextStyle(fontSize: 14),
                  ),
                ),
                if (!isUser && message.toolCalls != null && message.toolCalls!.isNotEmpty)
                  _buildToolCallsSection(message.toolCalls!),
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(
                    _formatTime(message.timestamp),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context)
                              .colorScheme
                              .onSurface
                              .withOpacity(0.6),
                        ),
                  ),
                ),
              ],
            ),
          ),
          if (isUser) ...[
            const SizedBox(width: 8),
            CircleAvatar(
              backgroundColor: Theme.of(context).colorScheme.primaryContainer,
              child: const Icon(Icons.person, size: 20),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildToolCallsSection(List<_ToolCall> toolCalls) {
    return Container(
      margin: const EdgeInsets.only(top: 8),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHigh,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: Theme.of(context).colorScheme.outline.withOpacity(0.3),
        ),
      ),
      child: ExpansionTile(
        title: Text(
          '🔧 Tool Calls (${toolCalls.length})',
          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
        ),
        initiallyExpanded: false,
        children: toolCalls.map((tc) => _buildToolCallItem(tc)).toList(),
      ),
    );
  }

  Widget _buildToolCallItem(_ToolCall toolCall) {
    return Container(
      padding: const EdgeInsets.all(12),
      margin: const EdgeInsets.only(left: 16, right: 16, bottom: 8),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(_getToolIcon(toolCall.tool), size: 16),
              const SizedBox(width: 8),
              Text(
                toolCall.tool,
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                  fontFamily: 'monospace',
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Input: ${json.encode(toolCall.input)}',
            style: const TextStyle(fontSize: 12, fontFamily: 'monospace'),
          ),
          const SizedBox(height: 4),
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(4),
            ),
            child: SelectableText(
              toolCall.result,
              style: const TextStyle(fontSize: 11, fontFamily: 'monospace'),
            ),
          ),
        ],
      ),
    );
  }

  IconData _getToolIcon(String toolName) {
    switch (toolName) {
      case 'read_file':
        return Icons.file_open;
      case 'write_file':
        return Icons.save;
      case 'edit_file':
        return Icons.edit;
      case 'execute_bash':
        return Icons.terminal;
      case 'glob_search':
        return Icons.folder_open;
      case 'grep_search':
        return Icons.search;
      default:
        return Icons.build;
    }
  }

  String _formatTime(DateTime time) {
    final now = DateTime.now();
    final diff = now.difference(time);

    if (diff.inSeconds < 60) {
      return 'Just now';
    } else if (diff.inMinutes < 60) {
      return '${diff.inMinutes}m ago';
    } else if (diff.inHours < 24) {
      return '${diff.inHours}h ago';
    } else {
      return '${time.hour}:${time.minute.toString().padLeft(2, '0')}';
    }
  }
}

class _ChatMessage {
  final String role;
  final String content;
  final DateTime timestamp;
  final List<_ToolCall>? toolCalls;

  _ChatMessage({
    required this.role,
    required this.content,
    required this.timestamp,
    this.toolCalls,
  });
}

class _ToolCall {
  final String tool;
  final Map<String, dynamic> input;
  final String result;

  _ToolCall({
    required this.tool,
    required this.input,
    required this.result,
  });
}
