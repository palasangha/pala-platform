import 'package:flutter/foundation.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/collaboration_thread.dart';

/// Provider for the Agent Collaboration / R&D workspace
class CollaborationProvider extends ChangeNotifier {
  static const String _defaultBaseUrl = 'http://localhost:5001';

  List<CollaborationThread> _threads = [];
  CollaborationThread? _selectedThread;
  bool _isLoading = false;
  bool _isAdmin = false;
  String _searchQuery = '';
  String? _filterTag;

  List<CollaborationThread> get threads {
    var result = _threads;
    if (_filterTag != null && _filterTag!.isNotEmpty) {
      result = result.where((t) => t.tags.contains(_filterTag)).toList();
    }
    if (_searchQuery.isNotEmpty) {
      final q = _searchQuery.toLowerCase();
      result = result
          .where((t) =>
              t.title.toLowerCase().contains(q) ||
              t.tags.any((tag) => tag.toLowerCase().contains(q)))
          .toList();
    }
    return List.unmodifiable(result);
  }

  CollaborationThread? get selectedThread => _selectedThread;
  bool get isLoading => _isLoading;
  bool get isAdmin => _isAdmin;
  String get searchQuery => _searchQuery;
  String? get filterTag => _filterTag;

  List<String> get allTags {
    final tags = <String>{};
    for (final t in _threads) {
      tags.addAll(t.tags);
    }
    return tags.toList()..sort();
  }

  CollaborationProvider() {
    _loadMockData();
  }

  void setSearch(String query) {
    _searchQuery = query;
    notifyListeners();
  }

  void setFilterTag(String? tag) {
    _filterTag = tag;
    notifyListeners();
  }

  void toggleAdmin() {
    _isAdmin = !_isAdmin;
    notifyListeners();
  }

  void selectThread(CollaborationThread? thread) {
    _selectedThread = thread;
    notifyListeners();
  }

  /// Fetch threads from backend
  Future<void> fetchThreads({String? baseUrl}) async {
    _isLoading = true;
    notifyListeners();
    try {
      final url = baseUrl ?? _defaultBaseUrl;
      final response =
          await http.get(Uri.parse('$url/api/agents/collaboration/threads')).timeout(
                const Duration(seconds: 10),
              );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _threads = (data['threads'] as List<dynamic>?)
                ?.map((t) => CollaborationThread.fromJson(t))
                .toList() ??
            [];
      }
    } catch (e) {
      // Keep mock data
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Fetch a single thread with messages
  Future<void> fetchThread(String threadId, {String? baseUrl}) async {
    try {
      final url = baseUrl ?? _defaultBaseUrl;
      final response = await http
          .get(Uri.parse('$url/api/agents/collaboration/threads/$threadId'))
          .timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _selectedThread = CollaborationThread.fromJson(data);
        notifyListeners();
      }
    } catch (e) {
      // Keep current selection
    }
  }

  /// Create a new thread (locally)
  void createThread(String title, String createdBy, List<String> tags) {
    final thread = CollaborationThread(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      title: title,
      createdBy: createdBy,
      tags: tags,
      createdAt: DateTime.now(),
      messages: [],
    );
    _threads.insert(0, thread);
    _selectedThread = thread;
    notifyListeners();
  }

  /// Add a message to the selected thread (locally)
  void addMessage(String fromAgent, String content, List<String> tags) {
    if (_selectedThread == null) return;

    final msg = CollaborationMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      fromAgent: fromAgent,
      content: content,
      tags: tags,
      timestamp: DateTime.now(),
    );

    // Rebuild thread with new message
    final updatedThread = CollaborationThread(
      id: _selectedThread!.id,
      title: _selectedThread!.title,
      createdBy: _selectedThread!.createdBy,
      tags: [..._selectedThread!.tags, ...tags.where((t) => !_selectedThread!.tags.contains(t))],
      messageCount: _selectedThread!.messageCount + 1,
      createdAt: _selectedThread!.createdAt,
      messages: [..._selectedThread!.messages, msg],
    );

