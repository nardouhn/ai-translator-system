import 'package:flutter/material.dart';

class TranslationDualPanel extends StatelessWidget {
  const TranslationDualPanel({super.key, this.scale = 1});

  final double scale;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final primary = Theme.of(context).colorScheme.primary;
    final panelBgLeft = isDark ? const Color(0xFF19182B) : const Color(0xFFFAFAFA);
    final panelBgRight = isDark ? const Color(0xFF1C1B30) : const Color(0xFFEEDAF7);
    final border = isDark ? const Color(0xFF2A2740) : const Color(0xFFE7D2F3);
    final textColor = Theme.of(context).colorScheme.onSurface;

    return Container(
      width: 1500 * scale,
      height: 520 * scale,
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF171628) : const Color(0xFFF8ECFF),
        borderRadius: BorderRadius.circular(28 * scale),
        boxShadow: [
          BoxShadow(
            color: (isDark ? const Color(0xFFAB57FF) : const Color(0xFFBE86E3))
                .withValues(alpha: isDark ? 0.2 : 0.35),
            blurRadius: (isDark ? 26 : 20) * scale,
            spreadRadius: isDark ? 1 : 0,
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(28 * scale),
        child: Stack(
          alignment: Alignment.center,
          children: [
            Row(
              children: [
                Expanded(
                  child: _EditorPane(
                    title: 'English',
                    subtitle: 'DETECTED',
                    hintText: 'Type or paste text to translate...',
                    footerLeft: '0 / 5000',
                    footerIcons: const [Icons.mic_none_rounded],
                    backgroundColor: panelBgLeft,
                    textColor: textColor,
                    borderColor: border,
                    scale: scale,
                  ),
                ),
                Container(
                  width: 2 * scale,
                  decoration: BoxDecoration(
                    color: border,
                    boxShadow: [
                      BoxShadow(
                        color: primary.withValues(
                          alpha: isDark ? 0.22 : 0.28,
                        ),
                        blurRadius: 18 * scale,
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: _EditorPane(
                    title: 'Vietnamese',
                    subtitle: null,
                    hintText: 'Translation will appear here...',
                    footerLeft: '',
                    footerIcons: const [
                      Icons.volume_up_outlined,
                      Icons.copy_all_outlined,
                      Icons.share_outlined,
                    ],
                    backgroundColor: panelBgRight,
                    textColor: textColor,
                    borderColor: border,
                    scale: scale,
                  ),
                ),
              ],
            ),
            Container(
              width: 64 * scale,
              height: 64 * scale,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: const LinearGradient(
                  colors: [Color(0xFF8B2CFF), Color(0xFFD22DFF)],
                ),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFFB23FFF).withValues(alpha: 0.45),
                    blurRadius: 22 * scale,
                    spreadRadius: 2,
                  ),
                ],
              ),
              child: Icon(
                Icons.compare_arrows_rounded,
                color: Colors.white,
                size: 26 * scale,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _EditorPane extends StatelessWidget {
  const _EditorPane({
    required this.title,
    required this.subtitle,
    required this.hintText,
    required this.footerLeft,
    required this.footerIcons,
    required this.backgroundColor,
    required this.textColor,
    required this.borderColor,
    required this.scale,
  });

  final String title;
  final String? subtitle;
  final String hintText;
  final String footerLeft;
  final List<IconData> footerIcons;
  final Color backgroundColor;
  final Color textColor;
  final Color borderColor;
  final double scale;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: backgroundColor,
      padding: EdgeInsets.fromLTRB(
        32 * scale,
        24 * scale,
        26 * scale,
        18 * scale,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                title,
                style: TextStyle(
                  color: textColor.withValues(alpha: 0.9),
                  fontSize: 16 * scale,
                  fontWeight: FontWeight.w700,
                ),
              ),
              if (subtitle != null) ...[
                const Spacer(),
                Row(
                  children: [
                    if (subtitle == 'DETECTED') ...[
                      Icon(
                        Icons.auto_awesome_rounded,
                        size: 14 * scale,
                        color: textColor.withValues(alpha: 0.55),
                      ),
                      SizedBox(width: 6 * scale),
                    ],
                    Text(
                      subtitle!,
                      style: TextStyle(
                        color: textColor.withValues(alpha: 0.5),
                        fontSize: 13 * scale,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.3,
                      ),
                    ),
                  ],
                ),
              ],
            ],
          ),
          SizedBox(height: 18 * scale),
          Divider(color: borderColor, thickness: 1),
          SizedBox(height: 22 * scale),
          Text(
            hintText,
            style: TextStyle(
              color: textColor.withValues(alpha: 0.35),
              fontSize: 18 * scale,
              fontWeight: FontWeight.w500,
            ),
          ),
          const Spacer(),
          Row(
            children: [
              Text(
                footerLeft,
                style: TextStyle(
                  color: textColor.withValues(alpha: 0.35),
                  fontSize: 12 * scale,
                ),
              ),
              const Spacer(),
              for (final icon in footerIcons) ...[
                Icon(
                  icon,
                  color: textColor.withValues(alpha: 0.72),
                  size: 18 * scale,
                ),
                SizedBox(width: 18 * scale),
              ],
            ],
          ),
        ],
      ),
    );
  }
}
