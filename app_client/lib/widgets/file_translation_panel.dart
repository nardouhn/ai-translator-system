import 'package:flutter/material.dart';
import 'package:dotted_border/dotted_border.dart';
import 'package:file_picker/file_picker.dart';
import 'package:desktop_drop/desktop_drop.dart';
import 'domain_dropdown.dart';

class FileTranslationPanel extends StatefulWidget {
  const FileTranslationPanel({
    super.key,
    required this.onFileValidated,
    required this.onTranslatePressed,
  });

  final Function(String fileName, int sizeInBytes, String path) onFileValidated;
  final Function(String domain) onTranslatePressed;

  @override
  State<FileTranslationPanel> createState() => _FileTranslationPanelState();
}

class _FileTranslationPanelState extends State<FileTranslationPanel> {
  bool _isDragging = false;
  String? _selectedFileName;
  String _selectedDomain = 'General';

  Future<void> _pickFile() async {
    try {
      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf', 'docx', 'txt'],
      );
      if (result != null && result.files.isNotEmpty) {
        final file = result.files.single;
        _validateAndProcessFile(file.name, file.size, file.path ?? '');
      }
    } catch (e) {
      debugPrint('File picker error: $e');
    }
  }

  void _validateAndProcessFile(String fileName, int sizeInBytes, String path) {
    final ext = fileName.split('.').last.toLowerCase();
    if (ext != 'pdf' && ext != 'docx' && ext != 'txt') {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Invalid file format. Please upload another file.'),
          backgroundColor: Colors.redAccent,
        ),
      );
      return;
    }

    final double sizeInMb = sizeInBytes / (1024 * 1024);
    if (sizeInMb > 20) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('File exceeds 20MB limit. Please upload another file.'),
          backgroundColor: Colors.redAccent,
        ),
      );
      return;
    }

    if (mounted) {
      setState(() {
        _selectedFileName = fileName;
      });
    }

    widget.onFileValidated(fileName, sizeInBytes, path);
  }

  @override
  Widget build(BuildContext context) {
    final primaryColor = Theme.of(context).colorScheme.primary;
    final onSurface = Theme.of(context).colorScheme.onSurface;

    return Column(
      children: [
        Expanded(
          child: DropTarget(
            onDragEntered: (details) => setState(() => _isDragging = true),
            onDragExited: (details) => setState(() => _isDragging = false),
            onDragDone: (details) async {
              setState(() => _isDragging = false);
              if (details.files.isNotEmpty) {
                final file = details.files.first;
                final len = await file.length();
                _validateAndProcessFile(file.name, len, file.path);
              }
            },
            child: DottedBorder(
              color: _isDragging ? primaryColor : primaryColor.withOpacity(0.5),
              strokeWidth: 2,
              dashPattern: const [8, 4],
              borderType: BorderType.RRect,
              radius: const Radius.circular(16),
              child: Container(
                width: double.infinity,
                decoration: BoxDecoration(
                  color: _isDragging ? primaryColor.withOpacity(0.15) : primaryColor.withOpacity(0.05),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    if (_selectedFileName != null) ...[
                      Icon(Icons.description_rounded, size: 64, color: primaryColor),
                      const SizedBox(height: 16),
                      Text(
                        _selectedFileName!,
                        style: TextStyle(color: onSurface, fontSize: 18, fontWeight: FontWeight.bold),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 8),
                      const Text('Ready to translate', style: TextStyle(color: Colors.green, fontSize: 14)),
                    ] else ...[
                      Icon(
                        Icons.cloud_upload_outlined,
                        size: 64,
                        color: _isDragging ? primaryColor : primaryColor.withOpacity(0.7),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'Upload Manuscript',
                        style: TextStyle(
                          color: onSurface,
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Drag and drop PDF, DOCX, or TXT here',
                        style: TextStyle(
                          color: onSurface.withOpacity(0.6),
                          fontSize: 14,
                        ),
                      ),
                    ],
                    const SizedBox(height: 24),
                    InkWell(
                      onTap: _pickFile,
                      borderRadius: BorderRadius.circular(24),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 12),
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
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
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
        ),
        const SizedBox(height: 24),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            DomainDropdown(
              scale: 0.8,
              selectedDomain: _selectedDomain,
              onDomainChanged: (newValue) {
                setState(() {
                  _selectedDomain = newValue;
                });
              },
            ),
            ElevatedButton.icon(
              onPressed: () {
                if (_selectedFileName == null) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Please select a file first.')),
                  );
                  return;
                }
                widget.onTranslatePressed(_selectedDomain);
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: primaryColor,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                elevation: 4,
              ),
              icon: const Icon(Icons.auto_awesome, size: 20),
              label: const Text(
                'Translate Document',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }
}
