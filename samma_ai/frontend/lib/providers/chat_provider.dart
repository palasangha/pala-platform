import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import '../models/chat_message.dart';
import '../services/api_service.dart';

/// Provider for managing chat state
class ChatProvider extends ChangeNotifier {
  final ApiService _apiService = ApiService();
  final ScrollController scrollController = ScrollController();

  final List<ChatMessage> _messages = [];
  bool _isLoading = false;
  String? _conversationId;
  String? _error;
  String _selectedModelId = 'claude-sonnet-4-20250514'; // Default model

  List<Map<String, dynamic>> _availableModels = [];
  List<Map<String, dynamic>> get availableModels => _availableModels;
  List<ChatMessage> get messages => List.unmodifiable(_messages);
  bool get isLoading => _isLoading;
  String? get conversationId => _conversationId;
  String? get error => _error;
  String get selectedModelId => _selectedModelId;

  ChatProvider() {
    _loadChatHistory();
    fetchAvailableModels();
  }

  /// Load chat history from local storage
  Future<void> _loadChatHistory() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final conversationId = prefs.getString('chat_conversation_id');
      final messagesJson = prefs.getString('chat_messages');
      final modelId = prefs.getString('chat_model_id');

      if (conversationId != null) {
        _conversationId = conversationId;
      }
      if (modelId != null) {
        _selectedModelId = modelId;
      }
      if (messagesJson != null) {
        final List<dynamic> messagesList = jsonDecode(messagesJson);
        _messages.clear();
        _messages.addAll(
          messagesList.map((m) => ChatMessage.fromJson(m)).toList(),
        );
      }
      notifyListeners();
    } catch (e) {
      // Ignore errors loading from storage
    }
  }

  /// Save chat history to local storage
  Future<void> _saveChatHistory() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      if (_conversationId != null) {
        await prefs.setString('chat_conversation_id', _conversationId!);
      }
      await prefs.setString('chat_model_id', _selectedModelId);
      final messagesJson = jsonEncode(
        _messages.map((m) => m.toJson()).toList(),
      );
      await prefs.setString('chat_messages', messagesJson);
    } catch (e) {
      // Ignore errors saving to storage
    }
  }

  /// Fetch available models from backend
  Future<void> fetchAvailableModels() async {
    try {
      final response = await _apiService.getAvailableModels();
      _availableModels = List<Map<String, dynamic>>.from(response['models']);
      
      // If selected model is not in the list and list is not empty, 
      // check if it's available by ID
      bool isSelectedAvailable = _availableModels.any((m) => m['id'] == _selectedModelId);
      if (!isSelectedAvailable && _availableModels.isNotEmpty) {
        // Find first available model
        final firstAvailable = _availableModels.firstWhere(
          (m) => m['available'] == true,
          orElse: () => _availableModels.first,
        );
        _selectedModelId = firstAvailable['id'];
      }
      notifyListeners();
    } catch (e) {
      // Fallback to defaults if API fails
      _availableModels = [
        {'id': 'claude-sonnet-4-20250514', 'name': 'Claude Sonnet', 'provider': 'claude', 'available': true},
        {'id': 'gpt-4o', 'name': 'GPT-4o', 'provider': 'openai', 'available': false},
      ];
      notifyListeners();
    }
  }

  /// Change the selected AI model
  void setModel(String modelId) {
    _selectedModelId = modelId;
    _saveChatHistory();
    notifyListeners();
  }

  /// Send a message and get response from Samma AI
  Future<void> sendMessage(String content) async {
    if (content.trim().isEmpty) return;

    // Clear any previous error
    _error = null;

    // Add user message
    final userMessage = ChatMessage.user(content);
    _messages.add(userMessage);
    _isLoading = true;
    notifyListeners();

    // Scroll to bottom
    _scrollToBottom();

    try {
      // Send to API with selected model
      final response = await _apiService.sendChatMessage(
        message: content,
        conversationId: _conversationId,
        modelId: _selectedModelId,
      );

      // Update conversation ID
      _conversationId = response['conversation_id'];

      // Create assistant message
      final formattedText = response['response']?['formatted_text'] ??
          response['response']?.toString() ??
          'No response received';

      final assistantMessage = ChatMessage.assistant(
        formattedText,
        dhammaResponse: response['response'] != null
            ? DhammaResponse.fromJson(response['response'])
            : null,
      );

      _messages.add(assistantMessage);
      
      // Save to local storage
      await _saveChatHistory();
    } catch (e) {
      _error = e.toString();

      // Add error message
      _messages.add(ChatMessage.assistant(
        'I apologize, but I encountered an error processing your request. '
        'Please try again.\n\nError: ${e.toString()}',
      ));
    } finally {
      _isLoading = false;
      notifyListeners();
      _scrollToBottom();
    }
  }

  /// Clear chat history
  Future<void> clearChat() async {
    _messages.clear();
    _conversationId = null;
    _error = null;
    
    // Clear from storage
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('chat_conversation_id');
      await prefs.remove('chat_messages');
    } catch (e) {
      // Ignore errors
    }
    
    notifyListeners();
  }

  /// Scroll to bottom of chat
  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (scrollController.hasClients) {
        scrollController.animateTo(
          scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  void dispose() {
    scrollController.dispose();
    super.dispose();
  }
}
