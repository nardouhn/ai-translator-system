import 'package:flutter/material.dart';

class AppTheme {
  static const Color _lightBg = Color(0xFFF3E5F7);
  static const Color _lightSurface = Color(0xFFF0D9F5);
  static const Color _lightPrimary = Color(0xFF8E44CF);
  static const Color _lightSecondary = Color(0xFFCDA6E8);
  static const Color _lightText = Color(0xFF2F223A);

  static const Color _darkBg = Color(0xFF090511);
  static const Color _darkSurface = Color(0xFF1A1530);
  static const Color _darkPrimary = Color(0xFFB53CFF);
  static const Color _darkSecondary = Color(0xFFDDB3FF);
  static const Color _darkText = Color(0xFFF2E8FF);

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
      cardTheme: const CardThemeData(
        color: _lightSurface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(18)),
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
      cardTheme: const CardThemeData(
        color: _darkSurface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(18)),
        ),
      ),
    );
  }
}
