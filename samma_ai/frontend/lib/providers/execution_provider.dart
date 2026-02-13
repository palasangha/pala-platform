import 'package:flutter/foundation.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/execution_log.dart';

/// Provider for live execution monitoring
class ExecutionProvider extends ChangeNotifier {
  static const String _defaultBaseUrl = 'http://localhost:5001';

  List<ExecutionLog> _logs = [];
  QueueStatus _queueStatus = QueueStatus();
  bool _isLoading = false;
  String? _filterAgent;
  String? _filterStatus;

  List<ExecutionLog> get logs => List.unmodifiable(_logs);
  QueueStatus get queueStatus => _queueStatus;
  bool get isLoading => _isLoading;
  String? get filterAgent => _filterAgent;
  String? get filterStatus => _filterStatus;

  List<ExecutionLog> get filteredLogs {
    var result = _logs;
    if (_filterAgent != null && _filterAgent!.isNotEmpty) {
      result = result.where((l) => l.agentName == _filterAgent).toList();
    }
    if (_filterStatus != null && _filterStatus!.isNotEmpty) {
      result = result.where((l) => l.status.name == _filterStatus).toList();
    }
    return result;
  }

  ExecutionProvider() {
    _loadMockData();
  }

  void setAgentFilter(String? agent) {
    _filterAgent = agent;
    notifyListeners();
  }

  void setStatusFilter(String? status) {
    _filterStatus = status;
    notifyListeners();
  }

