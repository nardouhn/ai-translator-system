import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'dart:typed_data';
import 'dart:convert';
import 'package:universal_html/html.dart' as html;
import 'package:file_picker/file_picker.dart';

import '../services/api_service.dart';
import '../widgets/translation_top_bar.dart';
import '../widgets/domain_dropdown.dart';
import '../widgets/upload_dropzone.dart';
import '../widgets/file_info_card.dart';
import '../widgets/sidebar_queue.dart';

class FileTranslationView extends StatefulWidget {
  const FileTranslationView({
    super.key,
    required this.isDarkMode,
    required this.onToggleTheme,
    required this.onSwitchToText,
  });

  final bool isDarkMode;
  final VoidCallback onToggleTheme;
  final VoidCallback onSwitchToText;

  @override
  State<FileTranslationView> createState() => _FileTranslationViewState();
}

class _FileTranslationViewState extends State<FileTranslationView> {
  final List<Map<String, dynamic>> _activeQueue = [];
  bool _isDragging = false;
  bool _isTranslating = false;
  String? _selectedFileName;
  String? _selectedFileSize;
  Uint8List? _selectedFileBytes;
  String? _selectedFilePath;
  String _selectedDomain = 'General';
  String _selectedSourceLang = 'en';
  String _selectedTargetLang = 'vi';

