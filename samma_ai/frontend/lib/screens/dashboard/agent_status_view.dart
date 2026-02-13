import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/agent_provider.dart';
import '../../widgets/model_selector_widget.dart';
import '../../models/agent.dart';

/// View showing status of all agents organized by team
class AgentStatusView extends StatelessWidget {
  const AgentStatusView({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<AgentProvider>(
      builder: (context, agentProvider, _) {
        if (agentProvider.isLoading) {
          return const Center(child: CircularProgressIndicator());
        }

        final teams = agentProvider.teams;

        return ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: teams.length,
          itemBuilder: (context, index) {
            final team = teams[index];
            return _TeamCard(team: team);
          },
        );
      },
    );
  }
}

class _TeamCard extends StatelessWidget {
  final AgentTeam team;

  const _TeamCard({required this.team});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: ExpansionTile(
        leading: CircleAvatar(
          backgroundColor: _getTeamColor(team.name, colorScheme),
          child: Text(
            team.name.substring(0, 1).toUpperCase(),
            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
          ),
        ),
        title: Text(
          team.displayName,
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: Text(
          '${team.agents.length} agents • ${_getActiveCount(team.agents)} active',
        ),
        children: team.agents.map((agent) => _AgentTile(agent: agent)).toList(),
      ),
    );
  }

  Color _getTeamColor(String name, ColorScheme colorScheme) {
    switch (name) {
      case 'engineering':
        return Colors.blue;
      case 'tipitaka-mastery':
        return Colors.amber;
      case 'quality-assurance':
        return Colors.green;
      case 'ai-ml':
        return Colors.purple;
      case 'devops':
        return Colors.orange;
      case 'optimization':
        return Colors.teal;
      default:
        return colorScheme.primary;
    }
  }

  int _getActiveCount(List<Agent> agents) {
    return agents.where((a) => a.status == AgentStatus.active || a.status == AgentStatus.busy).length;
  }
}

class _AgentTile extends StatelessWidget {
  final Agent agent;

  const _AgentTile({required this.agent});

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: _StatusIndicator(status: agent.status),
      title: Row(
        children: [
          Flexible(child: Text(agent.displayName)),
          const SizedBox(width: 6),
          ModelSelectorWidget(
            agentName: agent.name,
            currentModel: agent.defaultModel,
          ),
        ],
      ),
      subtitle: agent.currentTask != null
          ? Text(
              agent.currentTask!,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            )
          : Text(
              agent.description,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant),
            ),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            icon: const Icon(Icons.chat_bubble_outline, size: 20),
            onPressed: () => _openChat(context),
            tooltip: 'Message agent',
          ),
          IconButton(
            icon: const Icon(Icons.assignment_outlined, size: 20),
            onPressed: () => _assignTask(context),
            tooltip: 'Assign task',
          ),
        ],
      ),
    );
  }

  void _openChat(BuildContext context) {
    // TODO: Open direct message with agent
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Opening chat with ${agent.displayName}...')),
    );
  }

  void _assignTask(BuildContext context) {
    // TODO: Open task assignment dialog
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Assigning task to ${agent.displayName}...')),
    );
  }
}

class _StatusIndicator extends StatelessWidget {
  final AgentStatus status;

  const _StatusIndicator({required this.status});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 12,
      height: 12,
      decoration: BoxDecoration(
        color: _getStatusColor(),
        shape: BoxShape.circle,
        border: Border.all(color: Colors.white, width: 2),
        boxShadow: [
          BoxShadow(
            color: _getStatusColor().withOpacity(0.4),
            blurRadius: 4,
            spreadRadius: 1,
          ),
        ],
      ),
    );
  }

  Color _getStatusColor() {
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
