import 'package:flutter/material.dart';

/// Kanban-style task board for viewing and managing agent tasks
class TaskBoardView extends StatefulWidget {
  const TaskBoardView({super.key});

  @override
  State<TaskBoardView> createState() => _TaskBoardViewState();
}

class _TaskBoardViewState extends State<TaskBoardView> {
  final _tasks = <_Task>[
    _Task(
      id: '1',
      title: 'Create Agent Dashboard',
      description: 'Build the Flutter web dashboard for agent management',
      assignee: 'flutter-web',
      status: _TaskStatus.inProgress,
      priority: _TaskPriority.high,
    ),
    _Task(
      id: '2',
      title: 'Set up context persistence',
      description: 'Create INIT.md, CONTEXT.md, and memory structure',
      assignee: 'context-manager',
      status: _TaskStatus.done,
      priority: _TaskPriority.high,
    ),
    _Task(
      id: '3',
      title: 'Download Tipitaka database',
      description: 'Download tipitaka_ultimate.db and configure path',
      assignee: 'database-architect',
      status: _TaskStatus.pending,
      priority: _TaskPriority.medium,
    ),
    _Task(
      id: '4',
      title: 'Configure Claude API',
      description: 'Set up Anthropic API key and test integration',
      assignee: 'claude-integrator',
      status: _TaskStatus.pending,
      priority: _TaskPriority.high,
    ),
    _Task(
      id: '5',
      title: 'Write unit tests',
      description: 'Create unit tests for backend services',
      assignee: 'test-runner',
      status: _TaskStatus.pending,
      priority: _TaskPriority.low,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _TaskColumn(
            title: 'Pending',
            icon: Icons.pending_outlined,
            color: Colors.grey,
            tasks: _tasks.where((t) => t.status == _TaskStatus.pending).toList(),
            onTaskMove: _moveTask,
          ),
          const SizedBox(width: 16),
          _TaskColumn(
            title: 'In Progress',
            icon: Icons.play_circle_outline,
            color: Colors.blue,
            tasks: _tasks.where((t) => t.status == _TaskStatus.inProgress).toList(),
            onTaskMove: _moveTask,
          ),
          const SizedBox(width: 16),
          _TaskColumn(
            title: 'Done',
            icon: Icons.check_circle_outline,
            color: Colors.green,
            tasks: _tasks.where((t) => t.status == _TaskStatus.done).toList(),
            onTaskMove: _moveTask,
          ),
        ],
      ),
    );
  }

  void _moveTask(String taskId, _TaskStatus newStatus) {
    setState(() {
      final taskIndex = _tasks.indexWhere((t) => t.id == taskId);
      if (taskIndex != -1) {
        _tasks[taskIndex] = _Task(
          id: _tasks[taskIndex].id,
          title: _tasks[taskIndex].title,
          description: _tasks[taskIndex].description,
          assignee: _tasks[taskIndex].assignee,
          status: newStatus,
          priority: _tasks[taskIndex].priority,
        );
      }
    });
  }
}

class _TaskColumn extends StatelessWidget {
  final String title;
  final IconData icon;
  final Color color;
  final List<_Task> tasks;
  final void Function(String taskId, _TaskStatus newStatus) onTaskMove;

  const _TaskColumn({
    required this.title,
    required this.icon,
    required this.color,
    required this.tasks,
    required this.onTaskMove,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Card(
        child: Column(
          children: [
            // Header
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
              ),
              child: Row(
                children: [
                  Icon(icon, color: color),
                  const SizedBox(width: 8),
                  Text(
                    title,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          color: color,
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  const Spacer(),
                  Chip(
                    label: Text('${tasks.length}'),
                    backgroundColor: color.withOpacity(0.2),
                    labelStyle: TextStyle(color: color),
                  ),
                ],
              ),
            ),
            const Divider(height: 1),

            // Tasks
            Expanded(
              child: tasks.isEmpty
                  ? Center(
                      child: Text(
                        'No tasks',
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.all(8),
                      itemCount: tasks.length,
                      itemBuilder: (context, index) {
                        return _TaskCard(
                          task: tasks[index],
                          onMove: onTaskMove,
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TaskCard extends StatelessWidget {
  final _Task task;
  final void Function(String taskId, _TaskStatus newStatus) onMove;

  const _TaskCard({
    required this.task,
    required this.onMove,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Priority indicator
            Row(
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: _getPriorityColor(task.priority),
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  task.priority.name.toUpperCase(),
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    color: _getPriorityColor(task.priority),
                  ),
                ),
                const Spacer(),
                PopupMenuButton<_TaskStatus>(
                  icon: const Icon(Icons.more_vert, size: 18),
                  itemBuilder: (context) => [
                    const PopupMenuItem(
                      value: _TaskStatus.pending,
                      child: Text('Move to Pending'),
                    ),
                    const PopupMenuItem(
                      value: _TaskStatus.inProgress,
                      child: Text('Move to In Progress'),
                    ),
                    const PopupMenuItem(
                      value: _TaskStatus.done,
                      child: Text('Move to Done'),
                    ),
                  ],
                  onSelected: (status) => onMove(task.id, status),
                ),
              ],
            ),
            const SizedBox(height: 8),

            // Title
            Text(
              task.title,
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),

            // Description
            Text(
              task.description,
              style: Theme.of(context).textTheme.bodySmall,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 8),

            // Assignee
            Row(
              children: [
                Icon(
                  Icons.person_outline,
                  size: 14,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
                const SizedBox(width: 4),
                Text(
                  task.assignee,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context).colorScheme.primary,
                      ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Color _getPriorityColor(_TaskPriority priority) {
    switch (priority) {
      case _TaskPriority.high:
        return Colors.red;
      case _TaskPriority.medium:
        return Colors.orange;
      case _TaskPriority.low:
        return Colors.green;
    }
  }
}

enum _TaskStatus { pending, inProgress, done }

enum _TaskPriority { high, medium, low }

class _Task {
  final String id;
  final String title;
  final String description;
  final String assignee;
  final _TaskStatus status;
  final _TaskPriority priority;

  _Task({
    required this.id,
    required this.title,
    required this.description,
    required this.assignee,
    required this.status,
    required this.priority,
  });
}
