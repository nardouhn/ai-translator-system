import 'package:flutter/material.dart';

class AppTheme {
  // Light Mode Colors
  static const Color _lightBg = Color(0xFFF8F5FB);
  static const Color _lightSurface = Color(0xFFFFFFFF);
  static const Color _lightPrimary = Color(0xFF7E3FB8);
  static const Color _lightSecondary = Color(0xFFB580E0);
  static const Color _lightText = Color(0xFF1E1525);

  // Dark Mode Colors
  static const Color _darkBg = Color(0xFF0D0814);
  static const Color _darkSurface = Color(0xFF1A1325);
  static const Color _darkPrimary = Color(0xFFA55EED);
  static const Color _darkSecondary = Color(0xFFC794F5);
  static const Color _darkText = Color(0xFFEFE8F7);

  static ThemeData get lightTheme {
    final scheme = const ColorScheme.light(
      primary: _lightPrimary,
      secondary: _lightSecondary,
      surface: _lightSurface,
      onPrimary: Colors.white,
      onSecondary: Colors.white,
      onSurface: _lightText,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      scaffoldBackgroundColor: _lightBg,
      colorScheme: scheme,
      textTheme: const TextTheme(
        titleLarge: TextStyle(color: _lightText, fontWeight: FontWeight.bold),
        bodyMedium: TextStyle(color: _lightText),
      ),
      navigationRailTheme: NavigationRailThemeData(
        backgroundColor: _lightSurface,
        selectedIconTheme: const IconThemeData(color: _lightPrimary),
        unselectedIconTheme: IconThemeData(
          color: _lightText.withValues(alpha: 0.65),
        ),
        selectedLabelTextStyle: const TextStyle(
          color: _lightPrimary,
          fontWeight: FontWeight.w600,
        ),
        unselectedLabelTextStyle: TextStyle(
          color: _lightText.withValues(alpha: 0.75),
        ),
        indicatorColor: _lightPrimary.withValues(alpha: 0.14),
      ),
      cardTheme: CardThemeData(
        color: _lightSurface,
        elevation: 4,
        shadowColor: _lightPrimary.withValues(alpha: 0.1),
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(20)),
        ),
      ),
    );
  }

  static ThemeData get darkTheme {
    final scheme = const ColorScheme.dark(
      primary: _darkPrimary,
      secondary: _darkSecondary,
      surface: _darkSurface,
      onPrimary: Colors.white,
      onSecondary: Colors.white,
      onSurface: _darkText,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: _darkBg,
      colorScheme: scheme,
      textTheme: const TextTheme(
        titleLarge: TextStyle(color: _darkText, fontWeight: FontWeight.bold),
        bodyMedium: TextStyle(color: _darkText),
      ),
      navigationRailTheme: NavigationRailThemeData(
        backgroundColor: _darkSurface,
        selectedIconTheme: const IconThemeData(color: _darkPrimary),
        unselectedIconTheme: IconThemeData(
          color: _darkText.withValues(alpha: 0.7),
        ),
        selectedLabelTextStyle: const TextStyle(
          color: _darkPrimary,
          fontWeight: FontWeight.w600,
        ),
        unselectedLabelTextStyle: TextStyle(
          color: _darkText.withValues(alpha: 0.75),
        ),
        indicatorColor: _darkPrimary.withValues(alpha: 0.2),
      ),
      cardTheme: CardThemeData(
        color: _darkSurface,
        elevation: 8,
        shadowColor: Colors.black.withValues(alpha: 0.4),
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(20)),
        ),
      ),
    );
  }
}
