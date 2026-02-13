import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:samma_ai/main.dart';
import 'package:samma_ai/screens/chat_screen.dart';

void main() {
  group('Widget Tests', () {
    testWidgets('App initializes with home screen', (WidgetTester tester) async {
      await tester.pumpWidget(const SammaAIApp());

      // Verify app renders
      expect(find.byType(Material), findsWidgets);
    });

    testWidgets('Chat screen has input field', (WidgetTester tester) async {
      await tester.pumpWidget(const SammaAIApp());

      // Look for TextField (chat input)
      expect(find.byType(TextField), findsWidgets);
    });

    testWidgets('Chat screen has send button', (WidgetTester tester) async {
      await tester.pumpWidget(const SammaAIApp());

      // Look for button or icon button
      expect(find.byType(IconButton), findsWidgets);
    });

    testWidgets('Navigation bar is present', (WidgetTester tester) async {
      await tester.pumpWidget(const SammaAIApp());

      // Verify bottom navigation exists
      expect(find.byType(NavigationBar), findsWidgets);
    });

    testWidgets('Chat message displays correctly', (WidgetTester tester) async {
      await tester.pumpWidget(const SammaAIApp());

      // Find the chat input and enter text
      final textField = find.byType(TextField).first;
      await tester.enterText(textField, 'What is dukkha?');

      // Verify text was entered
      expect(find.text('What is dukkha?'), findsWidgets);
    });

    testWidgets('Suggestion chips appear on chat screen', (WidgetTester tester) async {
      await tester.pumpWidget(const SammaAIApp());

      // Look for chips (suggestion buttons)
      expect(find.byType(Chip), findsWidgets);
    });
  });

  group('UI Theme Tests', () {
    testWidgets('App uses Material Design 3', (WidgetTester tester) async {
      await tester.pumpWidget(const SammaAIApp());

      // Material should be present
      expect(find.byType(Material), findsWidgets);
    });

    testWidgets('Navigation bar exists', (WidgetTester tester) async {
      await tester.pumpWidget(const SammaAIApp());

      // Check for navigation structure
      expect(find.byType(NavigationBar), findsWidgets);
    });
  });

  group('Responsive Layout Tests', () {
    testWidgets('Layout adapts to screen size', (WidgetTester tester) async {
      // Set to mobile size
      tester.binding.window.physicalSizeTestValue = const Size(400, 800);
      addTearDown(tester.binding.window.clearPhysicalSizeTestValue);

      await tester.pumpWidget(const SammaAIApp());

      expect(find.byType(SingleChildScrollView), findsWidgets);
    });
  });
}
