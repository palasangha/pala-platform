import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../services/api_service.dart';

class DashboardPage extends StatefulWidget {
  final String token;

  const DashboardPage({super.key, required this.token});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  Map<String, dynamic>? dashboardData;
  Map<String, dynamic>? feedbackData;
  Map<String, dynamic>? reportsData;
  bool isLoading = true;
  String? errorMessage;
  String adminName = '';
  String adminRole = '';
  String selectedPeriod = 'all';
  String? selectedDepartment;

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
    });
  }

  Future<void> _loadDashboardData() async {
    try {
      final apiService = context.read<ApiService>();

      final dashboard = await apiService.getDashboard(widget.token);
      final feedback = await apiService.getFeedbackList(widget.token, limit: 10);
      
      // Build query parameters for reports
      final reportsQuery = <String, String>{
        'limit': '20',
      };
      
      if (selectedDepartment != null && selectedDepartment!.isNotEmpty) {
        reportsQuery['department_code'] = selectedDepartment!;
      }
      
      // Add date filters based on period
      if (selectedPeriod != 'all') {
        final now = DateTime.now();
        DateTime startDate;
        
        switch (selectedPeriod) {
          case 'today':
            startDate = DateTime(now.year, now.month, now.day);
            break;
          case 'week':
            startDate = now.subtract(const Duration(days: 7));
            break;
          case 'month':
            startDate = now.subtract(const Duration(days: 30));
            break;
          default:
            startDate = now.subtract(const Duration(days: 7));
        }
        
        reportsQuery['start_date'] = startDate.toIso8601String();
      }

      final reports = await apiService.getReports(widget.token, queryParams: reportsQuery);

      setState(() {
        dashboardData = dashboard;
        feedbackData = feedback;
        reportsData = reports;
        isLoading = false;
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

  Future<void> _downloadReport(String reportId, String departmentCode) async {
    try {
      // Construct the download URL with auth token
      final url = Uri.parse('/api/reports/$reportId/download?token=${widget.token}');
      
      if (await canLaunchUrl(url)) {
        await launchUrl(url, mode: LaunchMode.externalApplication);
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Opening report...'),
              backgroundColor: Colors.green,
              duration: Duration(seconds: 2),
            ),
          );
        }
      } else {
        throw 'Could not launch report download';
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to download report: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
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
              ? Center(
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
                )
              : RefreshIndicator(
                  onRefresh: _loadDashboardData,
                  child: SingleChildScrollView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(24),
                    child: LayoutBuilder(
                      builder: (context, constraints) {
                        final isWideScreen = constraints.maxWidth > 1200;

                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            // Overview Stats
                            _buildOverviewSection(isWideScreen),
                            const SizedBox(height: 24),

                            // Recent Feedback & Reports with Filters
                            if (isWideScreen)
                              Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Expanded(child: _buildRecentFeedbackSection()),
                                  const SizedBox(width: 24),
                                  Expanded(child: _buildReportsSection()),
                                ],
                              )
                            else ...[
                              _buildRecentFeedbackSection(),
                              const SizedBox(height: 24),
                              _buildReportsSection(),
                            ],
                          ],
                        );
                      },
                    ),
                  ),
                ),
    );
  }

  Widget _buildOverviewSection(bool isWideScreen) {
    if (dashboardData == null) return const SizedBox.shrink();
    final overall = dashboardData!['overall'];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Overview',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 16),
        isWideScreen
            ? Row(
                children: [
                  Expanded(child: _buildStatCard('Total Feedback', overall['total_feedback'].toString(), Icons.feedback, Colors.blue)),
                  const SizedBox(width: 16),
                  Expanded(child: _buildStatCard('Avg Rating', '${overall['avg_rating'].toStringAsFixed(2)} / 10', Icons.star, Colors.amber)),
                  const SizedBox(width: 16),
                  Expanded(child: _buildStatCard('With Comments', overall['with_comments'].toString(), Icons.comment, Colors.green)),
                  const SizedBox(width: 16),
                  Expanded(child: _buildStatCard('Anonymous', overall['anonymous_count'].toString(), Icons.visibility_off, Colors.purple)),
                ],
              )
            : Column(
                children: [
                  Row(
                    children: [
                      Expanded(child: _buildStatCard('Total Feedback', overall['total_feedback'].toString(), Icons.feedback, Colors.blue)),
                      const SizedBox(width: 16),
                      Expanded(child: _buildStatCard('Avg Rating', '${overall['avg_rating'].toStringAsFixed(2)} / 10', Icons.star, Colors.amber)),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(child: _buildStatCard('With Comments', overall['with_comments'].toString(), Icons.comment, Colors.green)),
                      const SizedBox(width: 16),
                      Expanded(child: _buildStatCard('Anonymous', overall['anonymous_count'].toString(), Icons.visibility_off, Colors.purple)),
                    ],
                  ),
                ],
              ),
      ],
    );
  }

  Widget _buildStatCard(String title, String value, IconData icon, Color color) {
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
                Icon(icon, color: color, size: 32),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    value,
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: color,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              title,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: Colors.grey[600],
                  ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRecentFeedbackSection() {
    if (feedbackData == null) return const SizedBox.shrink();
    final feedbacks = (feedbackData!['feedbacks'] as List?) ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Recent Feedback',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 16),
        Card(
          child: feedbacks.isEmpty
              ? const Padding(
                  padding: EdgeInsets.all(32),
                  child: Center(
                    child: Text('No feedback yet'),
                  ),
                )
              : ListView.separated(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: feedbacks.length > 5 ? 5 : feedbacks.length,
                  separatorBuilder: (context, index) => const Divider(),
                  itemBuilder: (context, index) {
                    final feedback = feedbacks[index];
                    final createdAt = DateTime.parse(feedback['created_at']);

                    return ListTile(
                      leading: CircleAvatar(
                        child: Text((index + 1).toString()),
                      ),
                      title: Text(
                        feedback['is_anonymous'] ? 'Anonymous' : feedback['user_name'] ?? 'Unknown',
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                      subtitle: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(feedback['department_code']),
                          Text(
                            '${createdAt.day}/${createdAt.month}/${createdAt.year} ${createdAt.hour}:${createdAt.minute.toString().padLeft(2, '0')}',
                            style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                          ),
                        ],
                      ),
                      trailing: feedback['comment'] != null
                          ? const Icon(Icons.comment, color: Colors.green)
                          : null,
                    );
                  },
                ),
        ),
      ],
    );
  }

  Widget _buildReportsSection() {
    if (reportsData == null) return const SizedBox.shrink();
    final reports = (reportsData!['reports'] as List?) ?? [];
    final departments = dashboardData != null 
        ? (dashboardData!['by_department'] as List?) ?? []
        : [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Generated Reports',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            IconButton(
              icon: const Icon(Icons.filter_list),
              onPressed: () => _showFiltersDialog(),
              tooltip: 'Filter Reports',
            ),
          ],
        ),
        const SizedBox(height: 8),
        
        // Filter Chips
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            FilterChip(
              label: const Text('All'),
              selected: selectedPeriod == 'all',
              onSelected: (selected) {
                setState(() {
                  selectedPeriod = 'all';
                  isLoading = true;
                });
                _loadDashboardData();
              },
            ),
            FilterChip(
              label: const Text('Today'),
              selected: selectedPeriod == 'today',
              onSelected: (selected) {
                setState(() {
                  selectedPeriod = 'today';
                  isLoading = true;
                });
                _loadDashboardData();
              },
            ),
            FilterChip(
              label: const Text('This Week'),
              selected: selectedPeriod == 'week',
              onSelected: (selected) {
                setState(() {
                  selectedPeriod = 'week';
                  isLoading = true;
                });
                _loadDashboardData();
              },
            ),
            FilterChip(
              label: const Text('This Month'),
              selected: selectedPeriod == 'month',
              onSelected: (selected) {
                setState(() {
                  selectedPeriod = 'month';
                  isLoading = true;
                });
                _loadDashboardData();
              },
            ),
          ],
        ),
        const SizedBox(height: 16),
        
        Card(
          child: reports.isEmpty
              ? const Padding(
                  padding: EdgeInsets.all(32),
                  child: Center(
                    child: Text('No reports found for selected filters'),
                  ),
                )
              : ListView.separated(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: reports.length,
                  separatorBuilder: (context, index) => const Divider(),
                  itemBuilder: (context, index) {
                    final report = reports[index];
                    final generatedAt = DateTime.parse(report['generated_at']);
                    final stats = report['summary_stats'];

                    return ListTile(
                      leading: const Icon(Icons.picture_as_pdf, color: Colors.red),
                      title: Text(
                        report['department_code'].toString().toUpperCase(),
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                      subtitle: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${stats['total_feedback']} feedback • ${stats['avg_rating'].toStringAsFixed(1)} avg'),
                          Text(
                            '${generatedAt.day}/${generatedAt.month}/${generatedAt.year} ${generatedAt.hour}:${generatedAt.minute.toString().padLeft(2, '0')}',
                            style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                          ),
                        ],
                      ),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            icon: const Icon(Icons.download, color: Colors.blue),
                            onPressed: () => _downloadReport(report['_id'], report['department_code']),
                            tooltip: 'Download PDF',
                          ),
                          Icon(
                            report['email_status']['sent'] ? Icons.check_circle : Icons.pending,
                            color: report['email_status']['sent'] ? Colors.green : Colors.orange,
                          ),
                        ],
                      ),
                      onTap: () => _downloadReport(report['_id'], report['department_code']),
                    );
                  },
                ),
        ),
      ],
    );
  }

  void _showFiltersDialog() {
    final departments = dashboardData != null 
        ? (dashboardData!['by_department'] as List?) ?? []
        : [];
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Filter Reports'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Department:', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            DropdownButton<String>(
              value: selectedDepartment,
              isExpanded: true,
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
                Navigator.pop(context);
                setState(() {
                  selectedDepartment = value;
                  isLoading = true;
                });
                _loadDashboardData();
              },
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }
}
