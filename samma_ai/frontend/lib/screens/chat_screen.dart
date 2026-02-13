import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/chat_provider.dart';
import '../widgets/message_bubble.dart';
import '../widgets/chat_input.dart';

/// Main chat screen for interacting with Samma AI
class ChatScreen extends StatelessWidget {
  const ChatScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            Text('🧘 '),
            Text('Samma AI'),
          ],
        ),
        centerTitle: false,
        actions: [
          // Model selector dropdown
          Consumer<ChatProvider>(
            builder: (context, chat, _) {
              return PopupMenuButton<String>(
                icon: const Icon(Icons.psychology_outlined),
                tooltip: 'Select AI Model',
                onOpened: () => chat.fetchAvailableModels(),
                onSelected: (modelId) {
                  chat.setModel(modelId);
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Switched to $modelId')),
                  );
                },
                itemBuilder: (context) => chat.availableModels.map((model) {
                  final isSelected = chat.selectedModelId == model['id'];
                  final isAvailable = model['available'] ?? false;
                  
                  return PopupMenuItem<String>(
                    value: model['id'],
                    enabled: isAvailable,
                    child: Row(
                      children: [
                        Icon(
                          isSelected
                              ? Icons.check_circle
                              : isAvailable 
                                ? Icons.circle_outlined
                                : Icons.block,
                          size: 16,
                          color: isSelected 
                            ? Colors.green 
                            : isAvailable ? null : Colors.grey,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            model['name'] ?? model['id'],
                            style: TextStyle(
                              color: isAvailable ? null : Colors.grey,
                              decoration: isAvailable ? null : TextDecoration.lineThrough,
                            ),
                          ),
                        ),
                        if (!isAvailable)
                          const Text(
                            ' (offline)',
                            style: TextStyle(fontSize: 10, color: Colors.grey),
                          ),
                      ],
                    ),
                  );
                }).toList(),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.help_outline),
            onPressed: () => _showAboutDialog(context),
            tooltip: 'About Samma AI',
          ),
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            onPressed: () => _openSettings(context),
            tooltip: 'Settings',
          ),
        ],
      ),
      body: Column(
        children: [
          // Chat messages area
          Expanded(
            child: Consumer<ChatProvider>(
              builder: (context, chat, _) {
                if (chat.messages.isEmpty) {
                  return const _WelcomeMessage();
                }

                return ListView.builder(
                  controller: chat.scrollController,
                  padding: const EdgeInsets.all(16),
                  itemCount: chat.messages.length,
                  itemBuilder: (context, index) {
                    final message = chat.messages[index];
                    return MessageBubble(message: message);
                  },
                );
              },
            ),
          ),

          // Loading indicator
          Consumer<ChatProvider>(
            builder: (context, chat, _) {
              if (chat.isLoading) {
                return const Padding(
                  padding: EdgeInsets.all(8.0),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                      SizedBox(width: 12),
                      Text('Consulting the Tipitaka...'),
                    ],
                  ),
                );
              }
              return const SizedBox.shrink();
            },
          ),

          // Chat input
          const ChatInput(),
        ],
      ),
    );
  }

  void _showAboutDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Row(
          children: [
            Text('🧘 '),
            Text('About Samma AI'),
          ],
        ),
        content: const SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Samma AI is a Dhamma-grounded AI companion serving the path '
                'to liberation through Buddha\'s teachings.',
                style: TextStyle(fontSize: 14),
              ),
              SizedBox(height: 16),
              Text(
                'Role: Kalyāṇamitta (Spiritual Friend)',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 8),
              Text(
                '• All responses sourced from the Tipiṭaka database\n'
                '• 73,765 Pāli passages available\n'
                '• 74,050 English translations\n'
                '• Non-authoritarian guidance\n'
                '• Serving liberation, not engagement',
                style: TextStyle(fontSize: 13),
              ),
              SizedBox(height: 16),
              Text(
                'धम्मं शरणं गच्छामि\nI take refuge in the Dhamma',
                style: TextStyle(fontStyle: FontStyle.italic),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  void _openSettings(BuildContext context) {
    // TODO: Implement settings screen
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Settings coming soon')),
    );
  }
}

/// Welcome message shown when chat is empty
class _WelcomeMessage extends StatelessWidget {
  const _WelcomeMessage();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text(
              '🧘',
              style: TextStyle(fontSize: 64),
            ),
            const SizedBox(height: 16),
            Text(
              'Samma AI',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 8),
            Text(
              'Your Kalyāṇamitta (Spiritual Friend)',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: Theme.of(context).colorScheme.secondary,
                  ),
            ),
            const SizedBox(height: 24),
            Text(
              'Ask me about the Buddha\'s teachings...',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
            const SizedBox(height: 32),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              alignment: WrapAlignment.center,
              children: [
                _SuggestionChip(
                  label: 'What is dukkha?',
                  onTap: (context) => _sendSuggestion(context, 'What is dukkha?'),
                ),
                _SuggestionChip(
                  label: 'Explain the Four Noble Truths',
                  onTap: (context) =>
                      _sendSuggestion(context, 'Explain the Four Noble Truths'),
                ),
                _SuggestionChip(
                  label: 'What is metta meditation?',
                  onTap: (context) =>
                      _sendSuggestion(context, 'What is metta meditation?'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  void _sendSuggestion(BuildContext context, String message) {
    final chat = Provider.of<ChatProvider>(context, listen: false);
    chat.sendMessage(message);
  }
}

class _SuggestionChip extends StatelessWidget {
  final String label;
  final void Function(BuildContext) onTap;

  const _SuggestionChip({
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ActionChip(
      label: Text(label),
      onPressed: () => onTap(context),
    );
  }
}
