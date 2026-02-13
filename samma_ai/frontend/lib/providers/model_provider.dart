import 'package:flutter/foundation.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;

/// Model information from the backend
class ModelInfo {
  final String id;
  final String name;
  final String provider;
  final bool available;
  final String endpoint;

  ModelInfo({
    required this.id,
    required this.name,
    required this.provider,
    this.available = true,
    this.endpoint = '',
  });

  factory ModelInfo.fromJson(Map<String, dynamic> json) {
    return ModelInfo(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      provider: json['provider'] ?? '',
      available: json['available'] ?? true,
      endpoint: json['endpoint'] ?? '',
    );
  }
}

/// Provider for managing model selection and discovery
class ModelProvider extends ChangeNotifier {
  static const String _defaultBaseUrl = 'http://localhost:5001';

  List<ModelInfo> _availableModels = [];
  Map<String, String> _agentModelOverrides = {};
  String? _sessionModelOverride;
  bool _isLoading = false;

  List<ModelInfo> get availableModels => List.unmodifiable(_availableModels);
  Map<String, String> get agentModelOverrides =>
      Map.unmodifiable(_agentModelOverrides);
  String? get sessionModelOverride => _sessionModelOverride;
  bool get isLoading => _isLoading;

  ModelProvider() {
    _loadDefaultModels();
  }

  /// Load default models (works without backend)
  void _loadDefaultModels() {
    _availableModels = [
      ModelInfo(
          id: 'claude-sonnet-4-20250514',
          name: 'Claude (claude-sonnet-4-20250514)',
          provider: 'claude'),
      ModelInfo(id: 'gpt-4o', name: 'OpenAI (gpt-4o)', provider: 'openai'),
      ModelInfo(
          id: 'ollama:llama3.2-vision:latest',
          name: 'Ollama (llama3.2-vision)',
          provider: 'ollama'),
    ];
    notifyListeners();
  }

  /// Fetch available models from backend
  Future<void> fetchModels({String? baseUrl}) async {
    _isLoading = true;
    notifyListeners();

    try {
      final url = baseUrl ?? _defaultBaseUrl;
      final response =
          await http.get(Uri.parse('$url/api/models')).timeout(
                const Duration(seconds: 10),
              );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final models = (data['models'] as List<dynamic>?) ?? [];
        _availableModels =
            models.map((m) => ModelInfo.fromJson(m)).toList();
      }
    } catch (e) {
      // Keep defaults on failure
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Discover Ollama models
  Future<void> discoverOllamaModels({String? baseUrl}) async {
    try {
      final url = baseUrl ?? _defaultBaseUrl;
      final response =
          await http.get(Uri.parse('$url/api/models/ollama/discover')).timeout(
                const Duration(seconds: 10),
              );
      if (response.statusCode == 200) {
        // Refresh full model list after discovery
        await fetchModels(baseUrl: baseUrl);
      }
    } catch (e) {
      // Silently fail — Ollama may not be available
    }
  }

  /// Set per-agent model override
  void setAgentModel(String agentName, String modelId) {
    _agentModelOverrides[agentName] = modelId;
    notifyListeners();
  }

  /// Clear per-agent model override
  void clearAgentModel(String agentName) {
    _agentModelOverrides.remove(agentName);
    notifyListeners();
  }

  /// Set session-wide model override
  void setSessionOverride(String? modelId) {
    _sessionModelOverride = modelId;
    notifyListeners();
  }

  /// Get effective model for an agent (session > per-agent > default)
  String getEffectiveModel(String agentName, String defaultModel) {
    if (_sessionModelOverride != null) return _sessionModelOverride!;
    return _agentModelOverrides[agentName] ?? defaultModel;
  }

  /// Get provider icon name for a model
  static String getProviderIcon(String provider) {
    switch (provider) {
      case 'claude':
        return '🟤'; // Brown for Anthropic
      case 'openai':
        return '🟢'; // Green for OpenAI
      case 'ollama':
        return '🦙';
      case 'copilot':
        return '🤖';
      default:
        return '⚡';
    }
  }
}
