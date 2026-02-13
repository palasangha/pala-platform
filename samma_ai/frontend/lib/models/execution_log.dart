/// Model for execution log entries displayed in Live Execution monitor
class ExecutionLog {
  final String id;
  final String taskName;
  final String agentName;
  final String modelUsed;
  final ExecutionStatus status;
  final String delegatedBy;
  final DateTime startTime;
  final DateTime? endTime;
  final double? durationSeconds;
  final String? error;
  final int retryCount;
  final List<String> logLines;
  final List<String> dependencies;

  ExecutionLog({
    required this.id,
    required this.taskName,
    required this.agentName,
    required this.modelUsed,
    this.status = ExecutionStatus.queued,
    this.delegatedBy = 'pala-jarvis',
    required this.startTime,
    this.endTime,
    this.durationSeconds,
    this.error,
    this.retryCount = 0,
    this.logLines = const [],
    this.dependencies = const [],
  });

  factory ExecutionLog.fromJson(Map<String, dynamic> json) {
    return ExecutionLog(
      id: json['id'] ?? '',
      taskName: json['task_name'] ?? '',
      agentName: json['agent_name'] ?? '',
      modelUsed: json['model_used'] ?? '',
      status: ExecutionStatus.values.firstWhere(
        (s) => s.name == json['status'],
        orElse: () => ExecutionStatus.queued,
      ),
      delegatedBy: json['delegated_by'] ?? 'pala-jarvis',
      startTime: json['start_time'] != null
          ? DateTime.parse(json['start_time'])
          : DateTime.now(),
      endTime:
          json['end_time'] != null ? DateTime.parse(json['end_time']) : null,
      durationSeconds: (json['duration_seconds'] as num?)?.toDouble(),
      error: json['error'],
      retryCount: json['retry_count'] ?? 0,
      logLines: List<String>.from(json['log_lines'] ?? []),
      dependencies: List<String>.from(json['dependencies'] ?? []),
    );
  }
}

/// Execution status enum
enum ExecutionStatus {
  queued,
  running,
  paused,
  completed,
  failed,
  cancelled,
}

/// Queue status summary
class QueueStatus {
  final int total;
  final int queued;
  final int running;
  final int paused;
  final int completed;
  final int failed;
  final int cancelled;

  QueueStatus({
    this.total = 0,
    this.queued = 0,
    this.running = 0,
    this.paused = 0,
    this.completed = 0,
    this.failed = 0,
    this.cancelled = 0,
  });

  factory QueueStatus.fromJson(Map<String, dynamic> json) {
    return QueueStatus(
      total: json['total'] ?? 0,
      queued: json['queued'] ?? 0,
      running: json['running'] ?? 0,
      paused: json['paused'] ?? 0,
      completed: json['completed'] ?? 0,
      failed: json['failed'] ?? 0,
      cancelled: json['cancelled'] ?? 0,
    );
  }
}
