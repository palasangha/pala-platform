import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/execution_provider.dart';
import '../../models/execution_log.dart';

/// Live Execution Monitor view
class ExecutionMonitorView extends StatelessWidget {
  const ExecutionMonitorView({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<ExecutionProvider>(
      builder: (context, execProvider, _) {
        return Column(
          children: [
            // Queue status summary bar
            _QueueStatusBar(queueStatus: execProvider.queueStatus),
            // Filter row
            _FilterRow(execProvider: execProvider),
            const Divider(height: 1),
            // Execution log list
            Expanded(
              child: execProvider.filteredLogs.isEmpty
                  ? _EmptyState()
                  : ListView.builder(
                      padding: const EdgeInsets.all(12),
                      itemCount: execProvider.filteredLogs.length,
                      itemBuilder: (context, index) {
                        return _ExecutionLogCard(
                          log: execProvider.filteredLogs[index],
                          execProvider: execProvider,
                        );
                      },
                    ),
            ),
          ],
        );
      },
    );
  }
}

// ── Queue Status Bar ─────────────────────────────────────────────────

class _QueueStatusBar extends StatelessWidget {
  final QueueStatus queueStatus;
  const _QueueStatusBar({required this.queueStatus});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      color: colorScheme.surfaceContainerHighest.withAlpha(80),
      child: Row(
        children: [
          Icon(Icons.monitor_heart, size: 20, color: colorScheme.primary),
          const SizedBox(width: 8),
          Text('Execution Queue', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14, color: colorScheme.onSurface)),
          const Spacer(),
          _StatusBadge(label: 'Queued', count: queueStatus.queued, color: Colors.grey),
          const SizedBox(width: 8),
          _StatusBadge(label: 'Running', count: queueStatus.running, color: Colors.blue),
          const SizedBox(width: 8),
          _StatusBadge(label: 'Paused', count: queueStatus.paused, color: Colors.orange),
          const SizedBox(width: 8),
          _StatusBadge(label: 'Done', count: queueStatus.completed, color: Colors.green),
          const SizedBox(width: 8),
          _StatusBadge(label: 'Failed', count: queueStatus.failed, color: Colors.red),
        ],
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  final String label;
  final int count;
  final Color color;
  const _StatusBadge({required this.label, required this.count, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withAlpha(30),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withAlpha(80)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(shape: BoxShape.circle, color: color),
          ),
          const SizedBox(width: 4),
          Text('$count $label', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w500, color: color.withAlpha(220))),
        ],
      ),
    );
  }
}

// ── Filter Row ───────────────────────────────────────────────────────

class _FilterRow extends StatelessWidget {
  final ExecutionProvider execProvider;
  const _FilterRow({required this.execProvider});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          const Text('Filter: ', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500)),
          const SizedBox(width: 8),
          ...['running', 'queued', 'paused', 'failed', 'completed'].map((status) {
            final isSelected = execProvider.filterStatus == status;
            return Padding(
              padding: const EdgeInsets.only(right: 6),
              child: FilterChip(
                label: Text(status),
                selected: isSelected,
                onSelected: (sel) => execProvider.setStatusFilter(sel ? status : null),
                visualDensity: VisualDensity.compact,
                labelStyle: const TextStyle(fontSize: 11),
              ),
            );
          }),
          const Spacer(),
          IconButton(
            icon: const Icon(Icons.refresh, size: 20),
            onPressed: () => execProvider.fetchLogs(),
            tooltip: 'Refresh logs',
          ),
        ],
      ),
    );
  }
}

// ── Execution Log Card ───────────────────────────────────────────────

class _ExecutionLogCard extends StatefulWidget {
  final ExecutionLog log;
  final ExecutionProvider execProvider;
  const _ExecutionLogCard({required this.log, required this.execProvider});

  @override
  State<_ExecutionLogCard> createState() => _ExecutionLogCardState();
}

