import 'package:flutter/material.dart';

class DomainDropdown extends StatelessWidget {
  const DomainDropdown({
    super.key,
    this.scale = 1,
    required this.selectedDomain,
    required this.onDomainChanged,
  });

  final double scale;
  final String selectedDomain;
  final ValueChanged<String> onDomainChanged;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textColor = Theme.of(context).colorScheme.onSurface;

    final domains = [
      'General',
      'Medical',
      'Business',
      'IT/Technical'
    ];

    // Cố gắng tìm giá trị hợp lệ, nếu không có fallback về General
    final currentValue = domains.contains(selectedDomain) ? selectedDomain : domains.first;

    return Row(
      children: [
        Text(
          'Domain:',
          style: TextStyle(
            color: textColor.withOpacity(0.8),
            fontSize: 20 * scale,
            fontWeight: FontWeight.w500,
          ),
        ),
        SizedBox(width: 14 * scale),
        Container(
          padding: EdgeInsets.symmetric(horizontal: 16 * scale, vertical: 4 * scale),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20 * scale),
            color: isDark ? const Color(0xFF302848) : const Color(0xFF9659CF),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: currentValue,
              dropdownColor: isDark ? const Color(0xFF302848) : const Color(0xFF9659CF),
              icon: Icon(
                Icons.keyboard_arrow_down_rounded,
                color: Colors.white.withOpacity(0.9),
                size: 18 * scale,
              ),
              style: TextStyle(
                color: Colors.white,
                fontSize: 16 * scale,
                fontWeight: FontWeight.w500,
              ),
              onChanged: (String? newValue) {
                if (newValue != null) {
                  onDomainChanged(newValue);
                }
              },
              items: domains.map((domain) {
                return DropdownMenuItem<String>(
                  value: domain,
                  child: Text(domain),
                );
              }).toList(),
            ),
          ),
        ),
      ],
    );
  }
}
