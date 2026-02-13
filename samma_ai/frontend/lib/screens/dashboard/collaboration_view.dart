import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/collaboration_provider.dart';
import '../../models/collaboration_thread.dart';

/// Agent Collaboration / R&D workspace view
class CollaborationView extends StatelessWidget {
  const CollaborationView({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<CollaborationProvider>(
      builder: (context, collab, _) {
        return Row(
          children: [
            // Left panel — Thread list
            SizedBox(
              width: 340,
              child: _ThreadListPanel(collab: collab),
            ),
            const VerticalDivider(width: 1),
            // Right panel — Thread detail
            Expanded(
              child: collab.selectedThread != null
                  ? _ThreadDetailPanel(collab: collab)
                  : const _EmptyThreadPanel(),
            ),
          ],
        );
      },
    );
  }
}

// ── Thread List Panel ────────────────────────────────────────────────

class _ThreadListPanel extends StatelessWidget {
  final CollaborationProvider collab;
  const _ThreadListPanel({required this.collab});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Column(
      children: [
        // Search + controls bar
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: colorScheme.surfaceContainerHighest.withAlpha(80),
            border: Border(bottom: BorderSide(color: colorScheme.outlineVariant)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      onChanged: collab.setSearch,
                      decoration: InputDecoration(
                        hintText: 'Search threads...',
                        prefixIcon: const Icon(Icons.search, size: 20),
                        isDense: true,
                        contentPadding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  // Admin toggle
                  Tooltip(
                    message: collab.isAdmin ? 'Admin mode ON' : 'Read-only mode',
                    child: IconButton(
                      icon: Icon(
                        collab.isAdmin ? Icons.admin_panel_settings : Icons.visibility,
                        color: collab.isAdmin ? colorScheme.primary : colorScheme.onSurfaceVariant,
                        size: 20,
                      ),
                      onPressed: collab.toggleAdmin,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              // Tag filter chips
              if (collab.allTags.isNotEmpty)
                SizedBox(
                  height: 32,
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    children: [
                      if (collab.filterTag != null)
                        Padding(
                          padding: const EdgeInsets.only(right: 6),
                          child: ActionChip(
                            label: const Text('Clear'),
                            avatar: const Icon(Icons.clear, size: 14),
                            onPressed: () => collab.setFilterTag(null),
                            visualDensity: VisualDensity.compact,
                          ),
                        ),
                      ...collab.allTags.map((tag) => Padding(
                            padding: const EdgeInsets.only(right: 6),
                            child: FilterChip(
                              label: Text(tag),
                              selected: collab.filterTag == tag,
                              onSelected: (sel) => collab.setFilterTag(sel ? tag : null),
                              visualDensity: VisualDensity.compact,
                            ),
                          )),
                    ],
                  ),
                ),
            ],
          ),
        ),
        // Thread list
        Expanded(
          child: collab.threads.isEmpty
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.forum_outlined, size: 48, color: colorScheme.onSurfaceVariant.withAlpha(100)),
                      const SizedBox(height: 8),
                      Text('No threads found', style: TextStyle(color: colorScheme.onSurfaceVariant)),
                    ],
                  ),
                )
              : ListView.separated(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  itemCount: collab.threads.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (context, index) {
                    final thread = collab.threads[index];
                    final isSelected = collab.selectedThread?.id == thread.id;
                    return _ThreadTile(thread: thread, isSelected: isSelected, collab: collab);
                  },
                ),
        ),
        // Read-only banner
        if (!collab.isAdmin)
          Container(
            padding: const EdgeInsets.all(8),
            color: colorScheme.tertiaryContainer.withAlpha(100),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.visibility, size: 14, color: colorScheme.onTertiaryContainer),
                const SizedBox(width: 4),
                Text(
                  'Read-only · Agent workspace',
                  style: TextStyle(fontSize: 12, color: colorScheme.onTertiaryContainer),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _ThreadTile extends StatelessWidget {
  final CollaborationThread thread;
  final bool isSelected;
  final CollaborationProvider collab;

  const _ThreadTile({required this.thread, required this.isSelected, required this.collab});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return ListTile(
      selected: isSelected,
      selectedTileColor: colorScheme.primaryContainer.withAlpha(80),
      leading: CircleAvatar(
        radius: 18,
        backgroundColor: colorScheme.secondaryContainer,
        child: Text(
          thread.createdBy.substring(0, 1).toUpperCase(),
          style: TextStyle(color: colorScheme.onSecondaryContainer, fontWeight: FontWeight.bold),
        ),
      ),
      title: Text(thread.title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
      subtitle: Wrap(
        spacing: 4,
        children: [
          Text('${thread.messageCount} msgs · by ${thread.createdBy}',
              style: TextStyle(fontSize: 11, color: colorScheme.onSurfaceVariant)),
          ...thread.tags.take(3).map((tag) => Container(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                decoration: BoxDecoration(
                  color: colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(tag, style: TextStyle(fontSize: 10, color: colorScheme.onSurfaceVariant)),
              )),
        ],
      ),
      onTap: () => collab.selectThread(thread),
    );
  }
}

// ── Thread Detail Panel ──────────────────────────────────────────────

class _ThreadDetailPanel extends StatelessWidget {
  final CollaborationProvider collab;
  const _ThreadDetailPanel({required this.collab});

  @override
  Widget build(BuildContext context) {
    final thread = collab.selectedThread!;
    final colorScheme = Theme.of(context).colorScheme;

    return Column(
      children: [
        // Thread header
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: colorScheme.surfaceContainerHighest.withAlpha(60),
            border: Border(bottom: BorderSide(color: colorScheme.outlineVariant)),
          ),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(thread.title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    Wrap(
                      spacing: 6,
                      children: thread.tags.map((tag) => Chip(
                        label: Text(tag),
                        visualDensity: VisualDensity.compact,
                        labelStyle: const TextStyle(fontSize: 11),
                        padding: EdgeInsets.zero,
                      )).toList(),
                    ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text('by ${thread.createdBy}', style: TextStyle(fontSize: 12, color: colorScheme.onSurfaceVariant)),
                  Text('${thread.messages.length} messages', style: TextStyle(fontSize: 12, color: colorScheme.onSurfaceVariant)),
                ],
              ),
            ],
          ),
        ),
        // Messages
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: thread.messages.length,
            itemBuilder: (context, index) {
              return _MessageBubble(message: thread.messages[index]);
            },
          ),
        ),
      ],
    );
  }
}

