import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../../providers/agent_provider.dart';
import '../../models/agent.dart';

/// View for direct messaging individual agents
class DirectMessageView extends StatefulWidget {
  const DirectMessageView({super.key});

  @override
  State<DirectMessageView> createState() => _DirectMessageViewState();
}

class _DirectMessageViewState extends State<DirectMessageView> {
  Agent? _selectedAgent;
  final _messageController = TextEditingController();
  final _searchController = TextEditingController();
  final _conversations = <String, List<_DirectMessage>>{};
  final _conversationIds = <String, String>{}; // agent_name -> conversation_id
  bool _isLoading = false;
  bool _isSending = false;

  @override
  void dispose() {
    _messageController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    // Load conversation history from localStorage
    _loadConversationHistory();
  }

  Future<void> _loadConversationHistory() async {
    // Load conversations from localStorage (browser storage)
    setState(() => _isLoading = true);

    try {
      final prefs = await SharedPreferences.getInstance();

      // Load conversation IDs
      final conversationIdsJson = prefs.getString('agent_conversation_ids');
      if (conversationIdsJson != null) {
        final decoded = json.decode(conversationIdsJson) as Map<String, dynamic>;
        _conversationIds.addAll(decoded.cast<String, String>());
      }

      // Load all conversations
      final conversationsJson = prefs.getString('agent_conversations');
      if (conversationsJson != null) {
        final decoded = json.decode(conversationsJson) as Map<String, dynamic>;

        for (var entry in decoded.entries) {
          final agentName = entry.key;
          final messages = (entry.value as List).map((msg) {
            return _DirectMessage(
              from: msg['from'],
              to: msg['to'],
              content: msg['content'],
              timestamp: DateTime.parse(msg['timestamp']),
              isFromUser: msg['isFromUser'],
              read: msg['read'],
            );
          }).toList();

          _conversations[agentName] = messages;
        }
      }

      debugPrint('Loaded conversations for ${_conversations.length} agents from localStorage');
    } catch (e) {
      debugPrint('Error loading conversation history from localStorage: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _saveConversationsToLocalStorage() async {
    // Save conversations to localStorage for persistence
    try {
      final prefs = await SharedPreferences.getInstance();

      // Save conversation IDs
      await prefs.setString('agent_conversation_ids', json.encode(_conversationIds));

      // Save all conversations
      final conversationsData = <String, List<Map<String, dynamic>>>{};
      for (var entry in _conversations.entries) {
        conversationsData[entry.key] = entry.value.map((msg) {
          return {
            'from': msg.from,
            'to': msg.to,
            'content': msg.content,
            'timestamp': msg.timestamp.toIso8601String(),
            'isFromUser': msg.isFromUser,
            'read': msg.read,
          };
        }).toList();
      }

      await prefs.setString('agent_conversations', json.encode(conversationsData));
      debugPrint('Saved conversations to localStorage');
    } catch (e) {
      debugPrint('Error saving conversations to localStorage: $e');
    }
  }

  Future<void> _loadAgentConversation(String agentName) async {
    setState(() => _isLoading = true);

    try {
      final response = await http.get(
        Uri.parse('http://localhost:5001/api/agents/$agentName/conversations'),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final conversations = data['conversations'] as List;

        if (conversations.isNotEmpty) {
          // Load the most recent conversation
          final mostRecent = conversations.first;
          final conversationId = mostRecent['conversation_id'] as String;
          _conversationIds[agentName] = conversationId;

          // Load full conversation history
          await _loadConversationMessages(conversationId, agentName);
        }
      }
    } catch (e) {
      debugPrint('Error loading agent conversation: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _loadConversationMessages(String conversationId, String agentName) async {
    try {
      final response = await http.get(
        Uri.parse('http://localhost:5001/api/agents/chat/history/$conversationId'),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final messages = data['messages'] as List;

        setState(() {
          _conversations[agentName] = messages.map((msg) {
            return _DirectMessage(
              from: 'You',
              to: agentName,
              content: msg['user_message'],
              timestamp: DateTime.parse(msg['timestamp']),
              isFromUser: true,
              read: true,
            );
          }).expand((userMsg) {
            // Get the corresponding agent response
            final msgData = messages.firstWhere(
              (m) => m['user_message'] == userMsg.content,
              orElse: () => null,
            );

            if (msgData != null && msgData['agent_response'] != null) {
              return [
                userMsg,
                _DirectMessage(
                  from: agentName,
                  to: 'You',
                  content: msgData['agent_response'],
                  timestamp: DateTime.parse(msgData['timestamp']),
                  isFromUser: false,
                  read: true,
                ),
              ];
            }
            return [userMsg];
          }).toList();
        });
      }
    } catch (e) {
      debugPrint('Error loading conversation messages: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AgentProvider>(
      builder: (context, agentProvider, _) {
        final allAgents = agentProvider.teams
            .expand((team) => team.agents)
            .toList();

        return Row(
          children: [
            // Agent list sidebar
            SizedBox(
              width: 280,
              child: Card(
                margin: const EdgeInsets.all(8),
                child: Column(
                  children: [
                    // Search
                    Padding(
                      padding: const EdgeInsets.all(12),
                      child: TextField(
                        controller: _searchController,
                        decoration: InputDecoration(
                          hintText: 'Search agents...',
                          prefixIcon: const Icon(Icons.search),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(24),
                            borderSide: BorderSide.none,
                          ),
                          filled: true,
                          contentPadding: const EdgeInsets.symmetric(
                            horizontal: 16,
                            vertical: 8,
                          ),
                        ),
                        onChanged: (_) => setState(() {}),
                      ),
                    ),
                    const Divider(height: 1),

                    // Agent list
                    Expanded(
                      child: ListView.builder(
                        itemCount: allAgents.length,
                        itemBuilder: (context, index) {
                          final agent = allAgents[index];
                          final searchQuery = _searchController.text.toLowerCase();

                          if (searchQuery.isNotEmpty &&
                              !agent.name.toLowerCase().contains(searchQuery) &&
                              !agent.displayName.toLowerCase().contains(searchQuery)) {
                            return const SizedBox.shrink();
                          }

                          final isSelected = _selectedAgent?.name == agent.name;
                          final hasUnread = _conversations[agent.name]?.any((m) => !m.read) ?? false;

                          return ListTile(
                            leading: Stack(
                              children: [
                                CircleAvatar(
                                  backgroundColor: _getAgentColor(agent),
                                  child: Text(
                                    agent.name.substring(0, 1).toUpperCase(),
                                    style: const TextStyle(color: Colors.white),
                                  ),
                                ),
                                if (hasUnread)
                                  Positioned(
                                    right: 0,
                                    top: 0,
                                    child: Container(
                                      width: 10,
                                      height: 10,
                                      decoration: const BoxDecoration(
                                        color: Colors.red,
                                        shape: BoxShape.circle,
                                      ),
                                    ),
                                  ),
                              ],
                            ),
                            title: Text(agent.displayName),
                            subtitle: Text(
                              agent.status.name,
                              style: TextStyle(
                                color: _getStatusColor(agent.status),
                                fontSize: 12,
                              ),
                            ),
                            selected: isSelected,
                            onTap: () {
                              setState(() => _selectedAgent = agent);
                              // Load conversation history for this agent
                              _loadAgentConversation(agent.name);
                            },
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // Chat area
            Expanded(
              child: _selectedAgent == null
                  ? const _EmptyState()
                  : _ChatArea(
                      agent: _selectedAgent!,
                      messages: _conversations[_selectedAgent!.name] ?? [],
                      controller: _messageController,
                      onSend: _sendMessage,
                      isLoading: _isLoading,
                      isSending: _isSending,
                    ),
            ),
          ],
        );
      },
    );
  }

  Color _getAgentColor(Agent agent) {
    // Use agent's team to determine color
    if (agent.name.contains('engineering') || agent.name.contains('flutter') || agent.name.contains('flask')) {
      return Colors.blue;
    } else if (agent.name.contains('tipitaka') || agent.name.contains('sutta') || agent.name.contains('vinaya') || agent.name.contains('abhidhamma') || agent.name.contains('pali')) {
      return Colors.amber;
    } else if (agent.name.contains('qa') || agent.name.contains('test') || agent.name.contains('review') || agent.name.contains('security')) {
      return Colors.green;
    } else if (agent.name.contains('ai') || agent.name.contains('claude') || agent.name.contains('embed') || agent.name.contains('rag')) {
      return Colors.purple;
    } else if (agent.name.contains('devops') || agent.name.contains('docker') || agent.name.contains('ci-cd') || agent.name.contains('infra')) {
      return Colors.orange;
    } else if (agent.name.contains('optimization') || agent.name.contains('token') || agent.name.contains('cost') || agent.name.contains('model')) {
      return Colors.teal;
    }
    return Colors.grey;
  }

  Color _getStatusColor(AgentStatus status) {
    switch (status) {
      case AgentStatus.active:
        return Colors.green;
      case AgentStatus.busy:
        return Colors.orange;
      case AgentStatus.idle:
        return Colors.grey;
      case AgentStatus.offline:
        return Colors.red;
    }
  }

  Future<void> _sendMessage() async {
    if (_messageController.text.trim().isEmpty || _selectedAgent == null || _isSending) return;

    final agentName = _selectedAgent!.name;
    final messageText = _messageController.text;

    // Add user message to UI immediately
    setState(() {
      _conversations.putIfAbsent(agentName, () => []);
      _conversations[agentName]!.add(_DirectMessage(
        from: 'You',
        to: agentName,
        content: messageText,
        timestamp: DateTime.now(),
        isFromUser: true,
        read: true,
      ));
      _isSending = true;
    });

    _messageController.clear();

    try {
      // Get or create conversation ID
      final conversationId = _conversationIds.putIfAbsent(
        agentName,
        () => DateTime.now().millisecondsSinceEpoch.toString(),
      );

      // Send message to backend
      final response = await http.post(
        Uri.parse('http://localhost:5001/api/agents/chat'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'agent_name': agentName,
          'message': messageText,
          'conversation_id': conversationId,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final agentResponse = data['agent_response'] as String;

        // Add agent response to UI
        if (mounted && _selectedAgent?.name == agentName) {
          setState(() {
            _conversations[agentName]!.add(_DirectMessage(
              from: agentName,
              to: 'You',
              content: agentResponse,
              timestamp: DateTime.parse(data['timestamp']),
              isFromUser: false,
              read: true,
            ));
          });
          // Save to localStorage for persistence
          _saveConversationsToLocalStorage();
        }
      } else {
        // Show error message
        if (mounted && _selectedAgent?.name == agentName) {
          setState(() {
            _conversations[agentName]!.add(_DirectMessage(
              from: agentName,
              to: 'You',
              content: 'Error: ${response.statusCode} - ${response.body}',
              timestamp: DateTime.now(),
              isFromUser: false,
              read: true,
            ));
          });
          _saveConversationsToLocalStorage();
        }
      }
    } catch (e) {
      // Show error message
      if (mounted && _selectedAgent?.name == agentName) {
        setState(() {
          _conversations[agentName]!.add(_DirectMessage(
            from: agentName,
            to: 'You',
            content: 'Error sending message: $e',
            timestamp: DateTime.now(),
            isFromUser: false,
            read: true,
          ));
        });
        _saveConversationsToLocalStorage();
      }
    } finally {
      if (mounted) {
        setState(() => _isSending = false);
      }
    }
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.chat_bubble_outline,
            size: 64,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
          const SizedBox(height: 16),
          Text(
            'Select an agent to start a conversation',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            'You can message any agent directly for specific tasks',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
          ),
        ],
      ),
    );
  }
}

class _ChatArea extends StatelessWidget {
  final Agent agent;
  final List<_DirectMessage> messages;
  final TextEditingController controller;
  final VoidCallback onSend;
  final bool isLoading;
  final bool isSending;

  const _ChatArea({
    required this.agent,
    required this.messages,
    required this.controller,
    required this.onSend,
    this.isLoading = false,
    this.isSending = false,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.all(8),
      child: Column(
        children: [
          // Header
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
            ),
            child: Row(
              children: [
                CircleAvatar(
                  backgroundColor: Theme.of(context).colorScheme.primary,
                  child: Text(
                    agent.name.substring(0, 1).toUpperCase(),
                    style: const TextStyle(color: Colors.white),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        agent.displayName,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      Text(
                        agent.description,
                        style: Theme.of(context).textTheme.bodySmall,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                Chip(
                  label: Text(agent.status.name),
                  backgroundColor: _getStatusColor(agent.status).withOpacity(0.2),
                ),
              ],
            ),
          ),
          const Divider(height: 1),

          // Messages
          Expanded(
            child: isLoading
                ? const Center(child: CircularProgressIndicator())
                : messages.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.chat,
                              size: 48,
                              color: Theme.of(context).colorScheme.onSurfaceVariant,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Start a conversation with ${agent.displayName}',
                              style: TextStyle(
                                color: Theme.of(context).colorScheme.onSurfaceVariant,
                              ),
                            ),
                          ],
                        ),
                      )
                    : Stack(
                        children: [
                          ListView.builder(
                            padding: const EdgeInsets.all(16),
                            itemCount: messages.length,
                            itemBuilder: (context, index) {
                              final msg = messages[index];
                              return _MessageBubble(message: msg);
                            },
                          ),
                          if (isSending)
                            Positioned(
                              bottom: 16,
                              left: 16,
                              child: Card(
                                child: Padding(
                                  padding: const EdgeInsets.all(12),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      SizedBox(
                                        width: 16,
                                        height: 16,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2,
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Text('${agent.displayName} is thinking...'),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                        ],
                      ),
          ),

          // Input
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surface,
              border: Border(
                top: BorderSide(
                  color: Theme.of(context).colorScheme.outlineVariant,
                ),
              ),
            ),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: controller,
                    decoration: InputDecoration(
                      hintText: 'Message ${agent.displayName}...',
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide.none,
                      ),
                      filled: true,
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 20,
                        vertical: 12,
                      ),
                    ),
                    onSubmitted: (_) => onSend(),
                  ),
                ),
                const SizedBox(width: 12),
                IconButton.filled(
                  onPressed: isSending ? null : onSend,
                  icon: isSending
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.send),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Color _getStatusColor(AgentStatus status) {
    switch (status) {
      case AgentStatus.active:
        return Colors.green;
      case AgentStatus.busy:
        return Colors.orange;
      case AgentStatus.idle:
        return Colors.grey;
      case AgentStatus.offline:
        return Colors.red;
    }
  }
}

class _MessageBubble extends StatelessWidget {
  final _DirectMessage message;

  const _MessageBubble({required this.message});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final isUser = message.isFromUser;

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.all(12),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.6,
        ),
        decoration: BoxDecoration(
          color: isUser ? colorScheme.primaryContainer : colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(message.content),
            const SizedBox(height: 4),
            Text(
              _formatTime(message.timestamp),
              style: TextStyle(
                fontSize: 10,
                color: colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _formatTime(DateTime time) {
    return '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}';
  }
}

class _DirectMessage {
  final String from;
  final String to;
  final String content;
  final DateTime timestamp;
  final bool isFromUser;
  final bool read;

  _DirectMessage({
    required this.from,
    required this.to,
    required this.content,
    required this.timestamp,
    required this.isFromUser,
    required this.read,
  });
}
