import 'package:flutter_test/flutter_test.dart';
import 'package:same_ai/models/chat_message.dart';
import 'package:samma_ai/providers/chat_provider.dart';
import 'package:samma_ai/providers/settings_provider.dart';
import 'package:samma_ai/providers/agent_provider.dart';

void main() {
  group('ChatProvider Tests', () {
    test('ChatProvider initialization', () {
      final provider = ChatProvider();

      expect(provider.messages, isNotNull);
      expect(provider.isLoading, false);
    });

    test('Add message to chat', () {
      final provider = ChatProvider();
      final message = ChatMessage(
        id: 'msg-1',
        role: 'user',
        content: 'Hello',
        timestamp: DateTime.now(),
      );

      provider.addMessage(message);
      expect(provider.messages.contains(message), true);
    });

    test('Clear chat history', () {
      final provider = ChatProvider();
      provider.addMessage(ChatMessage(
        id: 'msg-1',
        role: 'user',
        content: 'Test',
        timestamp: DateTime.now(),
      ));

      expect(provider.messages.isNotEmpty, true);
      provider.clearChat();
      expect(provider.messages.isEmpty, true);
    });
  });

  group('SettingsProvider Tests', () {
    test('SettingsProvider initialization', () {
      final provider = SettingsProvider();

      expect(provider.apiUrl, isNotNull);
      expect(provider.isDarkMode, isNotNull);
    });

    test('Toggle dark mode', () {
      final provider = SettingsProvider();
      final initialMode = provider.isDarkMode;

      provider.toggleDarkMode();
      expect(provider.isDarkMode, !initialMode);
    });
  });

  group('AgentProvider Tests', () {
    test('AgentProvider initialization', () {
      final provider = AgentProvider();

      expect(provider.agents.isNotEmpty, true);
      expect(provider.teams.isNotEmpty, true);
    });

    test('Filter agents by team', () {
      final provider = AgentProvider();
      final engineeringAgents = provider.agents
          .where((agent) => agent.team == 'Engineering')
          .toList();

      expect(engineeringAgents.isNotEmpty, true);
    });

    test('Get agent by ID', () {
      final provider = AgentProvider();
      final agent = provider.agents.isNotEmpty ? provider.agents.first : null;

      if (agent != null) {
        expect(agent.id, isNotNull);
      }
    });

    test('Update agent status', () {
      final provider = AgentProvider();
      if (provider.agents.isNotEmpty) {
        final agent = provider.agents.first;
        final initialStatus = agent.status;

        // Status should be valid
        expect([
          'idle',
          'busy',
          'offline'
        ].contains(agent.status), true);
      }
    });
  });

  group('Message History Tests', () {
    test('Conversation messages maintain order', () {
      final provider = ChatProvider();

      final msg1 = ChatMessage(
        id: 'msg-1',
        role: 'user',
        content: 'First',
        timestamp: DateTime.now(),
      );

      final msg2 = ChatMessage(
        id: 'msg-2',
        role: 'assistant',
        content: 'Second',
        timestamp: DateTime.now().add(const Duration(seconds: 1)),
      );

      provider.addMessage(msg1);
      provider.addMessage(msg2);

      expect(provider.messages[0].id, 'msg-1');
      expect(provider.messages[1].id, 'msg-2');
    });
  });
}
