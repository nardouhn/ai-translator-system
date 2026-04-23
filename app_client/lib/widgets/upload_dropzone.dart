import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:dotted_border/dotted_border.dart';
import 'package:desktop_drop/desktop_drop.dart';
import 'dart:typed_data';

class UploadDropzone extends StatelessWidget {
  const UploadDropzone({
    super.key,
    required this.isDragging,
    required this.onDraggingChanged,
    required this.onFileDropped,
    required this.onPickFile,
  });

  final bool isDragging;
  final ValueChanged<bool> onDraggingChanged;
  final Function(String fileName, int sizeInBytes, String? path, Uint8List? bytes) onFileDropped;
  final VoidCallback onPickFile;

  @override
  Widget build(BuildContext context) {
    final primaryColor = Theme.of(context).colorScheme.primary;
    final onSurface = Theme.of(context).colorScheme.onSurface;

    return DropTarget(
      onDragEntered: (details) => onDraggingChanged(true),
      onDragExited: (details) => onDraggingChanged(false),
      onDragDone: (details) async {
        onDraggingChanged(false);
        if (details.files.isNotEmpty) {
          final file = details.files.first;
          final len = await file.length();
          final bytes = await file.readAsBytes();
          final path = kIsWeb ? null : file.path;
          onFileDropped(file.name, len, path, bytes);
        }
      },
      child: DottedBorder(
        color: isDragging ? primaryColor : primaryColor.withOpacity(0.5),
        strokeWidth: 2,
        dashPattern: const [8, 4],
        borderType: BorderType.RRect,
        radius: const Radius.circular(16),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: isDragging ? primaryColor.withOpacity(0.15) : primaryColor.withOpacity(0.05),
            borderRadius: BorderRadius.circular(16),
          ),
          child: SingleChildScrollView(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.cloud_upload_outlined,
                  size: 40,
                  color: isDragging ? primaryColor : primaryColor.withOpacity(0.7),
                ),
                const SizedBox(height: 12),
                Text(
                  'Upload Manuscript',
                  style: TextStyle(
                    color: onSurface,
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Drag and drop PDF, DOCX, or TXT here',
                  style: TextStyle(
                    color: onSurface.withOpacity(0.6),
                    fontSize: 12,
                  ),
                ),
                const SizedBox(height: 16),
                InkWell(
                  onTap: onPickFile,
                  borderRadius: BorderRadius.circular(24),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFFB53CFF), Color(0xFF8E44CF)],
                        begin: Alignment.centerLeft,
                        end: Alignment.centerRight,
                      ),
                      borderRadius: BorderRadius.circular(24),
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFFB53CFF).withOpacity(0.3),
                          blurRadius: 8,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: const Text(
                      'Browse Files',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'MAXIMUM FILE SIZE: 20MB',
                  style: TextStyle(
                    color: onSurface.withOpacity(0.4),
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 1.2,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
