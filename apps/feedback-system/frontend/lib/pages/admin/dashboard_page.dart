import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../services/api_service.dart';

class DashboardPage extends StatefulWidget {
  final String token;

  const DashboardPage({super.key, required this.token});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  Map<String, dynamic>? dashboardData;
  Map<String, dynamic>? feedbackListData;
  bool isLoading = true;
  String? errorMessage;
  String adminName = '';
  String adminRole = '';
  String? adminDepartment;
  String selectedPeriod = 'month'; // Default: month-wise
  String? selectedDepartment; // For super admin only

  @override
  void initState() {
    super.initState();
    _loadAdminInfo();
    _loadDashboardData();
  }

  Future<void> _loadAdminInfo() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      adminName = prefs.getString('admin_name') ?? 'Admin';
      adminRole = prefs.getString('admin_role') ?? 'admin';
      adminDepartment = prefs.getString('admin_department');
    });
  }

  Future<void> _loadDashboardData() async {
    setState(() => isLoading = true);
    
    try {
      final apiService = context.read<ApiService>();

      // Build query parameters for feedback list
      final queryParams = <String, String>{
        'limit': '100', // Get more entries
      };
      
      // Department filter
      if (adminRole == 'dept_admin') {
        // Dept admins see only their department
        if (adminDepartment != null) {
          queryParams['department_code'] = adminDepartment!;
        }
      } else if (adminRole == 'super_admin') {
        // Super admin can filter by department
        if (selectedDepartment != null && selectedDepartment!.isNotEmpty) {
          queryParams['department_code'] = selectedDepartment!;
        }
      }
      
      // Time period filter
      final now = DateTime.now();
      DateTime startDate;
      
      switch (selectedPeriod) {
        case 'week':
          startDate = now.subtract(const Duration(days: 7));
          break;
        case 'month':
          startDate = DateTime(now.year, now.month - 1, now.day);
          break;
        case 'year':
          startDate = DateTime(now.year - 1, now.month, now.day);
          break;
        default:
          startDate = now.subtract(const Duration(days: 30));
      }
      
      queryParams['start_date'] = startDate.toIso8601String();

      final dashboard = await apiService.getDashboard(widget.token);
      final feedbackList = await apiService.getFeedbackList(widget.token, queryParams: queryParams);

      setState(() {
        dashboardData = dashboard;
        feedbackListData = feedbackList;
        isLoading = false;
        errorMessage = null;
      });
    } catch (e) {
      setState(() {
        errorMessage = e.toString();
        isLoading = false;
      });
    }
  }

  Future<void> _handleLogout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();

    if (mounted) {
      context.go('/admin');
    }
  }

  void _viewFeedback(Map<String, dynamic> feedback) {
    showDialog(
      context: context,
      builder: (context) => FeedbackViewDialog(feedback: feedback),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Admin Dashboard'),
        actions: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      adminName,
                      style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                    ),
                    Text(
                      adminRole.toUpperCase(),
                      style: TextStyle(fontSize: 11, color: Colors.grey[600]),
                    ),
                  ],
                ),
                const SizedBox(width: 16),
                IconButton(
                  icon: const Icon(Icons.logout),
                  onPressed: _handleLogout,
                  tooltip: 'Logout',
                ),
              ],
            ),
          ),
        ],
      ),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : errorMessage != null
              ? _buildErrorView()
              : RefreshIndicator(
                  onRefresh: _loadDashboardData,
                  child: SingleChildScrollView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _buildOverviewSection(),
                        const SizedBox(height: 24),
                        _buildFiltersSection(),
                        const SizedBox(height: 24),
                        _buildFeedbackListSection(),
                      ],
                    ),
                  ),
                ),
    );
  }

  Widget _buildErrorView() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.error_outline, size: 64, color: Colors.red[300]),
          const SizedBox(height: 16),
          Text('Failed to load dashboard', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(errorMessage!, style: TextStyle(color: Colors.grey[600])),
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: () {
              setState(() {
                isLoading = true;
                errorMessage = null;
              });
              _loadDashboardData();
            },
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  Widget _buildOverviewSection() {
    if (dashboardData == null) return const SizedBox.shrink();
    final overall = dashboardData!['overall'];

    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Overview',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 16,
              runSpacing: 16,
              children: [
                _buildStatChip('Total Feedback', overall['total_feedback'].toString(), Icons.feedback, Colors.blue),
                _buildStatChip('Avg Rating', '${overall['avg_rating'].toStringAsFixed(1)}/10', Icons.star, Colors.amber),
                _buildStatChip('With Comments', overall['with_comments'].toString(), Icons.comment, Colors.green),
                _buildStatChip('Anonymous', overall['anonymous_count'].toString(), Icons.visibility_off, Colors.purple),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatChip(String label, String value, IconData icon, Color color) {
    return Chip(
      avatar: Icon(icon, color: color, size: 20),
      label: Text('$label: $value'),
      backgroundColor: color.withOpacity(0.1),
    );
  }

  Widget _buildFiltersSection() {
    final departments = dashboardData != null 
        ? (dashboardData!['by_department'] as List?) ?? []
        : [];

    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Filters',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 16),
            
            // Super admin department filter
            if (adminRole == 'super_admin') ...[
              const Text('Department:', style: TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                value: selectedDepartment,
                decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                ),
                hint: const Text('All Departments'),
                items: [
                  const DropdownMenuItem<String>(
                    value: null,
                    child: Text('All Departments'),
                  ),
                  ...departments.map((dept) => DropdownMenuItem<String>(
                    value: dept['department_code'],
                    child: Text(dept['department_name']),
                  )).toList(),
                ],
                onChanged: (value) {
                  setState(() {
                    selectedDepartment = value;
                  });
                  _loadDashboardData();
                },
              ),
              const SizedBox(height: 16),
            ],
            
            // Time period filter
            const Text('Time Period:', style: TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilterChip(
                  label: const Text('Week'),
                  selected: selectedPeriod == 'week',
                  onSelected: (selected) {
                    setState(() => selectedPeriod = 'week');
                    _loadDashboardData();
                  },
                ),
                FilterChip(
                  label: const Text('Month'),
                  selected: selectedPeriod == 'month',
                  onSelected: (selected) {
                    setState(() => selectedPeriod = 'month');
                    _loadDashboardData();
                  },
                ),
                FilterChip(
                  label: const Text('Year'),
                  selected: selectedPeriod == 'year',
                  onSelected: (selected) {
                    setState(() => selectedPeriod = 'year');
                    _loadDashboardData();
                  },
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFeedbackListSection() {
    if (feedbackListData == null) return const SizedBox.shrink();
    final feedbacks = (feedbackListData!['feedbacks'] as List?) ?? [];

    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Feedback Entries',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                Text(
                  '${feedbacks.length} entries',
                  style: TextStyle(color: Colors.grey[600]),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            if (feedbacks.isEmpty)
              const Padding(
                padding: EdgeInsets.all(32),
                child: Center(
                  child: Text('No feedback found for selected filters'),
                ),
              )
            else
              ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: feedbacks.length,
                separatorBuilder: (context, index) => const Divider(),
                itemBuilder: (context, index) {
                  final feedback = feedbacks[index];
                  final createdAt = DateTime.parse(feedback['created_at']);
                  
                  return ListTile(
                    leading: CircleAvatar(
                      backgroundColor: Colors.blue[100],
                      child: Text('${index + 1}'),
                    ),
                    title: Text(
                      feedback['is_anonymous'] 
                          ? 'Anonymous Feedback' 
                          : feedback['user_name'] ?? 'Unknown',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          feedback['department_code'].toString().toUpperCase(),
                          style: TextStyle(color: Colors.blue[700]),
                        ),
                        Text(
                          '${createdAt.day}/${createdAt.month}/${createdAt.year} ${createdAt.hour}:${createdAt.minute.toString().padLeft(2, '0')}',
                          style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                        ),
                      ],
                    ),
                    trailing: ElevatedButton.icon(
                      onPressed: () => _viewFeedback(feedback),
                      icon: const Icon(Icons.visibility, size: 16),
                      label: const Text('View'),
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      ),
                    ),
                  );
                },
              ),
          ],
        ),
      ),
    );
  }
}

