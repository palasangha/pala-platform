/// Models for the Agent Collaboration / R&D workspace

/// A single message within a collaboration thread
class CollaborationMessage {
  final String id;
  final String fromAgent;
  final String content;
  final List<String> tags;
  final DateTime timestamp;

  CollaborationMessage({
    required this.id,
    required this.fromAgent,
    required this.content,
    this.tags = const [],
    required this.timestamp,
  });

  factory CollaborationMessage.fromJson(Map<String, dynamic> json) {
    return CollaborationMessage(
      id: json['id'] ?? '',
      fromAgent: json['from_agent'] ?? '',
      content: json['content'] ?? '',
      tags: List<String>.from(json['tags'] ?? []),
      timestamp: json['timestamp'] != null
          ? DateTime.parse(json['timestamp'])
          : DateTime.now(),
    );
  }
}

/// A threaded discussion in the collaboration space
class CollaborationThread {
  final String id;
  final String title;
  final String createdBy;
  final List<String> tags;
  final int messageCount;
  final DateTime createdAt;
  final List<CollaborationMessage> messages;

  CollaborationThread({
    required this.id,
    required this.title,
    required this.createdBy,
    this.tags = const [],
    this.messageCount = 0,
    required this.createdAt,
    this.messages = const [],
  });

  factory CollaborationThread.fromJson(Map<String, dynamic> json) {
    return CollaborationThread(
      id: json['id'] ?? '',
      title: json['title'] ?? '',
      createdBy: json['created_by'] ?? '',
      tags: List<String>.from(json['tags'] ?? []),
      messageCount: json['message_count'] ?? 0,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : DateTime.now(),
      messages: (json['messages'] as List<dynamic>?)
              ?.map((m) => CollaborationMessage.fromJson(m))
              .toList() ??
          [],
    );
  }
}
