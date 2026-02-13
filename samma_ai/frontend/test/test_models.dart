import 'package:flutter_test/flutter_test.dart';
import 'package:samma_ai/models/chat_message.dart';
import 'package:samma_ai/models/agent.dart';

void main() {
  group('ChatMessage Model Tests', () {
    test('ChatMessage.user factory creates user message', () {
      final message = ChatMessage.user('What is dukkha?');

      expect(message.isUser, true);
      expect(message.content, 'What is dukkha?');
      expect(message.id.isNotEmpty, true);
    });

    test('ChatMessage.assistant factory creates assistant message', () {
      final message = ChatMessage.assistant('The Buddha taught suffering.');

      expect(message.isUser, false);
      expect(message.content, 'The Buddha taught suffering.');
    });

    test('ChatMessage constructor with all fields', () {
      final now = DateTime.now();
      final message = ChatMessage(
        id: 'msg-1',
        isUser: true,
        content: 'Test',
        timestamp: now,
      );

      expect(message.id, 'msg-1');
      expect(message.isUser, true);
      expect(message.timestamp, now);
    });
  });

  group('DhammaResponse Model Tests', () {
    test('DhammaResponse requires formattedText', () {
      final response = DhammaResponse(
        databaseSummary: ResponseSection(title: 'DB', content: 'From db'),
        interpretiveSummary: ResponseSection(title: 'Modern', content: 'Modern view'),
        teachings: [],
        finalSummary: ResponseSection(title: 'Final', content: 'Synthesis'),
        formattedText: 'Formatted response',
      );

      expect(response.formattedText, 'Formatted response');
      expect(response.teachings.isEmpty, true);
    });
  });

  group('ResponseSection Model Tests', () {
    test('ResponseSection creation', () {
      final section = ResponseSection(
        title: 'Database Summary',
        content: 'The Tipitaka says...',
      );

      expect(section.title, 'Database Summary');
      expect(section.content, 'The Tipitaka says...');
    });
  });

  group('Agent Model Tests', () {
    test('Agent creation with required fields', () {
      final agent = Agent(
        name: 'flutter-web',
        displayName: 'Flutter Web Developer',
        description: 'Builds Flutter UI',
      );

      expect(agent.name, 'flutter-web');
      expect(agent.displayName, 'Flutter Web Developer');
      expect(agent.status, AgentStatus.idle);
    });

    test('Agent status defaults to idle', () {
      final agent = Agent(
        name: 'test-agent',
        displayName: 'Test Agent',
        description: 'Test',
      );

      expect(agent.status, AgentStatus.idle);
    });

    test('Agent can have custom status', () {
      final agent = Agent(
        name: 'test-agent',
        displayName: 'Test Agent',
        description: 'Test',
        status: AgentStatus.busy,
      );

      expect(agent.status, AgentStatus.busy);
    });
  });

  group('AgentStatus Enum Tests', () {
    test('AgentStatus has expected values', () {
      expect(AgentStatus.values.length, 4);
      expect(AgentStatus.values.contains(AgentStatus.idle), true);
      expect(AgentStatus.values.contains(AgentStatus.busy), true);
      expect(AgentStatus.values.contains(AgentStatus.active), true);
      expect(AgentStatus.values.contains(AgentStatus.offline), true);
    });
  });

  group('AgentTeam Model Tests', () {
    test('AgentTeam creation', () {
      final team = AgentTeam(
        name: 'engineering',
        displayName: 'Engineering Team',
        description: 'Backend and frontend devs',
        lead: 'engineering-lead',
        agents: [],
      );

      expect(team.name, 'engineering');
      expect(team.lead, 'engineering-lead');
      expect(team.agents.isEmpty, true);
    });
  });
}