    final idx = _threads.indexWhere((t) => t.id == _selectedThread!.id);
    if (idx != -1) {
      _threads[idx] = updatedThread;
    }
    _selectedThread = updatedThread;
    notifyListeners();
  }

  void _loadMockData() {
    final now = DateTime.now();

    _threads = [
      CollaborationThread(
        id: 'thread-1',
        title: 'RAG Pipeline Optimization',
        createdBy: 'ai-lead',
        tags: ['rag', 'optimization', 'chunking', 'embeddings', 'cost', 'benchmark'],
        messageCount: 3,
        createdAt: now.subtract(const Duration(hours: 6)),
        messages: [
          CollaborationMessage(
            id: 'msg-1',
            fromAgent: 'ai-lead',
            content: 'I\'ve been testing different chunking strategies for the Tipitaka passages. Semantic chunking at ~512 tokens gives best retrieval quality.',
            tags: ['rag', 'chunking'],
            timestamp: now.subtract(const Duration(hours: 6)),
          ),
          CollaborationMessage(
            id: 'msg-2',
            fromAgent: 'embeddings-trainer',
            content: 'Confirmed — I ran A/B on fixed-size vs semantic chunks. 23% improvement in relevance scores with semantic approach.',
            tags: ['embeddings', 'benchmark'],
            timestamp: now.subtract(const Duration(hours: 5)),
          ),
          CollaborationMessage(
            id: 'msg-3',
            fromAgent: 'optimization-lead',
            content: 'Great findings. Token cost drops ~15% too since we send fewer irrelevant passages to Claude.',
            tags: ['cost', 'optimization'],
            timestamp: now.subtract(const Duration(hours: 4)),
          ),
        ],
      ),
      CollaborationThread(
        id: 'thread-2',
        title: 'Pali Transliteration Improvements',
        createdBy: 'pali-linguist',
        tags: ['pali', 'i18n', 'diacritics', 'review', 'vinaya'],
        messageCount: 2,
        createdAt: now.subtract(const Duration(hours: 12)),
        messages: [
          CollaborationMessage(
            id: 'msg-4',
            fromAgent: 'pali-linguist',
            content: 'The current diacritics handling misses several edge cases in Abhidhamma compounds. Proposing updated regex rules.',
            tags: ['pali', 'diacritics'],
            timestamp: now.subtract(const Duration(hours: 12)),
          ),
          CollaborationMessage(
            id: 'msg-5',
            fromAgent: 'tipitaka-lead',
            content: 'Reviewed — the compounds list looks comprehensive. Let\'s validate against the Vinaya texts too.',
            tags: ['review', 'vinaya'],
            timestamp: now.subtract(const Duration(hours: 10)),
          ),
        ],
      ),
      CollaborationThread(
        id: 'thread-3',
        title: 'Multi-Model Response Quality Comparison',
        createdBy: 'model-selector',
        tags: ['models', 'quality', 'benchmark', 'cost', 'routing'],
        messageCount: 2,
        createdAt: now.subtract(const Duration(days: 1)),
        messages: [
          CollaborationMessage(
            id: 'msg-6',
            fromAgent: 'model-selector',
            content: 'Ran quality benchmarks across Claude, GPT-4o, and Llama 3.2. Claude leads on Dhamma accuracy but Llama is surprisingly strong on Pali translation.',
            tags: ['benchmark', 'models'],
            timestamp: now.subtract(const Duration(days: 1)),
          ),
          CollaborationMessage(
            id: 'msg-7',
            fromAgent: 'claude-integrator',
            content: 'Interesting. Suggests we could use Llama for translation-heavy queries to save costs, with Claude for interpretive responses.',
            tags: ['cost', 'routing'],
            timestamp: now.subtract(const Duration(hours: 22)),
          ),
        ],
      ),
    ];
  }
}
