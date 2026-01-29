import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_rating_bar/flutter_rating_bar.dart';
import '../services/api_service.dart';

class FeedbackFormPage extends StatefulWidget {
  final String departmentCode;

  const FeedbackFormPage({super.key, required this.departmentCode});

  @override
  State<FeedbackFormPage> createState() => _FeedbackFormPageState();
}

class _FeedbackFormPageState extends State<FeedbackFormPage> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _commentController = TextEditingController();

  Map<String, dynamic>? departmentData;
  Map<String, double> ratings = {};
  bool isAnonymous = false;
  bool isLoading = true;
  bool isSubmitting = false;
  String? errorMessage;

  @override
  void initState() {
    super.initState();
    _loadDepartmentDetails();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _commentController.dispose();
    super.dispose();
  }

  Future<void> _loadDepartmentDetails() async {
    try {
      final apiService = context.read<ApiService>();
      final data = await apiService.getDepartmentDetails(widget.departmentCode);
      setState(() {
        departmentData = data['department'];
        // Initialize ratings map
        final questions = data['department']['questions'] as List;
        for (var q in questions) {
          ratings[q['key']] = 0.0;
        }
        isLoading = false;
      });
    } catch (e) {
      setState(() {
        errorMessage = e.toString();
        isLoading = false;
      });
    }
  }

  Future<void> _submitFeedback() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    // Validate all ratings are filled
    final questions = departmentData!['questions'] as List;
    for (var q in questions) {
      final rating = ratings[q['key']];
      if (q['required'] == true && (rating == null || rating == 0.0 || rating < 1)) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Please answer: ${q['label']}'),
            backgroundColor: Colors.orange,
          ),
        );
        return;
      }
    }

    setState(() => isSubmitting = true);

    try {
      final apiService = context.read<ApiService>();

      // Convert ratings to integers
      final ratingsMap = ratings.map((key, value) => MapEntry(key, value.toInt()));

      final feedbackData = {
        'department_code': widget.departmentCode,
        'user_name': isAnonymous ? 'Anonymous' : _nameController.text.trim(),
        'user_email': isAnonymous ? 'anonymous@feedback.local' : _emailController.text.trim(),
        'is_anonymous': isAnonymous,
        'access_mode': 'web',
        'ratings': ratingsMap,
        'comment': _commentController.text.trim(),
      };

      await apiService.submitFeedback(feedbackData);

      if (mounted) {
        context.go('/thank-you');
      }
    } catch (e) {
      setState(() => isSubmitting = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to submit feedback: $e'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 5),
          ),
        );
      }
    }
  }

  Widget _buildRatingWidget(Map<String, dynamic> question) {
    final type = question['type'];
    final questionId = question['key'];
    final currentRating = ratings[questionId] ?? 0.0;

    if (type == 'rating_10' || type == 'numeric') {
      // Changed from slider to number buttons (1-5)
      return Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: List.generate(5, (index) {
              final rating = index + 1;
              final isSelected = currentRating.toInt() == rating;
              return Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 4.0),
                  child: Material(
                    color: isSelected
                        ? Theme.of(context).colorScheme.primary
                        : Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    elevation: isSelected ? 4 : 1,
                    child: InkWell(
                      onTap: () {
                        setState(() {
                          ratings[questionId] = rating.toDouble();
                        });
                      },
                      borderRadius: BorderRadius.circular(12),
                      child: Container(
                        height: 60,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: isSelected
                                ? Theme.of(context).colorScheme.primary
                                : Colors.grey[300]!,
                            width: isSelected ? 3 : 2,
                          ),
                        ),
                        child: Center(
                          child: Text(
                            '$rating',
                            style: TextStyle(
                              fontSize: 24,
                              fontWeight: FontWeight.bold,
                              color: isSelected
                                  ? Colors.white
                                  : Colors.grey[700],
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              );
            }),
          ),
          const SizedBox(height: 8),
          if (currentRating > 0)
            Text(
              'Rating: ${currentRating.toInt()}/5',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).colorScheme.primary,
                    fontWeight: FontWeight.w600,
                  ),
            ),
        ],
      );
    } else if (type == 'smiley_5' || type == 'emoji') {
      return Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: List.generate(5, (index) {
          final rating = index + 1;
          final isSelected = currentRating.toInt() == rating;
          return InkWell(
            onTap: () {
              setState(() {
                ratings[questionId] = rating.toDouble();
              });
            },
            child: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: isSelected ? Theme.of(context).colorScheme.primaryContainer : null,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: isSelected
                      ? Theme.of(context).colorScheme.primary
                      : Colors.grey[300]!,
                  width: 2,
                ),
              ),
              child: Text(
                _getEmojiForRating(rating),
                style: const TextStyle(fontSize: 32),
              ),
            ),
          );
        }),
      );
    } else if (type == 'star') {
      return RatingBar.builder(
        initialRating: currentRating,
        minRating: 0,
        direction: Axis.horizontal,
        allowHalfRating: false,
        itemCount: 5,
        itemPadding: const EdgeInsets.symmetric(horizontal: 4.0),
        itemBuilder: (context, _) => const Icon(
          Icons.star,
          color: Colors.amber,
        ),
        onRatingUpdate: (rating) {
          setState(() {
            ratings[questionId] = rating;
          });
        },
      );
    }

    return const SizedBox();
  }

  String _getEmojiForRating(int rating) {
    switch (rating) {
      case 1:
        return '😞';
      case 2:
        return '😕';
      case 3:
        return '😐';
      case 4:
        return '🙂';
      case 5:
        return '😄';
      default:
        return '😐';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(departmentData?['name'] ?? 'Feedback Form'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/'),
        ),
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
                      Text('Failed to load form', style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: 8),
                      Text(errorMessage!, style: TextStyle(color: Colors.grey[600])),
                      const SizedBox(height: 24),
                      ElevatedButton(
                        onPressed: () => context.go('/'),
                        child: const Text('Go Back'),
                      ),
                    ],
                  ),
                )
              : SingleChildScrollView(
                  child: Center(
                    child: Container(
                      constraints: const BoxConstraints(maxWidth: 800),
                      padding: const EdgeInsets.all(24),
                      child: Form(
                        key: _formKey,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            // Header
                            Card(
                              child: Padding(
                                padding: const EdgeInsets.all(24),
                                child: Column(
                                  children: [
                                    Text(
                                      'Share Your Experience',
                                      style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                                            fontWeight: FontWeight.bold,
                                          ),
                                    ),
                                    const SizedBox(height: 8),
                                    Text(
                                      'Your feedback helps us improve our services',
                                      style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                                            color: Colors.grey[600],
                                          ),
                                      textAlign: TextAlign.center,
                                    ),
                                  ],
                                ),
                              ),
                            ),
                            const SizedBox(height: 24),

                            // Anonymous Toggle
                            Card(
                              child: SwitchListTile(
                                title: const Text('Submit Anonymously'),
                                subtitle: const Text('Your name and email will not be recorded'),
                                value: isAnonymous,
                                onChanged: (value) {
                                  setState(() => isAnonymous = value);
                                },
                              ),
                            ),
                            const SizedBox(height: 16),

                            // User Info (if not anonymous)
                            if (!isAnonymous) ...[
                              Card(
                                child: Padding(
                                  padding: const EdgeInsets.all(16),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        'Your Information',
                                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                              fontWeight: FontWeight.bold,
                                            ),
                                      ),
                                      const SizedBox(height: 16),
                                      TextFormField(
                                        controller: _nameController,
                                        decoration: const InputDecoration(
                                          labelText: 'Full Name *',
                                          border: OutlineInputBorder(),
                                          prefixIcon: Icon(Icons.person),
                                        ),
                                        validator: (value) {
                                          if (!isAnonymous && (value == null || value.trim().isEmpty)) {
                                            return 'Please enter your name';
                                          }
                                          return null;
                                        },
                                      ),
                                      const SizedBox(height: 16),
                                      TextFormField(
                                        controller: _emailController,
                                        decoration: const InputDecoration(
                                          labelText: 'Email Address *',
                                          border: OutlineInputBorder(),
                                          prefixIcon: Icon(Icons.email),
                                        ),
                                        keyboardType: TextInputType.emailAddress,
                                        validator: (value) {
                                          if (!isAnonymous && (value == null || value.trim().isEmpty)) {
                                            return 'Please enter your email';
                                          }
                                          if (!isAnonymous && value != null && !value.contains('@')) {
                                            return 'Please enter a valid email';
                                          }
                                          return null;
                                        },
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                              const SizedBox(height: 16),
                            ],

                            // Questions
                            ...((departmentData!['questions'] as List).map((question) {
                              return Card(
                                child: Padding(
                                  padding: const EdgeInsets.all(16),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        children: [
                                          Expanded(
                                            child: Text(
                                              question['label'],
                                              style: Theme.of(context).textTheme.titleMedium,
                                            ),
                                          ),
                                          if (question['required'] == true)
                                            const Text(
                                              '*',
                                              style: TextStyle(color: Colors.red, fontSize: 20),
                                            ),
                                        ],
                                      ),
                                      const SizedBox(height: 16),
                                      _buildRatingWidget(question),
                                    ],
                                  ),
                                ),
                              );
                            }).toList()),
                            const SizedBox(height: 16),

                            // Comment
                            Card(
                              child: Padding(
                                padding: const EdgeInsets.all(16),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      'Additional Comments',
                                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                            fontWeight: FontWeight.bold,
                                          ),
                                    ),
                                    const SizedBox(height: 8),
                                    Text(
                                      'Please share any additional feedback or suggestions (optional)',
                                      style: TextStyle(color: Colors.grey[600]),
                                    ),
                                    const SizedBox(height: 16),
                                    TextFormField(
                                      controller: _commentController,
                                      decoration: const InputDecoration(
                                        hintText: 'Your comments here...',
                                        border: OutlineInputBorder(),
                                      ),
                                      maxLines: 5,
                                      maxLength: 2000,
                                    ),
                                  ],
                                ),
                              ),
                            ),
                            const SizedBox(height: 24),

                            // Submit Button
                            ElevatedButton(
                              onPressed: isSubmitting ? null : _submitFeedback,
                              style: ElevatedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(vertical: 20),
                                backgroundColor: Theme.of(context).colorScheme.primary,
                                foregroundColor: Colors.white,
                              ),
                              child: isSubmitting
                                  ? const SizedBox(
                                      height: 20,
                                      width: 20,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                                      ),
                                    )
                                  : const Text(
                                      'Submit Feedback',
                                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                                    ),
                            ),
                            const SizedBox(height: 24),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
    );
  }
}