class _MessageBubble extends StatelessWidget {
  final CollaborationMessage message;
  const _MessageBubble({required this.message});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  radius: 12,
                  backgroundColor: colorScheme.primaryContainer,
                  child: Text(
                    message.fromAgent.substring(0, 1).toUpperCase(),
                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: colorScheme.onPrimaryContainer),
                  ),
                ),
                const SizedBox(width: 8),
                Text(message.fromAgent, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                const Spacer(),
                Text(
                  _formatTime(message.timestamp),
                  style: TextStyle(fontSize: 11, color: colorScheme.onSurfaceVariant),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(message.content, style: const TextStyle(fontSize: 13)),
            if (message.tags.isNotEmpty) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 4,
                children: message.tags.map((tag) => Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: colorScheme.secondaryContainer.withAlpha(150),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(tag, style: TextStyle(fontSize: 10, color: colorScheme.onSecondaryContainer)),
                )).toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _formatTime(DateTime dt) {
    final diff = DateTime.now().difference(dt);
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
  }
}

// ── Empty State ──────────────────────────────────────────────────────

class _EmptyThreadPanel extends StatelessWidget {
  const _EmptyThreadPanel();

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.science_outlined, size: 64, color: colorScheme.onSurfaceVariant.withAlpha(80)),
          const SizedBox(height: 12),
          Text(
            'Agent Collaboration Space',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: colorScheme.onSurfaceVariant),
          ),
          const SizedBox(height: 4),
          Text(
            'Select a thread to view agent discussions & insights',
            style: TextStyle(fontSize: 13, color: colorScheme.onSurfaceVariant.withAlpha(180)),
          ),
        ],
      ),
    );
  }
}