class FeedbackViewDialog extends StatelessWidget {
  final Map<String, dynamic> feedback;

  const FeedbackViewDialog({super.key, required this.feedback});

  @override
  Widget build(BuildContext context) {
    final ratings = feedback['ratings'] as Map<String, dynamic>? ?? {};
    final createdAt = DateTime.parse(feedback['created_at']);
    
    return Dialog(
      child: Container(
        constraints: const BoxConstraints(maxWidth: 600),
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Feedback Details',
                      style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => Navigator.pop(context),
                    ),
                  ],
                ),
                const Divider(),
                const SizedBox(height: 16),
                
                // User Information
                _buildInfoRow('Name', feedback['is_anonymous'] ? 'Anonymous' : (feedback['user_name'] ?? 'N/A')),
                if (!feedback['is_anonymous'] && feedback['user_email'] != null)
                  _buildInfoRow('Email', feedback['user_email']),
                _buildInfoRow('Department', feedback['department_code'].toString().toUpperCase()),
                _buildInfoRow('Submitted', '${createdAt.day}/${createdAt.month}/${createdAt.year} ${createdAt.hour}:${createdAt.minute.toString().padLeft(2, '0')}'),
                _buildInfoRow('Access Mode', feedback['access_mode'] ?? 'web'),
                
                const SizedBox(height: 16),
                const Divider(),
                const SizedBox(height: 16),
                
                // Ratings
                Text(
                  'Ratings',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                const SizedBox(height: 12),
                
                ...ratings.entries.map((entry) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          _formatRatingKey(entry.key),
                          style: const TextStyle(fontWeight: FontWeight.w500),
                        ),
                      ),
                      Row(
                        children: [
                          ...List.generate(10, (i) => Icon(
                            i < entry.value ? Icons.star : Icons.star_border,
                            size: 16,
                            color: Colors.amber,
                          )),
                          const SizedBox(width: 8),
                          Text(
                            '${entry.value}/10',
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                    ],
                  ),
                )),
                
                const SizedBox(height: 16),
                const Divider(),
                const SizedBox(height: 16),
                
                // Comment
                if (feedback['comment'] != null && feedback['comment'].toString().isNotEmpty) ...[
                  Text(
                    'Comment',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.grey[100],
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.grey[300]!),
                    ),
                    child: Text(feedback['comment']),
                  ),
                ],
                
                const SizedBox(height: 24),
                Align(
                  alignment: Alignment.centerRight,
                  child: ElevatedButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('Close'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              '$label:',
              style: const TextStyle(
                fontWeight: FontWeight.w600,
                color: Colors.grey,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }

  String _formatRatingKey(String key) {
    return key
        .split('_')
        .map((word) => word[0].toUpperCase() + word.substring(1))
        .join(' ');
  }
}
