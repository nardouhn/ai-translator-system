import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'dart:typed_data';
import 'dart:convert';
import 'package:universal_html/html.dart' as html;
import 'package:file_picker/file_picker.dart' as fp;
import 'package:url_launcher/url_launcher.dart';

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
  final String _selectedSourceLang = 'en';
  final String _selectedTargetLang = 'vi';

  Future<void> _pickFile() async {
    try {
      fp.FilePickerResult? result = await fp.FilePicker.pickFiles(
        type: fp.FileType.custom,
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
    if (sizeInMb > 5) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('File exceeds 5MB limit. Please upload another file.'),
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
      final initResult = await ApiService.translateFile(
        filePath: _selectedFilePath,
        fileBytes: _selectedFileBytes,
        fileName: _selectedFileName,
        domain: _selectedDomain,
      );

      final int fileId = initResult['file_id'];
      Map<String, dynamic> statusResult = {};
      bool isSuccess = false;

      int consecutiveErrors = 0;

      // Poll until success or failure (timeout after ~1200 seconds for large files)
      for (int i = 0; i < 600; i++) {
        // Tự động giãn thời gian delay để tiết kiệm pin: 
        // 20 lần đầu (40s) chờ 2s, sau đó chờ 5s.
        int delaySeconds = (i < 20) ? 2 : 5;
        await Future.delayed(Duration(seconds: delaySeconds));
        
        if (!mounted) return;
        
        try {
          statusResult = await ApiService.checkFileStatus(fileId);
          consecutiveErrors = 0; // Reset counter on success
        } catch (e) {
          consecutiveErrors++;
          if (consecutiveErrors > 15) {
            throw Exception('Mất kết nối mạng quá lâu. Vui lòng kiểm tra lại Internet.');
          }
          debugPrint('Network error during polling (attempt $consecutiveErrors/15): $e');
          continue; // Skip the rest of the loop and try again later
        }

        final statusStr = statusResult['status'];
        final progressVal = statusResult['progress'] ?? 0;
        
        setState(() {
          _activeQueue.last['progress'] = progressVal / 100.0;
          if (statusStr == 'processing') {
            _activeQueue.last['status'] = 'Processing ($progressVal%)...';
          }
        });
        
        if (statusStr == 'success') {
          isSuccess = true;
          break;
        } else if (statusStr == 'failed' || statusStr == 'error') {
          throw Exception('Translation failed on server.');
        }
      }

      if (!isSuccess) {
        throw Exception('Translation timed out.');
      }

      if (!mounted) return;
      setState(() {
        _activeQueue.last['status'] = 'Done';
        _activeQueue.last['progress'] = 1.0;
        _activeQueue.last['translatedText'] = statusResult['translated_text'];
        _activeQueue.last['fileContentB64'] = statusResult['file_content_b64'];
        _activeQueue.last['fileUrl'] = statusResult['file_url'];
      });
      debugPrint("Translation success: $fileId");
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
    final fileUrl = item['fileUrl'] as String?;
    final b64Data = item['fileContentB64'] as String?;
    final text = item['translatedText'] as String?;
    
    if (fileUrl != null && fileUrl.isNotEmpty) {
      if (kIsWeb) {
        html.window.open(fileUrl, '_blank');
      } else {
        final uri = Uri.parse(fileUrl);
        launchUrl(uri, mode: LaunchMode.externalApplication).then((success) {
          if (!success) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Could not open download link.')),
            );
          }
        }).catchError((error) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Could not open download link.')),
          );
        });
      }
      return;
    }
    
    if (b64Data == null && text == null) return;
    
    if (kIsWeb) {
      if (b64Data != null && b64Data.isNotEmpty) {
        // Trả về file docx hoặc txt xịn từ base64
        String sanitizedB64 = b64Data.replaceAll(RegExp(r'\s+'), '');
        final padLength = (4 - (sanitizedB64.length % 4)) % 4;
        sanitizedB64 = sanitizedB64.padRight(sanitizedB64.length + padLength, '=');
        
        final bytes = base64Decode(sanitizedB64);
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

  Widget _buildMainCardContent(BuildContext context, Color primaryColor, bool isMobile) {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
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
          _selectedFileName != null
              ? FileInfoCard(
                  fileName: _selectedFileName!,
                  onClear: _clearSelectedFile,
                )
              : SizedBox(
                  height: 250,
                  child: UploadDropzone(
                    isDragging: _isDragging,
                    onDraggingChanged: (val) => setState(() => _isDragging = val),
                    onFileDropped: _validateAndProcessFile,
                    onPickFile: _pickFile,
                  ),
                ),
          const SizedBox(height: 24),
          // Language and Translate controls
          isMobile
              ? Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      alignment: WrapAlignment.center,
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
                        _buildFixedLangLabel('English'),
                        const Icon(Icons.arrow_forward_rounded, color: Colors.grey),
                        _buildFixedLangLabel('Vietnamese'),
                      ],
                    ),
                    const SizedBox(height: 16),
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
                )
              : Row(
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
                          _buildFixedLangLabel('English'),
                          const Icon(Icons.arrow_forward_rounded, color: Colors.grey),
                          _buildFixedLangLabel('Vietnamese'),
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
    );
  }

  void _onDelete(int index) {
    setState(() {
      _activeQueue.removeAt(index);
    });
  }

  Widget _buildFixedLangLabel(String label) {
    final primaryColor = Theme.of(context).colorScheme.primary;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: primaryColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: primaryColor.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.language, size: 18, color: primaryColor),
          const SizedBox(width: 8),
          Text(
            label,
            style: TextStyle(
              color: Theme.of(context).colorScheme.onSurface,
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
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
      body: LayoutBuilder(
        builder: (context, constraints) {
          final isMobile = constraints.maxWidth < 600;
          return Container(
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
            child: SingleChildScrollView(
              padding: EdgeInsets.symmetric(
                horizontal: isMobile ? 16 : 42,
                vertical: isMobile ? 16 : 24,
              ),
              child: Column(
                children: [
                  TranslationTopBar(
                    scale: isMobile ? 0.85 : 1.0,
                    pageTitle: 'Text Translation',
                    onPagePressed: widget.onSwitchToText,
                    isDarkMode: widget.isDarkMode,
                    onToggleTheme: widget.onToggleTheme,
                  ),
                  SizedBox(height: isMobile ? 16 : 32),
                  Flex(
                    direction: isMobile ? Axis.vertical : Axis.horizontal,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Main translation card
                      if (isMobile)
                        Card(
                          margin: EdgeInsets.zero,
                          child: _buildMainCardContent(context, primaryColor, isMobile),
                        )
                      else
                        Expanded(
                          flex: 3,
                          child: Card(
                            margin: EdgeInsets.zero,
                            child: _buildMainCardContent(context, primaryColor, isMobile),
                          ),
                        ),
                      if (isMobile) const SizedBox(height: 16) else const SizedBox(width: 24),
                      // Queue card
                      SizedBox(
                        width: isMobile ? double.infinity : 320,
                        child: Card(
                          margin: EdgeInsets.zero,
                          child: Padding(
                            padding: const EdgeInsets.all(24.0),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(
                                  'Translation Queue',
                                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                        fontSize: 20,
                                      ),
                                ),
                                const SizedBox(height: 16),
                                SidebarQueueWidget(
                                  queue: _activeQueue,
                                  onDownload: _onDownload,
                                  onDelete: _onDelete,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 48), // Padding at bottom
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