  Future<void> _pickFile() async {
    try {
      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf', 'docx', 'txt'],
        withData: kIsWeb,
      );
      if (result != null && result.files.isNotEmpty) {
        final file = result.files.single;
        final path = kIsWeb ? null : file.path;
        _validateAndProcessFile(file.name, file.size, path, file.bytes);
      }
    } catch (e) {
      debugPrint('File picker error: $e');
    }
  }

  void _validateAndProcessFile(String fileName, int sizeInBytes, String? path, Uint8List? bytes) {
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

    setState(() {
      _selectedFileName = fileName;
      _selectedFilePath = path;
      _selectedFileBytes = bytes;
      _selectedFileSize = '${sizeInMb.toStringAsFixed(1)} MB';
    });
  }

  void _clearSelectedFile() {
    setState(() {
      _selectedFileName = null;
      _selectedFilePath = null;
      _selectedFileBytes = null;
      _selectedFileSize = null;
    });
  }

  void _onTranslatePressed() async {
    if (_selectedFileName == null || (_selectedFilePath == null && _selectedFileBytes == null)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a file first.')),
      );
      return;
    }

    final String ext = _selectedFileName!.split('.').last.toLowerCase();
    
    setState(() {
      _isTranslating = true;
      _activeQueue.add({
        'fileName': _selectedFileName,
        'fileType': ext,
        'fileSize': _selectedFileSize ?? 'Unknown',
        'status': 'Processing...',
        'progress': 0.5, // Giả lập progress
      });
    });

    try {
      final result = await ApiService.translateFile(
        filePath: _selectedFilePath,
        fileBytes: _selectedFileBytes,
        fileName: _selectedFileName,
        sourceLang: _selectedSourceLang,
        targetLang: _selectedTargetLang,
        domain: _selectedDomain,
      );

      if (!mounted) return;
      setState(() {
        _activeQueue.last['status'] = 'Done';
        _activeQueue.last['progress'] = 1.0;
        _activeQueue.last['translatedText'] = result['translated_text'];
        _activeQueue.last['fileContentB64'] = result['file_content_b64'];
      });
      debugPrint("Translation success: ${result['file_id']}");
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _activeQueue.last['status'] = 'Error';
        _activeQueue.last['progress'] = 0.0;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Lỗi hệ thống: $e'),
          backgroundColor: Colors.redAccent,
        ),
      );
      debugPrint("Translation error: $e");
    } finally {
      if (mounted) {
        setState(() {
          _isTranslating = false;
        });
      }
    }

    _clearSelectedFile();
  }

  void _onDownload(int index) {
    final item = _activeQueue[index];
    final b64Data = item['fileContentB64'] as String?;
    final text = item['translatedText'] as String?;
    
    if (b64Data == null && text == null) return;
    
    if (kIsWeb) {
      if (b64Data != null && b64Data.isNotEmpty) {
        // Trả về file docx hoặc txt xịn từ base64
        final bytes = base64Decode(b64Data);
        final blob = html.Blob([bytes]);
        final url = html.Url.createObjectUrlFromBlob(blob);
        final originalFileName = item['fileName'] as String;
        final isPdf = originalFileName.toLowerCase().endsWith('.pdf');
        
        final downloadName = isPdf 
            ? 'translated_${originalFileName.substring(0, originalFileName.length - 4)}.docx'
            : 'translated_$originalFileName';
            
        final anchor = html.AnchorElement(href: url)
          ..setAttribute("download", downloadName)
          ..click();
        html.Url.revokeObjectUrl(url);
      } else if (text != null) {
        // Fallback: Lưu dưới dạng txt thuần túy
        final bytes = utf8.encode(text);
        final blob = html.Blob([bytes]);
        final url = html.Url.createObjectUrlFromBlob(blob);
        final anchor = html.AnchorElement(href: url)
          ..setAttribute("download", "translated_${item['fileName']}.txt")
          ..click();
        html.Url.revokeObjectUrl(url);
      }
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Download not implemented for desktop yet.')),
      );
    }
  }

  void _onDelete(int index) {
    setState(() {
      _activeQueue.removeAt(index);
    });
  }

  Widget _buildLangDropdown(String label, String currentValue, ValueChanged<String?> onChanged) {
    final primaryColor = Theme.of(context).colorScheme.primary;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      decoration: BoxDecoration(
        color: primaryColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: primaryColor.withOpacity(0.3)),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: currentValue,
          dropdownColor: Theme.of(context).colorScheme.surface,
          icon: Icon(Icons.language, size: 18, color: primaryColor),
          style: TextStyle(
            color: Theme.of(context).colorScheme.onSurface,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
          items: const [
            DropdownMenuItem(value: 'en', child: Text('English')),
            DropdownMenuItem(value: 'vi', child: Text('Vietnamese')),
          ],
          onChanged: onChanged,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final primaryColor = Theme.of(context).colorScheme.primary;

    final gradientColors = isDark
        ? [const Color(0xFF130927), const Color(0xFF090511)]
        : [const Color(0xFFFDFBFF), const Color(0xFFF3E5F7)];

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: Container(
        key: const ValueKey<String>('file_translation_view'),
        width: double.infinity,
        height: double.infinity,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: gradientColors,
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 42, vertical: 24),
        child: Column(
          children: [
            TranslationTopBar(
              scale: 1,
              pageTitle: 'Text Translation',
              onPagePressed: widget.onSwitchToText,
              isDarkMode: widget.isDarkMode,
              onToggleTheme: widget.onToggleTheme,
            ),
            const SizedBox(height: 32),
            Expanded(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    flex: 3,
                    child: Card(
                      margin: EdgeInsets.zero,
                      child: Padding(
                        padding: const EdgeInsets.all(24.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'File Translation',
                              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                    fontSize: 24,
                                  ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Upload a document to translate its contents while preserving layout.',
                              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                    color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                                  ),
                            ),
                            const SizedBox(height: 24),
                            Expanded(
                              child: _selectedFileName != null
                                  ? FileInfoCard(
                                      fileName: _selectedFileName!,
                                      onClear: _clearSelectedFile,
                                    )
                                  : UploadDropzone(
                                      isDragging: _isDragging,
                                      onDraggingChanged: (val) => setState(() => _isDragging = val),
                                      onFileDropped: _validateAndProcessFile,
                                      onPickFile: _pickFile,
                                    ),
                            ),
                            const SizedBox(height: 24),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Expanded(
                                  child: Wrap(
                                    spacing: 16,
                                    runSpacing: 16,
                                    crossAxisAlignment: WrapCrossAlignment.center,
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
                                      _buildLangDropdown('en', _selectedSourceLang, (val) => setState(() => _selectedSourceLang = val!)),
                                      const Icon(Icons.arrow_forward_rounded, color: Colors.grey),
                                      _buildLangDropdown('vi', _selectedTargetLang, (val) => setState(() => _selectedTargetLang = val!)),
                                    ],
                                  ),
                                ),
                                const SizedBox(width: 16),
                                ElevatedButton.icon(
                                  onPressed: _isTranslating ? null : _onTranslatePressed,
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: primaryColor,
                                    foregroundColor: Colors.white,
                                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                    elevation: 4,
                                  ),
                                  icon: _isTranslating
                                      ? const SizedBox(
                                          width: 20,
                                          height: 20,
                                          child: CircularProgressIndicator(
                                            color: Colors.white,
                                            strokeWidth: 2,
                                          ),
                                        )
                                      : const Icon(Icons.auto_awesome, size: 20),
                                  label: Text(
                                    _isTranslating ? 'Translating...' : 'Translate Document',
                                    style: const TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 24),
                  SizedBox(
                    width: 320,
                    child: Card(
                      margin: EdgeInsets.zero,
                      child: Padding(
                        padding: const EdgeInsets.all(24.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Translation Queue',
                              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                    fontSize: 20,
                                  ),
                            ),
                            const SizedBox(height: 16),
                            Expanded(
                              child: SidebarQueueWidget(
                                queue: _activeQueue,
                                onDownload: _onDownload,
                                onDelete: _onDelete,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
