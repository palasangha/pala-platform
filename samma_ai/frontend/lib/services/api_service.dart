import 'dart:convert';
import 'package:http/http.dart' as http;

/// Service for communicating with the Samma AI backend API
class ApiService {
  static const String _defaultBaseUrl = 'http://localhost:5001';

  String _baseUrl;

  ApiService({String? baseUrl}) : _baseUrl = baseUrl ?? _defaultBaseUrl;

  /// Set the base URL for API calls
  void setBaseUrl(String url) {
    _baseUrl = url;
  }

  /// Send a chat message and receive 4-part Dhamma response
  Future<Map<String, dynamic>> sendChatMessage({
    required String message,
    String? conversationId,
    String? modelId,
  }) async {
    final uri = Uri.parse('$_baseUrl/api/chat');

    // Use a client with extended timeout for long-running AI requests (Llama takes ~65 seconds)
    final client = http.Client();
    try {
      final response = await client.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'message': message,
          if (conversationId != null) 'conversation_id': conversationId,
          if (modelId != null) 'model_id': modelId,
        }),
      ).timeout(
        const Duration(minutes: 3), // Extended timeout for AI response generation
        onTimeout: () {
          throw ApiException('Request timeout: AI response took too long', 408);
        },
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      } else {
        final error = jsonDecode(response.body);
        throw ApiException(
          error['error'] ?? 'Unknown error',
          response.statusCode,
        );
      }
    } finally {
      client.close();
    }
  }

  /// Look up a Pali word
  Future<Map<String, dynamic>> lookupWord(String word) async {
    final uri = Uri.parse('$_baseUrl/api/lookup/$word');
    final client = http.Client();

    try {
      final response = await client.get(uri).timeout(
        const Duration(seconds: 30),
        onTimeout: () {
          throw ApiException('Request timeout: Server not responding', 408);
        },
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      } else if (response.statusCode == 404) {
        throw ApiException('Word not found', 404);
      } else {
        final error = jsonDecode(response.body);
        throw ApiException(
          error['error'] ?? 'Unknown error',
          response.statusCode,
        );
      }
    } finally {
      client.close();
    }
  }

  /// Get a sutta by reference (e.g., MN 10, DN 22)
  Future<Map<String, dynamic>> getSutta(String reference) async {
    final uri = Uri.parse('$_baseUrl/api/sutta/$reference');

    final response = await http.get(uri);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else if (response.statusCode == 404) {
      throw ApiException('Sutta not found', 404);
    } else {
      final error = jsonDecode(response.body);
      throw ApiException(
        error['error'] ?? 'Unknown error',
        response.statusCode,
      );
    }
  }

  /// Full-text search in Tipitaka
  Future<Map<String, dynamic>> search({
    required String query,
    int limit = 20,
    int offset = 0,
  }) async {
    final uri = Uri.parse('$_baseUrl/api/search').replace(
      queryParameters: {
        'q': query,
        'limit': limit.toString(),
        'offset': offset.toString(),
      },
    );

    final response = await http.get(uri);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      final error = jsonDecode(response.body);
      throw ApiException(
        error['error'] ?? 'Unknown error',
        response.statusCode,
      );
    }
  }

  /// Get chat history for a conversation
  Future<Map<String, dynamic>> getChatHistory(String conversationId) async {
    final uri = Uri.parse('$_baseUrl/api/chat/history/$conversationId');

    final response = await http.get(uri);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      final error = jsonDecode(response.body);
      throw ApiException(
        error['error'] ?? 'Unknown error',
        response.statusCode,
      );
    }
  }

  /// Health check
  Future<bool> healthCheck() async {
    try {
      final uri = Uri.parse('$_baseUrl/api/health');
      final response = await http.get(uri);
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  // ── Models API ──────────────────────────────────────────────────────

  /// Get available models
  Future<Map<String, dynamic>> getAvailableModels() async {
    return _get('/api/models');
  }

  /// Discover Ollama models
  Future<Map<String, dynamic>> discoverOllamaModels() async {
    return _get('/api/models/ollama/discover');
  }

  /// Test a model endpoint
  Future<Map<String, dynamic>> testModelEndpoint(String modelId) async {
    return _post('/api/models/test', {'model_id': modelId});
  }

  // ── Agents API ─────────────────────────────────────────────────────

  /// Get agent hierarchy
  Future<Map<String, dynamic>> getAgents() async {
    return _get('/api/agents');
  }

  /// Delegate task via Pala-Jarvis
  Future<Map<String, dynamic>> delegateTask(String description, {String? targetTeam, String priority = 'medium'}) async {
    return _post('/api/agents/delegate', {
      'description': description,
      'target_team': targetTeam,
      'priority': priority,
    });
  }

  /// Get delegations
  Future<Map<String, dynamic>> getDelegations() async {
    return _get('/api/agents/delegations');
  }

  // ── Execution Monitor API ──────────────────────────────────────────

  /// Get execution logs
  Future<Map<String, dynamic>> getExecutionLogs({String? agent, String? status}) async {
    final params = <String, String>{};
    if (agent != null) params['agent'] = agent;
    if (status != null) params['status'] = status;
    return _get('/api/agents/execution-logs', queryParameters: params);
  }

  /// Pause/cancel/replay execution
  Future<Map<String, dynamic>> pauseExecution(String logId) async {
    return _post('/api/agents/execution/$logId/pause', {});
  }

  Future<Map<String, dynamic>> cancelExecution(String logId) async {
    return _post('/api/agents/execution/$logId/cancel', {});
  }

  Future<Map<String, dynamic>> replayExecution(String logId) async {
    return _post('/api/agents/execution/$logId/replay', {});
  }

  // ── Collaboration API ──────────────────────────────────────────────

  /// Get collaboration threads
  Future<Map<String, dynamic>> getCollaborationThreads({String? tag, String? search}) async {
    final params = <String, String>{};
    if (tag != null) params['tag'] = tag;
    if (search != null) params['search'] = search;
    return _get('/api/agents/collaboration/threads', queryParameters: params);
  }

  /// Get thread detail
  Future<Map<String, dynamic>> getCollaborationThread(String threadId) async {
    return _get('/api/agents/collaboration/threads/$threadId');
  }

  /// Create collaboration thread
  Future<Map<String, dynamic>> createCollaborationThread(String title, String createdBy, List<String> tags) async {
    return _post('/api/agents/collaboration/threads', {
      'title': title,
      'created_by': createdBy,
      'tags': tags,
    });
  }

  /// Add message to thread
  Future<Map<String, dynamic>> addCollaborationMessage(String threadId, String fromAgent, String content, List<String> tags) async {
    return _post('/api/agents/collaboration/threads/$threadId/messages', {
      'from_agent': fromAgent,
      'content': content,
      'tags': tags,
    });
  }

  // ── Private Helpers ────────────────────────────────────────────────

  Future<Map<String, dynamic>> _get(String path, {Map<String, String>? queryParameters}) async {
    Uri uri = Uri.parse('$_baseUrl$path');
    if (queryParameters != null && queryParameters.isNotEmpty) {
      uri = uri.replace(queryParameters: queryParameters);
    }

    final response = await http.get(uri).timeout(
          const Duration(seconds: 30),
          onTimeout: () {
            throw ApiException('Request timeout: Server not responding', 408);
          },
        );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    final error = jsonDecode(response.body);
    throw ApiException(error['error'] ?? 'Request failed', response.statusCode);
  }

  Future<Map<String, dynamic>> _post(String path, Map<String, dynamic> body) async {
    final response = await http.post(
      Uri.parse('$_baseUrl$path'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    ).timeout(
      const Duration(seconds: 30),
      onTimeout: () {
        throw ApiException('Request timeout: Server not responding', 408);
      },
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      return jsonDecode(response.body);
    }
    final error = jsonDecode(response.body);
    throw ApiException(error['error'] ?? 'Request failed', response.statusCode);
  }
}

/// Exception for API errors
class ApiException implements Exception {
  final String message;
  final int statusCode;

  ApiException(this.message, this.statusCode);

  @override
  String toString() => 'ApiException: $message (status: $statusCode)';
}
