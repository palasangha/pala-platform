import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Provider for managing app settings
class SettingsProvider extends ChangeNotifier {
  ThemeMode _themeMode = ThemeMode.system;
  String _apiBaseUrl = 'http://localhost:5001';
  bool _showPaliText = true;
  bool _showReferences = true;

  ThemeMode get themeMode => _themeMode;
  String get apiBaseUrl => _apiBaseUrl;
  bool get showPaliText => _showPaliText;
  bool get showReferences => _showReferences;

  SettingsProvider() {
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();

    // Load theme mode
    final themeModeIndex = prefs.getInt('themeMode') ?? 0;
    _themeMode = ThemeMode.values[themeModeIndex];

    // Load API URL
    _apiBaseUrl = prefs.getString('apiBaseUrl') ?? 'http://localhost:5001';

    // Load display preferences
    _showPaliText = prefs.getBool('showPaliText') ?? true;
    _showReferences = prefs.getBool('showReferences') ?? true;

    notifyListeners();
  }

  Future<void> setThemeMode(ThemeMode mode) async {
    _themeMode = mode;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt('themeMode', mode.index);
    notifyListeners();
  }

  Future<void> setApiBaseUrl(String url) async {
    _apiBaseUrl = url;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('apiBaseUrl', url);
    notifyListeners();
  }

  Future<void> setShowPaliText(bool show) async {
    _showPaliText = show;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('showPaliText', show);
    notifyListeners();
  }

  Future<void> setShowReferences(bool show) async {
    _showReferences = show;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('showReferences', show);
    notifyListeners();
  }
}