class _ExecutionLogCardState extends State<_ExecutionLogCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final log = widget.log;
    final colorScheme = Theme.of(context).colorScheme;

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Column(
        children: [
          // Main row
          InkWell(
            onTap: () => setState(() => _expanded = !_expanded),
            borderRadius: BorderRadius.circular(12),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                children: [
                  // Status icon
                  _StatusIcon(status: log.status),
                  const SizedBox(width: 12),
                  // Task info
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(log.taskName, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                        const SizedBox(height: 2),
                        Row(
                          children: [
                            Icon(Icons.smart_toy, size: 12, color: colorScheme.onSurfaceVariant),
                            const SizedBox(width: 4),
                            Text(log.agentName, style: TextStyle(fontSize: 11, color: colorScheme.onSurfaceVariant)),
                            const SizedBox(width: 12),
                            _ModelChip(model: log.modelUsed),
                          ],
                        ),
                      ],
                    ),
                  ),
                  // Duration
                  if (log.durationSeconds != null)
                    Padding(
                      padding: const EdgeInsets.only(right: 12),
                      child: Text(
                        _formatDuration(log.durationSeconds!),
                        style: TextStyle(fontSize: 11, color: colorScheme.onSurfaceVariant, fontFamily: 'monospace'),
                      ),
                    ),
                  // Error indicator
                  if (log.error != null)
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: Tooltip(
                        message: log.error!,
                        child: Icon(Icons.error_outline, size: 16, color: colorScheme.error),
                      ),
                    ),
                  // Retry badge
                  if (log.retryCount > 0)
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: Colors.orange.withAlpha(30),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text('retry ${log.retryCount}', style: const TextStyle(fontSize: 10, color: Colors.orange)),
                      ),
                    ),
                  // Action buttons
                  _ActionButtons(log: log, execProvider: widget.execProvider),
                  // Expand icon
                  Icon(_expanded ? Icons.expand_less : Icons.expand_more, size: 20, color: colorScheme.onSurfaceVariant),
                ],
              ),
            ),
          ),
          // Expanded log lines
          if (_expanded && log.logLines.isNotEmpty)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              margin: const EdgeInsets.symmetric(horizontal: 12).copyWith(bottom: 12),
              decoration: BoxDecoration(
                color: colorScheme.surfaceContainerHighest.withAlpha(100),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: log.logLines.map((line) => Padding(
                  padding: const EdgeInsets.only(bottom: 2),
                  child: Text(
                    line,
                    style: TextStyle(fontFamily: 'monospace', fontSize: 11, color: colorScheme.onSurface),
                  ),
                )).toList(),
              ),
            ),
        ],
      ),
    );
  }

  String _formatDuration(double seconds) {
    if (seconds < 60) return '${seconds.toInt()}s';
    if (seconds < 3600) return '${(seconds / 60).toInt()}m ${(seconds % 60).toInt()}s';
    return '${(seconds / 3600).toInt()}h ${((seconds % 3600) / 60).toInt()}m';
  }
}

// ── Status Icon ──────────────────────────────────────────────────────

class _StatusIcon extends StatelessWidget {
  final ExecutionStatus status;
  const _StatusIcon({required this.status});

  @override
  Widget build(BuildContext context) {
    IconData icon;
    Color color;

    switch (status) {
      case ExecutionStatus.queued:
        icon = Icons.schedule;
        color = Colors.grey;
        break;
      case ExecutionStatus.running:
        icon = Icons.play_circle_filled;
        color = Colors.blue;
        break;
      case ExecutionStatus.paused:
        icon = Icons.pause_circle_filled;
        color = Colors.orange;
        break;
      case ExecutionStatus.completed:
        icon = Icons.check_circle;
        color = Colors.green;
        break;
      case ExecutionStatus.failed:
        icon = Icons.cancel;
        color = Colors.red;
        break;
      case ExecutionStatus.cancelled:
        icon = Icons.block;
        color = Colors.grey;
        break;
    }

    return Icon(icon, size: 24, color: color);
  }
}

// ── Model Chip ───────────────────────────────────────────────────────

class _ModelChip extends StatelessWidget {
  final String model;
  const _ModelChip({required this.model});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    String shortName = model;
    if (model.contains('claude')) {
      shortName = 'Claude';
    } else if (model.contains('gpt')) {
      shortName = 'GPT-4o';
    } else if (model.startsWith('ollama:')) {
      shortName = 'Ollama';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
      decoration: BoxDecoration(
        color: colorScheme.tertiaryContainer.withAlpha(120),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(shortName, style: TextStyle(fontSize: 10, color: colorScheme.onTertiaryContainer)),
    );
  }
}

// ── Action Buttons ───────────────────────────────────────────────────

class _ActionButtons extends StatelessWidget {
  final ExecutionLog log;
  final ExecutionProvider execProvider;
  const _ActionButtons({required this.log, required this.execProvider});

  @override
  Widget build(BuildContext context) {
    final actions = <Widget>[];

    if (log.status == ExecutionStatus.running) {
      actions.add(IconButton(
        icon: const Icon(Icons.pause, size: 16),
        onPressed: () => execProvider.pauseTask(log.id),
        tooltip: 'Pause',
        visualDensity: VisualDensity.compact,
      ));
      actions.add(IconButton(
        icon: const Icon(Icons.stop, size: 16),
        onPressed: () => execProvider.cancelTask(log.id),
        tooltip: 'Cancel',
        visualDensity: VisualDensity.compact,
      ));
    }

    if (log.status == ExecutionStatus.failed || log.status == ExecutionStatus.completed) {
      actions.add(IconButton(
        icon: const Icon(Icons.replay, size: 16),
        onPressed: () => execProvider.replayTask(log.id),
        tooltip: 'Replay',
        visualDensity: VisualDensity.compact,
      ));
    }

    if (log.status == ExecutionStatus.paused) {
      actions.add(IconButton(
        icon: const Icon(Icons.play_arrow, size: 16),
        onPressed: () {}, // Resume not implemented yet
        tooltip: 'Resume',
        visualDensity: VisualDensity.compact,
      ));
    }

    return Row(mainAxisSize: MainAxisSize.min, children: actions);
  }
}

// ── Empty State ──────────────────────────────────────────────────────

class _EmptyState extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.monitor_heart_outlined, size: 64, color: colorScheme.onSurfaceVariant.withAlpha(80)),
          const SizedBox(height: 12),
          Text(
            'No execution logs',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: colorScheme.onSurfaceVariant),
          ),
          const SizedBox(height: 4),
          Text(
            'Tasks will appear here when agents are working',
            style: TextStyle(fontSize: 13, color: colorScheme.onSurfaceVariant.withAlpha(180)),
          ),
        ],
      ),
    );
  }
}
