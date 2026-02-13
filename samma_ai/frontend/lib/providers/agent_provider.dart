import 'package:flutter/foundation.dart';
import '../models/agent.dart';

/// Provider for managing agent state
class AgentProvider extends ChangeNotifier {
  bool _isLoading = false;
  List<AgentTeam> _teams = [];
  Map<String, List<AgentMessage>> _inboxes = {};
  List<AgentTask> _tasks = [];

  bool get isLoading => _isLoading;
  List<AgentTeam> get teams => List.unmodifiable(_teams);
  List<AgentTask> get tasks => List.unmodifiable(_tasks);

  AgentProvider() {
    _loadMockData();
  }

  /// Load mock data for demonstration
  void _loadMockData() {
    _isLoading = true;
    notifyListeners();

    // Simulate API delay
    Future.delayed(const Duration(milliseconds: 500), () {
      _teams = _createMockTeams();
      _isLoading = false;
      notifyListeners();
    });
  }

  /// Get inbox for a specific agent
  List<AgentMessage> getInbox(String agentName) {
    return _inboxes[agentName] ?? [];
  }

  /// Send a message to an agent
  Future<void> sendMessage({
    required String from,
    required String to,
    required String subject,
    required String content,
  }) async {
    final message = AgentMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      from: from,
      to: to,
      subject: subject,
      content: content,
      timestamp: DateTime.now(),
    );

