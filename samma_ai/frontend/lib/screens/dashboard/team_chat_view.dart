import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/agent_provider.dart';
import '../../models/agent.dart';

/// View for chatting with team leads
class TeamChatView extends StatefulWidget {
  const TeamChatView({super.key});

  @override
  State<TeamChatView> createState() => _TeamChatViewState();
}

class _TeamChatViewState extends State<TeamChatView> {
  String? _selectedTeam;
  final _messageController = TextEditingController();
  final _messages = <_TeamMessage>[];

  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AgentProvider>(
      builder: (context, agentProvider, _) {
        final teams = agentProvider.teams;

        return Row(
          children: [
            // Team list sidebar
            SizedBox(
              width: 250,
              child: Card(
                margin: const EdgeInsets.all(8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Padding(
                      padding: const EdgeInsets.all(16),
                      child: Text(
                        'Teams',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ),
                    const Divider(height: 1),
                    Expanded(
                      child: ListView.builder(
                        itemCount: teams.length,
                        itemBuilder: (context, index) {
                          final team = teams[index];
                          final isSelected = _selectedTeam == team.name;

                          return ListTile(
                            leading: _TeamAvatar(team: team),
                            title: Text(team.displayName),
                            subtitle: Text('Lead: ${team.lead}'),
                            selected: isSelected,
                            onTap: () {
                              setState(() => _selectedTeam = team.name);
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
              child: _selectedTeam == null
                  ? const _EmptyState()
                  : _ChatArea(
                      teamName: _selectedTeam!,
                      messages: _messages,
                      controller: _messageController,
                      onSend: _sendMessage,
                    ),
            ),
          ],
        );
      },
    );
  }

  void _sendMessage() {
    if (_messageController.text.trim().isEmpty || _selectedTeam == null) return;

    setState(() {
      _messages.add(_TeamMessage(
        from: 'You',
        to: _selectedTeam!,
        content: _messageController.text,
        timestamp: DateTime.now(),
        isFromUser: true,
      ));
    });

    _messageController.clear();

    // Simulate response
    Future.delayed(const Duration(seconds: 1), () {
      if (mounted) {
        setState(() {
          _messages.add(_TeamMessage(
            from: '$_selectedTeam-lead',
            to: 'You',
            content: 'Received your message. I\'ll coordinate with my team and get back to you.',
            timestamp: DateTime.now(),
            isFromUser: false,
          ));
        });
      }
    });
  }
}

class _TeamAvatar extends StatelessWidget {
  final AgentTeam team;

  const _TeamAvatar({required this.team});

  @override
  Widget build(BuildContext context) {
    IconData icon;
    Color color;

    switch (team.name) {
      case 'engineering':
        icon = Icons.engineering;
        color = Colors.blue;
        break;
      case 'tipitaka-mastery':
        icon = Icons.menu_book;
        color = Colors.amber;
        break;
      case 'quality-assurance':
        icon = Icons.verified;
        color = Colors.green;
        break;
      case 'ai-ml':
        icon = Icons.psychology;
        color = Colors.purple;
        break;
      case 'devops':
        icon = Icons.cloud;
        color = Colors.orange;
        break;
      case 'optimization':
        icon = Icons.speed;
        color = Colors.teal;
        break;
      default:
        icon = Icons.group;
        color = Theme.of(context).colorScheme.primary;
    }

    return CircleAvatar(
      backgroundColor: color,
      child: Icon(icon, color: Colors.white, size: 20),
    );
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
            Icons.groups,
            size: 64,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
          const SizedBox(height: 16),
          Text(
            'Select a team to start chatting',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            'Messages go to the team lead who coordinates with sub-agents',
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
  final String teamName;
  final List<_TeamMessage> messages;
  final TextEditingController controller;
  final VoidCallback onSend;

  const _ChatArea({
    required this.teamName,
    required this.messages,
    required this.controller,
    required this.onSend,
  });

  @override
  Widget build(BuildContext context) {
    final teamMessages = messages.where(
      (m) => m.to == teamName || m.from.contains(teamName),
    ).toList();

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
                Text(
                  'Team: $teamName',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const Spacer(),
                Chip(
                  label: Text('$teamName-lead'),
                  avatar: const Icon(Icons.person, size: 16),
                ),
              ],
            ),
          ),
          const Divider(height: 1),

          // Messages
          Expanded(
            child: teamMessages.isEmpty
                ? Center(
                    child: Text(
                      'No messages yet. Start the conversation!',
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: teamMessages.length,
                    itemBuilder: (context, index) {
                      final msg = teamMessages[index];
                      return _MessageBubble(message: msg);
                    },
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
                      hintText: 'Message $teamName team...',
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
                  onPressed: onSend,
                  icon: const Icon(Icons.send),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  final _TeamMessage message;

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
            if (!isUser)
              Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Text(
                  message.from,
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                    color: colorScheme.primary,
                  ),
                ),
              ),
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

class _TeamMessage {
  final String from;
  final String to;
  final String content;
  final DateTime timestamp;
  final bool isFromUser;

  _TeamMessage({
    required this.from,
    required this.to,
    required this.content,
    required this.timestamp,
    required this.isFromUser,
  });
}
