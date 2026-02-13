/// Model for chat messages
class ChatMessage {
  final String id;
  final String content;
  final bool isUser;
  final DateTime timestamp;
  final DhammaResponse? dhammaResponse;

  ChatMessage({
    required this.id,
    required this.content,
    required this.isUser,
    required this.timestamp,
    this.dhammaResponse,
  });

  factory ChatMessage.user(String content) {
    return ChatMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      content: content,
      isUser: true,
      timestamp: DateTime.now(),
    );
  }

  factory ChatMessage.assistant(String content, {DhammaResponse? dhammaResponse}) {
    return ChatMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      content: content,
      isUser: false,
      timestamp: DateTime.now(),
      dhammaResponse: dhammaResponse,
    );
  }

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: json['id'] ?? '',
      content: json['content'] ?? json['response']?['formatted_text'] ?? '',
      isUser: json['is_user'] ?? false,
      timestamp: json['timestamp'] != null
          ? DateTime.parse(json['timestamp'])
          : DateTime.now(),
      dhammaResponse: json['response'] != null
          ? DhammaResponse.fromJson(json['response'])
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'content': content,
      'is_user': isUser,
      'timestamp': timestamp.toIso8601String(),
      if (dhammaResponse != null) 'response': dhammaResponse!.toJson(),
    };
  }
}

/// Model for the 4-part Dhamma response
class DhammaResponse {
  final ResponseSection databaseSummary;
  final ResponseSection interpretiveSummary;
  final List<Teaching> teachings;
  final ResponseSection finalSummary;
  final String formattedText;

  DhammaResponse({
    required this.databaseSummary,
    required this.interpretiveSummary,
    required this.teachings,
    required this.finalSummary,
    required this.formattedText,
  });

  factory DhammaResponse.fromJson(Map<String, dynamic> json) {
    return DhammaResponse(
      databaseSummary: ResponseSection.fromJson(
        json['database_summary'] ?? {},
      ),
      interpretiveSummary: ResponseSection.fromJson(
        json['interpretive_summary'] ?? {},
      ),
      teachings: (json['teachings'] as List<dynamic>?)
              ?.map((t) => Teaching.fromJson(t))
              .toList() ??
          [],
      finalSummary: ResponseSection.fromJson(
        json['final_summary'] ?? {},
      ),
      formattedText: json['formatted_text'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'database_summary': databaseSummary.toJson(),
      'interpretive_summary': interpretiveSummary.toJson(),
      'teachings': teachings.map((t) => t.toJson()).toList(),
      'final_summary': finalSummary.toJson(),
      'formatted_text': formattedText,
    };
  }
}

/// Model for a response section
class ResponseSection {
  final String title;
  final String content;

  ResponseSection({
    required this.title,
    required this.content,
  });

  factory ResponseSection.fromJson(Map<String, dynamic> json) {
    return ResponseSection(
      title: json['title'] ?? '',
      content: json['content'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'title': title,
      'content': content,
    };
  }
}

/// Model for a teaching with references
class Teaching {
  final String title;
  final String pali;
  final String english;
  final String explanation;
  final Map<String, String> references;

  Teaching({
    required this.title,
    required this.pali,
    required this.english,
    required this.explanation,
    required this.references,
  });

  factory Teaching.fromJson(Map<String, dynamic> json) {
    return Teaching(
      title: json['title'] ?? '',
      pali: json['pali'] ?? '',
      english: json['english'] ?? '',
      explanation: json['explanation'] ?? '',
      references: Map<String, String>.from(json['references'] ?? {}),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'title': title,
      'pali': pali,
      'english': english,
      'explanation': explanation,
      'references': references,
    };
  }
}