    _inboxes.putIfAbsent(to, () => []);
    _inboxes[to]!.add(message);
    notifyListeners();
  }

  /// Create a task and assign to agent
  Future<void> createTask({
    required String title,
    required String description,
    required String assignee,
    TaskPriority priority = TaskPriority.medium,
    DateTime? deadline,
  }) async {
    final task = AgentTask(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      title: title,
      description: description,
      assignee: assignee,
      priority: priority,
      createdAt: DateTime.now(),
      deadline: deadline,
    );

    _tasks.add(task);
    notifyListeners();
  }

  /// Update task status
  void updateTaskStatus(String taskId, TaskStatus status) {
    final index = _tasks.indexWhere((t) => t.id == taskId);
    if (index != -1) {
      final task = _tasks[index];
      _tasks[index] = AgentTask(
        id: task.id,
        title: task.title,
        description: task.description,
        assignee: task.assignee,
        assignedBy: task.assignedBy,
        status: status,
        priority: task.priority,
        createdAt: task.createdAt,
        deadline: task.deadline,
        completedAt: status == TaskStatus.completed ? DateTime.now() : null,
      );
      notifyListeners();
    }
  }

  /// Refresh agent data
  Future<void> refresh() async {
    _loadMockData();
  }

  /// Create mock teams for demonstration
  List<AgentTeam> _createMockTeams() {
    return [
      // Pala-Jarvis Orchestrator (virtual team of 1)
      AgentTeam(
        name: 'orchestration',
        displayName: '🧠 Pala-Jarvis (Orchestrator)',
        description: 'Project manager coordinating all teams',
        lead: 'pala-jarvis',
        agents: [
          Agent(
            name: 'pala-jarvis',
            displayName: 'Pala-Jarvis',
            description: 'Project Manager — delegates, coordinates, escalates',
            status: AgentStatus.active,
            currentTask: 'Coordinating multi-model integration',
            skills: ['/delegate', '/escalate', '/coordinate'],
            defaultModel: 'claude-sonnet-4-20250514',
            hierarchyLevel: AgentHierarchy.orchestrator,
          ),
        ],
      ),
      AgentTeam(
        name: 'engineering',
        displayName: 'Engineering Team',
        description: 'Core development team for Flutter, Flask, and database work',
        lead: 'engineering-lead',
        agents: [
          Agent(
            name: 'engineering-lead',
            displayName: 'Engineering Lead',
            description: 'Architecture decisions, design documentation',
            status: AgentStatus.active,
            skills: ['/arch-review', '/design-doc'],
            defaultModel: 'claude-sonnet-4-20250514',
            hierarchyLevel: AgentHierarchy.teamLead,
            parentAgentName: 'pala-jarvis',
          ),
          Agent(
            name: 'flutter-web',
            displayName: 'Flutter Web Developer',
            description: 'Flutter web frontend development',
            status: AgentStatus.busy,
            currentTask: 'Creating Agent Dashboard',
            skills: ['/widget-create', '/state-manage'],
            defaultModel: 'gpt-4o',
            parentAgentName: 'engineering-lead',
          ),
          Agent(
            name: 'flask-api',
            displayName: 'Flask API Developer',
            description: 'REST API design and implementation',
            status: AgentStatus.idle,
            skills: ['/endpoint-create', '/middleware-add'],
            defaultModel: 'claude-sonnet-4-20250514',
            parentAgentName: 'engineering-lead',
          ),
          Agent(
            name: 'database-architect',
            displayName: 'Database Architect',
            description: 'SQLite + MongoDB schema design',
            status: AgentStatus.idle,
            skills: ['/schema-design', '/query-optimize'],
            defaultModel: 'ollama:llama3.2-vision:latest',
            parentAgentName: 'engineering-lead',
          ),
        ],
      ),
      AgentTeam(
        name: 'tipitaka-mastery',
        displayName: 'Tipitaka Mastery Team',
        description: 'Domain experts for Buddhist canonical texts',
        lead: 'tipitaka-lead',
        agents: [
          Agent(
            name: 'tipitaka-lead',
            displayName: 'Tipitaka Lead',
            description: 'Navigate Tipitaka structure, coordinate experts',
            status: AgentStatus.idle,
            skills: ['/canonical-navigate', '/teaching-plan'],
            defaultModel: 'claude-sonnet-4-20250514',
            hierarchyLevel: AgentHierarchy.teamLead,
            parentAgentName: 'pala-jarvis',
          ),
          Agent(
            name: 'sutta-pitaka-expert',
            displayName: 'Sutta Pitaka Expert',
            description: 'Expert on the 5 Nikayas',
            status: AgentStatus.idle,
            skills: ['/sutta-lookup', '/sutta-cross-ref'],
            defaultModel: 'claude-sonnet-4-20250514',
            parentAgentName: 'tipitaka-lead',
          ),
          Agent(
            name: 'vinaya-pitaka-expert',
            displayName: 'Vinaya Pitaka Expert',
            description: 'Expert on monastic discipline',
            status: AgentStatus.idle,
            skills: ['/vinaya-lookup', '/rule-explanation'],
            defaultModel: 'claude-sonnet-4-20250514',
            parentAgentName: 'tipitaka-lead',
          ),
          Agent(
            name: 'abhidhamma-expert',
            displayName: 'Abhidhamma Expert',
            description: 'Expert on the 7 Abhidhamma texts',
            status: AgentStatus.idle,
            skills: ['/abhidhamma-lookup', '/dhamma-analysis'],
            defaultModel: 'claude-sonnet-4-20250514',
            parentAgentName: 'tipitaka-lead',
          ),
          Agent(
            name: 'pali-linguist',
            displayName: 'Pali Linguist',
            description: 'Pali grammar, diacritics, transliteration',
            status: AgentStatus.idle,
            skills: ['/transliterate', '/parse-word'],
            defaultModel: 'claude-sonnet-4-20250514',
            parentAgentName: 'tipitaka-lead',
          ),
        ],
      ),
      AgentTeam(
        name: 'quality-assurance',
        displayName: 'Quality Assurance Team',
        description: 'Testing, code review, security',
        lead: 'qa-lead',
        agents: [
          Agent(
            name: 'qa-lead',
            displayName: 'QA Lead',
            description: 'QA planning, release readiness',
            status: AgentStatus.idle,
            skills: ['/qa-plan', '/release-check'],
            defaultModel: 'gpt-4o',
            hierarchyLevel: AgentHierarchy.teamLead,
            parentAgentName: 'pala-jarvis',
          ),
          Agent(
            name: 'code-reviewer',
            displayName: 'Code Reviewer',
            description: 'Code quality, best practices',
            status: AgentStatus.idle,
            skills: ['/review', '/lint-fix'],
            defaultModel: 'gpt-4o',
            parentAgentName: 'qa-lead',
          ),
          Agent(
            name: 'test-runner',
            displayName: 'Test Runner',
            description: 'Unit, integration, E2E testing',
            status: AgentStatus.idle,
            skills: ['/test', '/coverage'],
            defaultModel: 'gpt-4o',
            parentAgentName: 'qa-lead',
          ),
        ],
      ),
      AgentTeam(
        name: 'ai-ml',
        displayName: 'AI/ML Team',
        description: 'Claude integration, embeddings, RAG',
        lead: 'ai-lead',
        agents: [
          Agent(
            name: 'ai-lead',
            displayName: 'AI Lead',
            description: 'AI strategy, prompt engineering',
            status: AgentStatus.idle,
            skills: ['/ai-strategy', '/prompt-review'],
            defaultModel: 'claude-sonnet-4-20250514',
            hierarchyLevel: AgentHierarchy.teamLead,
            parentAgentName: 'pala-jarvis',
          ),
          Agent(
            name: 'claude-integrator',
            displayName: 'Claude Integrator',
            description: 'Claude API integration',
            status: AgentStatus.idle,
            skills: ['/claude-query', '/prompt-template'],
            defaultModel: 'claude-sonnet-4-20250514',
            parentAgentName: 'ai-lead',
          ),
          Agent(
            name: 'embeddings-trainer',
            displayName: 'Embeddings Trainer',
            description: 'Vector embeddings, semantic search',
            status: AgentStatus.idle,
            skills: ['/embed', '/similarity-search'],
            defaultModel: 'claude-sonnet-4-20250514',
            parentAgentName: 'ai-lead',
          ),
        ],
      ),
      AgentTeam(
        name: 'devops',
        displayName: 'DevOps Team',
        description: 'Docker, CI/CD, infrastructure',
        lead: 'devops-lead',
        agents: [
          Agent(
            name: 'devops-lead',
            displayName: 'DevOps Lead',
            description: 'Infrastructure planning',
            status: AgentStatus.idle,
            skills: ['/infra-plan', '/env-setup'],
            defaultModel: 'ollama:llama3.2-vision:latest',
            hierarchyLevel: AgentHierarchy.teamLead,
            parentAgentName: 'pala-jarvis',
          ),
          Agent(
            name: 'docker-builder',
            displayName: 'Docker Builder',
            description: 'Containerization, Docker Compose',
            status: AgentStatus.idle,
            skills: ['/dockerize', '/compose-up'],
            defaultModel: 'ollama:llama3.2-vision:latest',
            parentAgentName: 'devops-lead',
          ),
          Agent(
            name: 'ci-cd',
            displayName: 'CI/CD Engineer',
            description: 'GitHub Actions, deployment',
            status: AgentStatus.idle,
            skills: ['/pipeline-create', '/deploy-stage'],
            defaultModel: 'ollama:llama3.2-vision:latest',
            parentAgentName: 'devops-lead',
          ),
        ],
      ),
      AgentTeam(
        name: 'optimization',
        displayName: 'Optimization Team',
        description: 'Token efficiency, model selection, cost management',
        lead: 'optimization-lead',
        agents: [
          Agent(
            name: 'optimization-lead',
            displayName: 'Optimization Lead',
            description: 'Strategy for token/cost optimization',
            status: AgentStatus.active,
            skills: ['/optimize-strategy', '/cost-report'],
            defaultModel: 'claude-sonnet-4-20250514',
            hierarchyLevel: AgentHierarchy.teamLead,
            parentAgentName: 'pala-jarvis',
          ),
          Agent(
            name: 'token-optimizer',
            displayName: 'Token Optimizer',
            description: 'Minimize token usage, compress context',
            status: AgentStatus.idle,
            skills: ['/compress-context', '/prune-content'],
            defaultModel: 'claude-sonnet-4-20250514',
            parentAgentName: 'optimization-lead',
          ),
          Agent(
            name: 'model-selector',
            displayName: 'Model Selector',
            description: 'Auto-select best model for task',
            status: AgentStatus.idle,
            skills: ['/select-model', '/complexity-assess'],
            defaultModel: 'claude-sonnet-4-20250514',
            parentAgentName: 'optimization-lead',
          ),
          Agent(
            name: 'context-manager',
            displayName: 'Context Manager',
            description: 'Manage loaded context, prioritize files',
            status: AgentStatus.busy,
            currentTask: 'Setting up memory system',
            skills: ['/context-load', '/context-prune'],
            defaultModel: 'claude-sonnet-4-20250514',
            parentAgentName: 'optimization-lead',
          ),
          Agent(
            name: 'cost-tracker',
            displayName: 'Cost Tracker',
            description: 'Track token usage, report costs',
            status: AgentStatus.idle,
            skills: ['/track-usage', '/cost-report'],
            defaultModel: 'claude-sonnet-4-20250514',
            parentAgentName: 'optimization-lead',
          ),
        ],
      ),
    ];
  }
}
