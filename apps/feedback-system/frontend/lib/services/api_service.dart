import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  // Use environment variable or default to relative URL (goes through nginx proxy)
  static const String baseUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: '/api',
  );

  // Get all departments
  Future<List<Map<String, dynamic>>> getDepartments() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/departments'));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return List<Map<String, dynamic>>.from(data['data']['departments']);
      } else {
        throw Exception('Failed to load departments');
      }
    } catch (e) {
      throw Exception('Error fetching departments: $e');
    }
  }

  // Get department with questions
  Future<Map<String, dynamic>> getDepartmentDetails(String code) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/departments/$code'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['data']; // Return both department and questions
      } else {
        throw Exception('Failed to load department details');
      }
    } catch (e) {
      throw Exception('Error fetching department details: $e');
    }
  }

  // Submit feedback
  Future<Map<String, dynamic>> submitFeedback(Map<String, dynamic> feedbackData) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/feedback'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(feedbackData),
      );

      final data = json.decode(response.body);

      if (response.statusCode == 201) {
        return data['data'];
      } else {
        throw Exception(data['message'] ?? 'Failed to submit feedback');
      }
    } catch (e) {
      throw Exception('Error submitting feedback: $e');
    }
  }

  // Admin login
  Future<Map<String, dynamic>> login(String email, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'email': email, 'password': password}),
      );

      final data = json.decode(response.body);

      if (response.statusCode == 200) {
        return data['data'];
      } else {
        throw Exception(data['message'] ?? 'Login failed');
      }
    } catch (e) {
      throw Exception('Error during login: $e');
    }
  }

  // Get dashboard data
  Future<Map<String, dynamic>> getDashboard(String token) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/admin/dashboard'),
        headers: {'Authorization': 'Bearer $token'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['data'];
      } else {
        throw Exception('Failed to load dashboard');
      }
    } catch (e) {
      throw Exception('Error fetching dashboard: $e');
    }
  }

  // Get feedback list
  Future<Map<String, dynamic>> getFeedbackList(String token, {int page = 1, int limit = 20, Map<String, String>? queryParams}) async {
    try {
      final params = {
        'page': page.toString(),
        'limit': limit.toString(),
        ...?queryParams,
      };
      
      final uri = Uri.parse('$baseUrl/feedback').replace(queryParameters: params);
      
      final response = await http.get(
        uri,
        headers: {'Authorization': 'Bearer $token'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['data'];
      } else {
        throw Exception('Failed to load feedback');
      }
    } catch (e) {
      throw Exception('Error fetching feedback: $e');
    }
  }

  // Get reports list
  Future<Map<String, dynamic>> getReports(String token, {int page = 1, int limit = 10, Map<String, String>? queryParams}) async {
    try {
      final params = {
        'page': page.toString(),
        'limit': limit.toString(),
        ...?queryParams,
      };
      
      final uri = Uri.parse('$baseUrl/reports').replace(queryParameters: params);
      
      final response = await http.get(
        uri,
        headers: {'Authorization': 'Bearer $token'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['data'];
      } else {
        throw Exception('Failed to load reports');
      }
    } catch (e) {
      throw Exception('Error fetching reports: $e');
    }
  }

  // Trigger manual report
  Future<Map<String, dynamic>> triggerReport(String token, String departmentCode) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/reports/trigger'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
        body: json.encode({'department_code': departmentCode}),
      );

      final data = json.decode(response.body);

      if (response.statusCode == 201) {
        return data['data'];
      } else {
        throw Exception(data['message'] ?? 'Failed to trigger report');
      }
    } catch (e) {
      throw Exception('Error triggering report: $e');
    }
  }
}
