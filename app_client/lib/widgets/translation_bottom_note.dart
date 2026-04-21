import 'package:flutter/material.dart';

class TranslationBottomNote extends StatelessWidget {
  const TranslationBottomNote({super.key, this.scale = 1});

  final double scale;

  @override
  Widget build(BuildContext context) {
    final textColor = Theme.of(context).colorScheme.onSurface;
    return Padding(
      padding: EdgeInsets.only(top: 24 * scale, bottom: 4 * scale),
      child: Center(
        child: Text(
          '© 2024 LUMINA LEXICON. ALL RIGHTS RESERVED.',
          style: TextStyle(
            fontSize: 12 * scale,
            letterSpacing: 0.5,
            color: textColor.withValues(alpha: 0.32),
            fontWeight: FontWeight.w500,
          ),
        ),
      ),
    );
  }
}
