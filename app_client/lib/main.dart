import 'package:flutter/material.dart';

import 'app_theme.dart';
import 'home_screen.dart';

void main() {
  runApp(const AutoTransApp());
}

class AutoTransApp extends StatefulWidget {
  const AutoTransApp({super.key});

  @override
  State<AutoTransApp> createState() => _AutoTransAppState();
}

class _AutoTransAppState extends State<AutoTransApp> {
  ThemeMode _themeMode = ThemeMode.dark;

  void _toggleThemeMode() {
    setState(() {
      _themeMode =
          _themeMode == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AutoTrans',
      debugShowCheckedModeBanner: false,
      themeMode: _themeMode,
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      home: HomeScreen(
        themeMode: _themeMode,
        onToggleTheme: _toggleThemeMode,
      ),
    );
  }
}
