import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/agent_provider.dart';
import 'team_chat_view.dart';
import 'direct_message_view.dart';
import 'task_board_view.dart';
import 'collaboration_view.dart';
import 'execution_monitor_view.dart';
import 'pala_jarvis_view.dart';

/// Main Agent Dashboard with tabs for different views
class AgentDashboard extends StatefulWidget {
  const AgentDashboard({super.key});

  @override
  State<AgentDashboard> createState() => _AgentDashboardState();
}

class _AgentDashboardState extends State<AgentDashboard>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 6, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            Icon(Icons.hub),
            SizedBox(width: 8),
            Text('Agent Dashboard'),
          ],
        ),
        bottom: TabBar(
          controller: _tabController,
          isScrollable: true,
          tabAlignment: TabAlignment.start,
          tabs: const [
            Tab(icon: Icon(Icons.smart_toy), text: 'Pala Jarvis'),
            Tab(icon: Icon(Icons.groups), text: 'Teams'),
            Tab(icon: Icon(Icons.chat), text: 'Direct'),
            Tab(icon: Icon(Icons.view_kanban), text: 'Tasks'),
            Tab(icon: Icon(Icons.science), text: 'Collab'),
            Tab(icon: Icon(Icons.monitor_heart), text: 'Live Exec'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _refreshData,
            tooltip: 'Refresh',
          ),
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: _openSettings,
            tooltip: 'Settings',
          ),
        ],
      ),
      body: TabBarView(
        controller: _tabController,
        children: const [
          PalaJarvisView(),
          TeamChatView(),
          DirectMessageView(),
          TaskBoardView(),
          CollaborationView(),
          ExecutionMonitorView(),
        ],
      ),
    );
  }

  void _refreshData() {
    // TODO: Refresh agent data
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Refreshing agent data...')),
    );
  }

  void _openSettings() {
    // TODO: Open dashboard settings
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Settings coming soon')),
    );
  }
}