  /// Fetch execution logs from backend
  Future<void> fetchLogs({String? baseUrl}) async {
    _isLoading = true;
    notifyListeners();

    try {
      final url = baseUrl ?? _defaultBaseUrl;
      final response =
          await http.get(Uri.parse('$url/api/agents/execution-logs')).timeout(
                const Duration(seconds: 10),
              );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _logs = (data['logs'] as List<dynamic>?)
                ?.map((l) => ExecutionLog.fromJson(l))
                .toList() ??
            [];
        if (data['queue_status'] != null) {
          _queueStatus = QueueStatus.fromJson(data['queue_status']);
        }
      }
    } catch (e) {
      // Keep mock data on failure
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Pause a task
  Future<void> pauseTask(String logId, {String? baseUrl}) async {
    try {
      final url = baseUrl ?? _defaultBaseUrl;
      await http.post(Uri.parse('$url/api/agents/execution/$logId/pause'));
      await fetchLogs(baseUrl: baseUrl);
    } catch (e) {
      // Update locally
      _updateLocalStatus(logId, ExecutionStatus.paused);
    }
  }

  /// Cancel a task
  Future<void> cancelTask(String logId, {String? baseUrl}) async {
    try {
      final url = baseUrl ?? _defaultBaseUrl;
      await http.post(Uri.parse('$url/api/agents/execution/$logId/cancel'));
      await fetchLogs(baseUrl: baseUrl);
    } catch (e) {
      _updateLocalStatus(logId, ExecutionStatus.cancelled);
    }
  }

  /// Replay a task
  Future<void> replayTask(String logId, {String? baseUrl}) async {
    try {
      final url = baseUrl ?? _defaultBaseUrl;
      await http.post(Uri.parse('$url/api/agents/execution/$logId/replay'));
      await fetchLogs(baseUrl: baseUrl);
    } catch (e) {
      // Silently fail
    }
  }

  void _updateLocalStatus(String logId, ExecutionStatus newStatus) {
    final idx = _logs.indexWhere((l) => l.id == logId);
    if (idx != -1) {
      final old = _logs[idx];
      _logs[idx] = ExecutionLog(
        id: old.id,
        taskName: old.taskName,
        agentName: old.agentName,
        modelUsed: old.modelUsed,
        status: newStatus,
        delegatedBy: old.delegatedBy,
        startTime: old.startTime,
        endTime: newStatus == ExecutionStatus.paused ? null : DateTime.now(),
        error: old.error,
        retryCount: old.retryCount,
        logLines: [...old.logLines, 'Status → ${newStatus.name}'],
        dependencies: old.dependencies,
      );
      notifyListeners();
    }
  }

  void _loadMockData() {
    final now = DateTime.now();
    _logs = [
      ExecutionLog(
        id: 'exec-1',
        taskName: 'Build Tipitaka search index',
        agentName: 'database-architect',
        modelUsed: 'ollama:llama3.2-vision:latest',
        status: ExecutionStatus.completed,
        startTime: now.subtract(const Duration(hours: 2)),
        endTime: now.subtract(const Duration(hours: 1, minutes: 45)),
        durationSeconds: 900,
        logLines: ['Task queued', 'Status → running', 'Status → completed'],
      ),
      ExecutionLog(
        id: 'exec-2',
        taskName: 'Generate sutta embeddings',
        agentName: 'embeddings-trainer',
        modelUsed: 'claude-sonnet-4-20250514',
        status: ExecutionStatus.running,
        startTime: now.subtract(const Duration(minutes: 30)),
        durationSeconds: 1800,
        logLines: ['Task queued', 'Status → running', 'Processing batch 3/10...'],
      ),
      ExecutionLog(
        id: 'exec-3',
        taskName: 'Pali diacritics validation',
        agentName: 'pali-linguist',
        modelUsed: 'claude-sonnet-4-20250514',
        status: ExecutionStatus.completed,
        startTime: now.subtract(const Duration(hours: 1)),
        endTime: now.subtract(const Duration(minutes: 50)),
        durationSeconds: 600,
        logLines: ['Task queued', 'Status → running', 'Status → completed'],
      ),
      ExecutionLog(
        id: 'exec-4',
        taskName: 'Dashboard responsive layout',
        agentName: 'flutter-web',
        modelUsed: 'gpt-4o',
        status: ExecutionStatus.running,
        startTime: now.subtract(const Duration(minutes: 15)),
        durationSeconds: 900,
        logLines: ['Task queued', 'Status → running'],
      ),
      ExecutionLog(
        id: 'exec-5',
        taskName: 'API rate limit middleware',
        agentName: 'flask-api',
        modelUsed: 'claude-sonnet-4-20250514',
        status: ExecutionStatus.queued,
        startTime: now.subtract(const Duration(minutes: 5)),
        logLines: ['Task queued by pala-jarvis'],
      ),
      ExecutionLog(
        id: 'exec-6',
        taskName: 'Docker compose optimization',
        agentName: 'docker-builder',
        modelUsed: 'ollama:llama3.2-vision:latest',
        status: ExecutionStatus.failed,
        startTime: now.subtract(const Duration(hours: 3)),
        endTime: now.subtract(const Duration(hours: 2, minutes: 50)),
        durationSeconds: 600,
        error: 'Container build timeout after 600s',
        retryCount: 1,
        logLines: ['Task queued', 'Status → running', 'ERROR: Container build timeout'],
      ),
      ExecutionLog(
        id: 'exec-7',
        taskName: 'Unit test coverage report',
        agentName: 'test-runner',
        modelUsed: 'gpt-4o',
        status: ExecutionStatus.completed,
        startTime: now.subtract(const Duration(hours: 4)),
        endTime: now.subtract(const Duration(hours: 3, minutes: 30)),
        durationSeconds: 1800,
        logLines: ['Task queued', 'Status → running', 'Status → completed'],
      ),
      ExecutionLog(
        id: 'exec-8',
        taskName: 'Token usage analysis',
        agentName: 'cost-tracker',
        modelUsed: 'claude-sonnet-4-20250514',
        status: ExecutionStatus.paused,
        startTime: now.subtract(const Duration(minutes: 45)),
        logLines: ['Task queued', 'Status → running', 'Status → paused'],
      ),
    ];

    _queueStatus = QueueStatus(
      total: 8,
      queued: 1,
      running: 2,
      paused: 1,
      completed: 3,
      failed: 1,
      cancelled: 0,
    );
  }
}
