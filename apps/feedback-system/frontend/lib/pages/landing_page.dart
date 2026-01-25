import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../services/api_service.dart';

class LandingPage extends StatefulWidget {
  const LandingPage({super.key});

  @override
  State<LandingPage> createState() => _LandingPageState();
}

class _LandingPageState extends State<LandingPage> {
  List<Map<String, dynamic>> departments = [];
  bool isLoading = true;
  String? errorMessage;

  @override
  void initState() {
    super.initState();
    _loadDepartments();
  }

  Future<void> _loadDepartments() async {
    try {
      final apiService = context.read<ApiService>();
      final data = await apiService.getDepartments();
      setState(() {
        departments = data;
        isLoading = false;
      });
    } catch (e) {
      setState(() {
        errorMessage = e.toString();
        isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Theme.of(context).colorScheme.primary.withOpacity(0.1),
              Colors.white,
            ],
          ),
        ),
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final screenWidth = constraints.maxWidth;
              final screenHeight = constraints.maxHeight;

              // Determine grid columns based on width
              int crossAxisCount = 1;
              if (screenWidth > 1200) {
                crossAxisCount = 3;
              } else if (screenWidth > 800) {
                crossAxisCount = 2;
              }

              // Calculate header height (compact)
              final headerHeight = screenWidth > 600 ? 120.0 : 100.0;

              // Calculate available height for grid
              final gridHeight = screenHeight - headerHeight;

              // Calculate number of rows needed
              final itemCount = departments.length;
              final rowCount = (itemCount / crossAxisCount).ceil();

              // Calculate item height to fit perfectly
              final spacing = 12.0;
              final padding = 16.0;
              final availableGridHeight = gridHeight - (padding * 2);
              final totalSpacing = spacing * (rowCount - 1);
              final itemHeight = (availableGridHeight - totalSpacing) / rowCount;

              // Calculate aspect ratio
              final itemWidth = (screenWidth - (padding * 2) - (spacing * (crossAxisCount - 1))) / crossAxisCount;
              final childAspectRatio = itemWidth / itemHeight;

              return Column(
                children: [
                  // Compact Header
                  SizedBox(
                    height: headerHeight,
                    child: Padding(
                      padding: EdgeInsets.symmetric(
                        horizontal: screenWidth > 600 ? 24.0 : 16.0,
                        vertical: 8.0,
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            'Global Vipassana Pagoda',
                            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                                  fontWeight: FontWeight.bold,
                                  color: Theme.of(context).colorScheme.primary,
                                  fontSize: screenWidth > 600 ? 28 : 24,
                                ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'Feedback System',
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                  color: Colors.grey[700],
                                  fontSize: screenWidth > 600 ? 18 : 16,
                                ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'Please select your department',
                            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                  color: Colors.grey[600],
                                  fontSize: screenWidth > 600 ? 14 : 12,
                                ),
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    ),
                  ),

                  // Department Grid (fits perfectly)
                  Expanded(
                    child: isLoading
                        ? const Center(child: CircularProgressIndicator())
                        : errorMessage != null
                            ? Center(
                                child: Padding(
                                  padding: const EdgeInsets.all(24.0),
                                  child: Column(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      Icon(
                                        Icons.error_outline,
                                        size: 48,
                                        color: Colors.red[300],
                                      ),
                                      const SizedBox(height: 12),
                                      Text(
                                        'Failed to load departments',
                                        style: Theme.of(context).textTheme.titleMedium,
                                      ),
                                      const SizedBox(height: 8),
                                      Text(
                                        errorMessage!,
                                        style: TextStyle(color: Colors.grey[600], fontSize: 12),
                                        textAlign: TextAlign.center,
                                      ),
                                      const SizedBox(height: 16),
                                      ElevatedButton.icon(
                                        onPressed: () {
                                          setState(() {
                                            isLoading = true;
                                            errorMessage = null;
                                          });
                                          _loadDepartments();
                                        },
                                        icon: const Icon(Icons.refresh, size: 18),
                                        label: const Text('Retry'),
                                      ),
                                    ],
                                  ),
                                ),
                              )
                            : GridView.builder(
                                physics: const NeverScrollableScrollPhysics(),
                                padding: EdgeInsets.all(padding),
                                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                                  crossAxisCount: crossAxisCount,
                                  crossAxisSpacing: spacing,
                                  mainAxisSpacing: spacing,
                                  childAspectRatio: childAspectRatio.clamp(0.8, 2.5),
                                ),
                                itemCount: departments.length,
                                itemBuilder: (context, index) {
                                  final dept = departments[index];
                                  return _DepartmentCard(
                                    name: dept['name'],
                                    code: dept['code'],
                                    description: dept['description'] ?? '',
                                    isActive: dept['active'] ?? true,
                                    onTap: () {
                                      context.go('/feedback/${dept['code']}');
                                    },
                                    isCompact: screenWidth < 600 || screenHeight < 600,
                                  );
                                },
                              ),
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}

class _DepartmentCard extends StatelessWidget {
  final String name;
  final String code;
  final String description;
  final bool isActive;
  final VoidCallback onTap;
  final bool isCompact;

  const _DepartmentCard({
    required this.name,
    required this.code,
    required this.description,
    required this.isActive,
    required this.onTap,
    this.isCompact = false,
  });

  IconData _getIconForDepartment(String code) {
    switch (code) {
      case 'global_pagoda':
        return Icons.temple_buddhist;
      case 'shop':
      case 'souvenir_store':
        return Icons.store;
      case 'dpvc':
        return Icons.self_improvement;
      case 'dhamma_lane':
      case 'dhammalaya':
        return Icons.local_library;
      case 'food_court':
        return Icons.restaurant;
      default:
        return Icons.business;
    }
  }

  @override
  Widget build(BuildContext context) {
    final iconSize = isCompact ? 32.0 : 40.0;
    final padding = isCompact ? 12.0 : 16.0;

    return Card(
      elevation: isActive ? 4 : 2,
      child: InkWell(
        onTap: isActive ? onTap : null,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: EdgeInsets.all(padding),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            gradient: isActive
                ? LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      Theme.of(context).colorScheme.primaryContainer,
                      Theme.of(context).colorScheme.secondaryContainer,
                    ],
                  )
                : null,
            color: isActive ? null : Colors.grey[300],
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                _getIconForDepartment(code),
                size: iconSize,
                color: isActive
                    ? Theme.of(context).colorScheme.primary
                    : Colors.grey[500],
              ),
              SizedBox(height: isCompact ? 8 : 12),
              Flexible(
                child: Text(
                  name,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: isActive ? null : Colors.grey[600],
                        fontSize: isCompact ? 14 : 16,
                      ),
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (description.isNotEmpty && !isCompact) ...[
                const SizedBox(height: 4),
                Flexible(
                  child: Text(
                    description,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: isActive ? Colors.grey[700] : Colors.grey[500],
                          fontSize: 11,
                        ),
                    textAlign: TextAlign.center,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
              if (!isActive) ...[
                const SizedBox(height: 4),
                Chip(
                  label: Text(
                    'Inactive',
                    style: TextStyle(fontSize: isCompact ? 10 : 12),
                  ),
                  backgroundColor: Colors.grey[400],
                  padding: EdgeInsets.zero,
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
