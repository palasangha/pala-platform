import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flex_color_scheme/flex_color_scheme.dart';

import 'screens/chat_screen.dart';
import 'screens/dashboard/agent_dashboard.dart';
import 'providers/chat_provider.dart';
import 'providers/settings_provider.dart';
import 'providers/agent_provider.dart';
import 'providers/model_provider.dart';
import 'providers/execution_provider.dart';
import 'providers/collaboration_provider.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const SammaAIApp());
}

class SammaAIApp extends StatelessWidget {
  const SammaAIApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ChatProvider()),
        ChangeNotifierProvider(create: (_) => SettingsProvider()),
        ChangeNotifierProvider(create: (_) => AgentProvider()),
        ChangeNotifierProvider(create: (_) => ModelProvider()),
        ChangeNotifierProvider(create: (_) => ExecutionProvider()),
        ChangeNotifierProvider(create: (_) => CollaborationProvider()),
      ],
      child: Consumer<SettingsProvider>(
        builder: (context, settings, _) {
          return MaterialApp(
            title: 'Samma AI',
            debugShowCheckedModeBanner: false,

            // Brown + Gold theme as specified in SOUL.md
            theme: FlexThemeData.light(
              scheme: FlexScheme.gold,
              surfaceMode: FlexSurfaceMode.levelSurfacesLowScaffold,
              blendLevel: 7,
              subThemesData: const FlexSubThemesData(
                blendOnLevel: 10,
                blendOnColors: false,
                useTextTheme: true,
                useM2StyleDividerInM3: true,
              ),
              visualDensity: FlexColorScheme.comfortablePlatformDensity,
              useMaterial3: true,
            ),
            darkTheme: FlexThemeData.dark(
              scheme: FlexScheme.gold,
              surfaceMode: FlexSurfaceMode.levelSurfacesLowScaffold,
              blendLevel: 13,
              subThemesData: const FlexSubThemesData(
                blendOnLevel: 20,
                useTextTheme: true,
                useM2StyleDividerInM3: true,
              ),
              visualDensity: FlexColorScheme.comfortablePlatformDensity,
              useMaterial3: true,
            ),
            themeMode: settings.themeMode,

            // Named routes for navigation
            initialRoute: '/',
            routes: {
              '/': (context) => const MainNavigationShell(),
              '/chat': (context) => const ChatScreen(),
              '/dashboard': (context) => const AgentDashboard(),
            },
          );
        },
      ),
    );
  }
}

/// Main navigation shell with bottom navigation
class MainNavigationShell extends StatefulWidget {
  const MainNavigationShell({super.key});

  @override
  State<MainNavigationShell> createState() => _MainNavigationShellState();
}

class _MainNavigationShellState extends State<MainNavigationShell> {
  int _selectedIndex = 0;

  final _screens = const [
    ChatScreen(),
    AgentDashboard(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _screens[_selectedIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) {
          setState(() => _selectedIndex = index);
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.chat_outlined),
            selectedIcon: Icon(Icons.chat),
            label: 'Chat',
          ),
          NavigationDestination(
            icon: Icon(Icons.hub_outlined),
            selectedIcon: Icon(Icons.hub),
            label: 'Agents',
          ),
        ],
      ),
    );
  }
}
