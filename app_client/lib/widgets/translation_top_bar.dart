import 'package:flutter/material.dart';

class TranslationTopBar extends StatelessWidget {
  const TranslationTopBar({
    super.key,
    this.scale = 1,
    required this.pageTitle,
    required this.onPagePressed,
    required this.isDarkMode,
    required this.onToggleTheme,
  });

  final double scale;
  final String pageTitle;
  final VoidCallback onPagePressed;
  final bool isDarkMode;
  final VoidCallback onToggleTheme;

  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;
    final textColor = Theme.of(context).colorScheme.onSurface;

    return Row(
      children: [
        Row(
          children: [
            Container(
              width: 38 * scale,
              height: 38 * scale,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(10 * scale),
                border: Border.all(color: primary, width: 1.2),
              ),
              child: Icon(
                Icons.g_translate_rounded,
                color: primary,
                size: 22 * scale,
              ),
            ),
            SizedBox(width: 12 * scale),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'AutoTrans',
                  style: TextStyle(
                    color: primary,
                    fontSize: 30 * scale,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(
                  'AI Translator',
                  style: TextStyle(
                    color: textColor.withValues(alpha: 0.6),
                    fontSize: 12 * scale,
                    fontStyle: FontStyle.italic,
                  ),
                ),
              ],
            ),
          ],
        ),
        const Spacer(),
        InkWell(
          onTap: onPagePressed,
          borderRadius: BorderRadius.circular(26 * scale),
          child: Container(
            padding: EdgeInsets.symmetric(
              horizontal: 22 * scale,
              vertical: 11 * scale,
            ),
            decoration: BoxDecoration(
              color:
                  isDarkMode ? const Color(0xFF3A174E) : const Color(0xFFE9D2FA),
              borderRadius: BorderRadius.circular(26 * scale),
              border: Border.all(
                color: isDarkMode
                    ? const Color(0xFF65407E)
                    : const Color(0xFFB98CDD),
              ),
            ),
            child: Row(
              children: [
                Icon(
                  Icons.insert_drive_file_outlined,
                  color: isDarkMode
                      ? const Color(0xFFD9A9FF)
                      : const Color(0xFF7D42B3),
                  size: 18 * scale,
                ),
                SizedBox(width: 8 * scale),
                Text(
                  pageTitle,
                  style: TextStyle(
                    color: isDarkMode
                        ? const Color(0xFFD9A9FF)
                        : const Color(0xFF7D42B3),
                    fontSize: 14 * scale,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ),
        SizedBox(width: 18 * scale),
        IconButton(
          onPressed: onToggleTheme,
          icon: Icon(
            isDarkMode ? Icons.light_mode_outlined : Icons.dark_mode_outlined,
            color: textColor.withValues(alpha: 0.75),
            size: 20 * scale,
          ),
          tooltip: isDarkMode ? 'Switch to light mode' : 'Switch to dark mode',
        ),
      ],
    );
  }
}
