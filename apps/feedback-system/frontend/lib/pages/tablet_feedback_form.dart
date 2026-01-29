import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../widgets/tablet_widgets.dart';
import '../widgets/tablet_rating_widgets.dart';

class TabletFeedbackForm extends StatefulWidget {
  final String departmentCode;
  final Map<String, dynamic> departmentData;

  const TabletFeedbackForm({
    super.key,
    required this.departmentCode,
    required this.departmentData,
  });

  @override
  State<TabletFeedbackForm> createState() => _TabletFeedbackFormState();
}

class _TabletFeedbackFormState extends State<TabletFeedbackForm> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _commentController = TextEditingController();
  
  bool isAnonymous = false;
  bool isSubmitting = false;
  Map<String, int> ratings = {};
  
  List<Map<String, dynamic>> get questions {
    return (widget.departmentData['questions'] as List<dynamic>?)
        ?.cast<Map<String, dynamic>>() ?? [];
  }

  String get welcomeMessage {
    return widget.departmentData['tablet_config']?['welcome_message'] ?? 
           'We value your feedback!';
  }

  Color get primaryColor {
    final colorHex = widget.departmentData['tablet_config']?['primary_color'] as String?;
    if (colorHex != null && colorHex.startsWith('#')) {
      return Color(int.parse(colorHex.substring(1), radix: 16) + 0xFF000000);
    }
    return const Color(0xFF3498DB);
  }

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _commentController.dispose();
    super.dispose();
  }

  Future<void> _submitFeedback() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    // Check if all questions are answered
    final unansweredQuestions = questions
        .where((q) => 
          q['required'] == true && 
          (!ratings.containsKey(q['key']) || ratings[q['key']] == null || ratings[q['key']] == 0 || ratings[q['key']]! < 1))
        .toList();

    if (unansweredQuestions.isNotEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please answer all required questions'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    setState(() => isSubmitting = true);

    try {
      final apiService = context.read<ApiService>();
      
      await apiService.submitFeedback({
        'department_code': widget.departmentCode,
        'user_name': isAnonymous ? 'Anonymous' : _nameController.text.trim(),
        'user_email': isAnonymous ? 'anonymous@feedback.local' : _emailController.text.trim(),
        'is_anonymous': isAnonymous,
        'access_mode': 'tablet',
        'ratings': ratings,
        'comment': _commentController.text.trim().isEmpty 
            ? null 
            : _commentController.text.trim(),
      });

      if (mounted) {
        _showSuccessDialog();
      }
    } catch (e) {
      setState(() => isSubmitting = false);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: ${e.toString().replaceAll('Exception: ', '')}'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 4),
          ),
        );
      }
    }
  }

  void _showSuccessDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        child: Padding(
          padding: const EdgeInsets.all(40),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 100,
                height: 100,
                decoration: BoxDecoration(
                  color: Colors.green.withOpacity(0.1),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.check_circle,
                  color: Colors.green,
                  size: 60,
                ),
              ),
              const SizedBox(height: 24),
              const Text(
                'Thank You!',
                style: TextStyle(
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'Your feedback has been submitted successfully.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 18,
                  color: Colors.grey[600],
                ),
              ),
              const SizedBox(height: 32),
              TabletButton(
                label: 'Submit Another',
                icon: Icons.replay,
                onPressed: () {
                  Navigator.pop(context);
                  _resetForm();
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _resetForm() {
    setState(() {
      _nameController.clear();
      _emailController.clear();
      _commentController.clear();
      isAnonymous = false;
      isSubmitting = false;
      ratings.clear();
    });
    _formKey.currentState?.reset();
  }

  Widget _buildQuestionWidget(Map<String, dynamic> question) {
    final type = question['type'] as String;
    final key = question['key'] as String;
    final label = question['label'] as String;
    final icon = question['icon'] as String?;

    switch (type) {
      case 'rating_10':
        return Padding(
          padding: const EdgeInsets.only(bottom: 32),
          child: TabletRatingBar(
            label: label,
            icon: icon,
            initialRating: ratings[key],
            maxRating: 5,
            activeColor: primaryColor,
            onRatingSelected: (rating) {
              setState(() {
                ratings[key] = rating;
              });
            },
          ),
        );

      case 'smiley_5':
        return Padding(
          padding: const EdgeInsets.only(bottom: 32),
          child: TabletSmileyPicker(
            label: label,
            icon: icon,
            initialValue: ratings[key],
            activeColor: primaryColor,
            onSelected: (value) {
              setState(() {
                ratings[key] = value;
              });
            },
          ),
        );

      case 'binary_yes_no':
        return Padding(
          padding: const EdgeInsets.only(bottom: 32),
          child: TabletBinaryChoice(
            label: label,
            icon: icon,
            initialValue: ratings[key] != null ? ratings[key] == 1 : null,
            onSelected: (value) {
              setState(() {
                ratings[key] = value ? 1 : 0;
              });
            },
          ),
        );

      default:
        return const SizedBox.shrink();
    }
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isLandscape = MediaQuery.of(context).orientation == Orientation.landscape;

    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        backgroundColor: primaryColor,
        foregroundColor: Colors.white,
        elevation: 0,
        toolbarHeight: 80,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              widget.departmentData['name'] ?? '',
              style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            Text(
              welcomeMessage,
              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w400),
            ),
          ],
        ),
        actions: [
          if (ratings.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(right: 16),
              child: Center(
                child: Chip(
                  backgroundColor: Colors.white,
                  label: Text(
                    '${ratings.length}/${questions.length} answered',
                    style: TextStyle(
                      color: primaryColor,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
      body: Form(
        key: _formKey,
        child: SingleChildScrollView(
          padding: EdgeInsets.all(isLandscape ? 40 : 24),
          child: Center(
            child: ConstrainedBox(
              constraints: BoxConstraints(
                maxWidth: isLandscape ? 1200 : 800,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Anonymous toggle
                  TabletSwitch(
                    label: 'Submit Anonymously',
                    subtitle: 'Your name and email will not be recorded',
                    value: isAnonymous,
                    onChanged: (value) {
                      setState(() => isAnonymous = value);
                    },
                  ),
                  
                  const SizedBox(height: 24),

                  // User information (if not anonymous)
                  if (!isAnonymous) ...[
                    Card(
                      elevation: 2,
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Your Information',
                              style: TextStyle(
                                fontSize: 20,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 20),
                            TabletTextField(
                              label: 'Name',
                              hintText: 'Enter your name',
                              controller: _nameController,
                              prefixIcon: const Icon(Icons.person),
                              validator: (value) {
                                if (!isAnonymous && (value == null || value.trim().isEmpty)) {
                                  return 'Please enter your name or submit anonymously';
                                }
                                return null;
                              },
                            ),
                            const SizedBox(height: 20),
                            TabletTextField(
                              label: 'Email',
                              hintText: 'Enter your email',
                              controller: _emailController,
                              keyboardType: TextInputType.emailAddress,
                              prefixIcon: const Icon(Icons.email),
                              validator: (value) {
                                if (!isAnonymous && value != null && value.isNotEmpty) {
                                  if (!value.contains('@')) {
                                    return 'Please enter a valid email';
                                  }
                                }
                                return null;
                              },
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),
                  ],

                  // Questions
                  Card(
                    elevation: 2,
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Your Feedback',
                            style: TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 24),
                          ...questions.map((q) => _buildQuestionWidget(q)).toList(),
                        ],
                      ),
                    ),
                  ),

                  const SizedBox(height: 24),

                  // Comments
                  Card(
                    elevation: 2,
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: TabletTextField(
                        label: 'Additional Comments (Optional)',
                        hintText: 'Share your thoughts...',
                        controller: _commentController,
                        maxLines: 5,
                        maxLength: 500,
                      ),
                    ),
                  ),

                  const SizedBox(height: 32),

                  // Submit button
                  TabletButton(
                    label: isSubmitting ? 'Submitting...' : 'Submit Feedback',
                    icon: isSubmitting ? null : Icons.send,
                    onPressed: isSubmitting ? null : _submitFeedback,
                    backgroundColor: primaryColor,
                    isFullWidth: true,
                  ),

                  const SizedBox(height: 20),

                  // Reset button
                  TabletOutlinedButton(
                    label: 'Clear Form',
                    icon: Icons.refresh,
                    onPressed: isSubmitting ? null : _resetForm,
                    borderColor: Colors.grey[400],
                    textColor: Colors.grey[700],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
