import 'package:flutter/material.dart';

import 'features/file_translation_view.dart';
import 'features/text_translation_view.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({
    super.key,
    required this.themeMode,
    required this.onToggleTheme,
  });

  final ThemeMode themeMode;
  final VoidCallback onToggleTheme;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedIndex = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 220),
          child: KeyedSubtree(
            key: ValueKey<int>(_selectedIndex),
            child: _selectedIndex == 0
                ? TextTranslationView(
                    isDarkMode: widget.themeMode == ThemeMode.dark,
                    onToggleTheme: widget.onToggleTheme,
                    onSwitchToFile: () {
                      setState(() {
                        _selectedIndex = 1;
                      });
                    },
                  )
                : FileTranslationView(
                    isDarkMode: widget.themeMode == ThemeMode.dark,
                    onToggleTheme: widget.onToggleTheme,
                    onSwitchToText: () {
                      setState(() {
                        _selectedIndex = 0;
                      });
                    },
                  ),
          ),
        ),
      ),
    );
  }
}
