import 'package:flutter/material.dart';

class DomainSelector extends StatelessWidget {
  const DomainSelector({super.key, this.scale = 1});

  final double scale;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textColor = Theme.of(context).colorScheme.onSurface;

    return Row(
      children: [
        Text(
          'Domain:',
          style: TextStyle(
            color: textColor.withValues(alpha: 0.8),
            fontSize: 20 * scale,
            fontWeight: FontWeight.w500,
          ),
        ),
        SizedBox(width: 14 * scale),
        Container(
          padding: EdgeInsets.symmetric(
            horizontal: 16 * scale,
            vertical: 8 * scale,
          ),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20 * scale),
            color: isDark ? const Color(0xFF302848) : const Color(0xFF9659CF),
          ),
          child: Row(
            children: [
              Text(
                'General',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 16 * scale,
                  fontWeight: FontWeight.w500,
                ),
              ),
              SizedBox(width: 8 * scale),
              Icon(
                Icons.keyboard_arrow_down_rounded,
                color: Colors.white.withValues(alpha: 0.9),
                size: 18 * scale,
              ),
            ],
          ),
        ),
      ],
    );
  }
}
