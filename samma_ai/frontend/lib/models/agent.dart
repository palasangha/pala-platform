/// Agent hierarchy levels
enum AgentHierarchy {
  orchestrator,
  teamLead,
  agent,
}

/// Model representing an AI agent
class Agent {
  final String name;
  final String displayName;
  final String description;
  final AgentStatus status;
  final String? currentTask;
  final List<String> skills;
  final DateTime? lastActive;
  final String defaultModel;
  final String activeModel;
  final AgentHierarchy hierarchyLevel;
  final String? parentAgentName;

  Agent({
    required this.name,
    required this.displayName,
    required this.description,
    this.status = AgentStatus.idle,
    this.currentTask,
    this.skills = const [],
    this.lastActive,
    this.defaultModel = 'claude-sonnet-4-20250514',
    String? activeModel,
    this.hierarchyLevel = AgentHierarchy.agent,
    this.parentAgentName,
  }) : activeModel = activeModel ?? defaultModel;

  factory Agent.fromJson(Map<String, dynamic> json) {
    return Agent(
      name: json['name'] ?? '',
      displayName: json['displayName'] ?? json['name'] ?? '',
      description: json['description'] ?? '',
      status: AgentStatus.values.firstWhere(
        (s) => s.name == json['status'],
        orElse: () => AgentStatus.idle,
      ),
      currentTask: json['currentTask'],
      skills: List<String>.from(json['skills'] ?? []),
      lastActive: json['lastActive'] != null
          ? DateTime.parse(json['lastActive'])
          : null,
      defaultModel: json['defaultModel'] ?? 'claude-sonnet-4-20250514',
      activeModel: json['activeModel'],
      hierarchyLevel: AgentHierarchy.values.firstWhere(
        (h) => h.name == json['hierarchyLevel'],
        orElse: () => AgentHierarchy.agent,
      ),
      parentAgentName: json['parentAgentName'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'displayName': displayName,
      'description': description,
      'status': status.name,
      'currentTask': currentTask,
      'skills': skills,
      'lastActive': lastActive?.toIso8601String(),
      'defaultModel': defaultModel,
      'activeModel': activeModel,
      'hierarchyLevel': hierarchyLevel.name,
      'parentAgentName': parentAgentName,
    };
  }
}

/// Agent status enum
enum AgentStatus {
  active,
  busy,
  idle,
  offline,
}

/// Model representing an agent team
class AgentTeam {
  final String name;
  final String displayName;
  final String description;
  final String lead;
  final List<Agent> agents;

  AgentTeam({
    required this.name,
    required this.displayName,
    required this.description,
    required this.lead,
    required this.agents,
  });

  factory AgentTeam.fromJson(Map<String, dynamic> json) {
    final agentsMap = json['agents'] as Map<String, dynamic>? ?? {};
    final agents = agentsMap.entries.map((entry) {
      final agentData = entry.value as Map<String, dynamic>;
      return Agent(
        name: entry.key,
        displayName: agentData['name'] ?? entry.key,
        description: agentData['description'] ?? '',
        skills: List<String>.from(agentData['skills'] ?? []),
      );
    }).toList();

    return AgentTeam(
      name: json['name'] ?? '',
      displayName: json['displayName'] ?? json['name'] ?? '',
      description: json['description'] ?? '',
      lead: json['lead'] ?? '',
      agents: agents,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'displayName': displayName,
      'description': description,
      'lead': lead,
      'agents': {for (var a in agents) a.name: a.toJson()},
    };
  }
}

/// Model for agent messages
class AgentMessage {
  final String id;
  final String from;
  final String to;
  final String subject;
  final String content;
  final DateTime timestamp;
  final MessagePriority priority;
  final bool requiresResponse;
  final bool read;

  AgentMessage({
    required this.id,
    required this.from,
    required this.to,
    required this.subject,
    required this.content,
    required this.timestamp,
    this.priority = MessagePriority.medium,
    this.requiresResponse = false,
    this.read = false,
  });

  factory AgentMessage.fromJson(Map<String, dynamic> json) {
    return AgentMessage(
      id: json['id'] ?? '',
      from: json['from'] ?? '',
      to: json['to'] ?? '',
      subject: json['subject'] ?? '',
      content: json['content'] ?? '',
      timestamp: DateTime.parse(json['timestamp'] ?? DateTime.now().toIso8601String()),
      priority: MessagePriority.values.firstWhere(
        (p) => p.name == json['priority'],
        orElse: () => MessagePriority.medium,
      ),
      requiresResponse: json['requiresResponse'] ?? false,
      read: json['read'] ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'from': from,
      'to': to,
      'subject': subject,
      'content': content,
      'timestamp': timestamp.toIso8601String(),
      'priority': priority.name,
      'requiresResponse': requiresResponse,
      'read': read,
    };
  }
}

/// Message priority enum
enum MessagePriority {
  critical,
  high,
  medium,
  low,
}

/// Model for agent tasks
class AgentTask {
  final String id;
  final String title;
  final String description;
  final String assignee;
  final String? assignedBy;
  final TaskStatus status;
  final TaskPriority priority;
  final DateTime createdAt;
  final DateTime? deadline;
  final DateTime? completedAt;

  AgentTask({
    required this.id,
    required this.title,
    required this.description,
    required this.assignee,
    this.assignedBy,
    this.status = TaskStatus.pending,
    this.priority = TaskPriority.medium,
    required this.createdAt,
    this.deadline,
    this.completedAt,
  });

  factory AgentTask.fromJson(Map<String, dynamic> json) {
    return AgentTask(
      id: json['id'] ?? '',
      title: json['title'] ?? '',
      description: json['description'] ?? '',
      assignee: json['assignee'] ?? '',
      assignedBy: json['assignedBy'],
      status: TaskStatus.values.firstWhere(
        (s) => s.name == json['status'],
        orElse: () => TaskStatus.pending,
      ),
      priority: TaskPriority.values.firstWhere(
        (p) => p.name == json['priority'],
        orElse: () => TaskPriority.medium,
      ),
      createdAt: DateTime.parse(json['createdAt'] ?? DateTime.now().toIso8601String()),
      deadline: json['deadline'] != null ? DateTime.parse(json['deadline']) : null,
      completedAt: json['completedAt'] != null ? DateTime.parse(json['completedAt']) : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'description': description,
      'assignee': assignee,
      'assignedBy': assignedBy,
      'status': status.name,
      'priority': priority.name,
      'createdAt': createdAt.toIso8601String(),
      'deadline': deadline?.toIso8601String(),
      'completedAt': completedAt?.toIso8601String(),
    };
  }
}

/// Task status enum
enum TaskStatus {
  pending,
  inProgress,
  completed,
  failed,
}

/// Task priority enum
enum TaskPriority {
  critical,
  high,
  medium,
  low,
}
