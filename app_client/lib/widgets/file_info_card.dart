import 'package:flutter/material.dart';
import 'package:dotted_border/dotted_border.dart';

class FileInfoCard extends StatelessWidget {
  const FileInfoCard({
    super.key,
    required this.fileName,
    required this.onClear,
  });

  final String fileName;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    final primaryColor = Theme.of(context).colorScheme.primary;
    final onSurface = Theme.of(context).colorScheme.onSurface;

    return DottedBorder(
      color: primaryColor.withOpacity(0.5),
      strokeWidth: 2,
      dashPattern: const [8, 4],
      borderType: BorderType.RRect,
      radius: const Radius.circular(16),
      child: Container(
        width: double.infinity,
        decoration: BoxDecoration(
          color: primaryColor.withOpacity(0.05),
          borderRadius: BorderRadius.circular(16),
        ),
        child: SingleChildScrollView(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.description_rounded, size: 48, color: primaryColor),
              const SizedBox(height: 12),
              Text(
                fileName,
                style: TextStyle(color: onSurface, fontSize: 16, fontWeight: FontWeight.bold),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 4),
              const Text('Ready to translate', style: TextStyle(color: Colors.green, fontSize: 14)),
              const SizedBox(height: 16),
              TextButton.icon(
                onPressed: onClear,
                style: TextButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  textStyle: const TextStyle(fontSize: 14),
                ),
                icon: const Icon(Icons.close, color: Colors.redAccent, size: 18),
                label: const Text('Remove', style: TextStyle(color: Colors.redAccent)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
