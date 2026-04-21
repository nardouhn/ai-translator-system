import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:http/http.dart' as http;

import '../services/api_service.dart';
import '../widgets/translation_top_bar.dart';

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
  bool _isLoading = false;
  String _resultText = '';
  String _errorMessage = '';
  String _selectedFilePath = '';
  String _sourceLang = 'en';
  String _targetLang = 'vi';

  Future<String> translateFile(String filePath) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('http://10.0.2.2:8000/api/v1/file/translate'),
    );

    request.fields['source_lang'] = _sourceLang;
    request.fields['target_lang'] = _targetLang;

    if (ApiService.sessionId != null) {
      request.headers['X-Session-ID'] = ApiService.sessionId!;
    }

    request.files.add(
      await http.MultipartFile.fromPath('upload_file', filePath),
    );

    final response = await request.send();

    final responseSessionId = response.headers['x-session-id'];
    if (responseSessionId != null && responseSessionId.isNotEmpty) {
      ApiService.sessionId = responseSessionId;
    }

    final responseBody = await response.stream.bytesToString();
    if (response.statusCode != 200) {
      throw Exception('API error');
    }

    final data = jsonDecode(responseBody) as Map<String, dynamic>;
    return data['translated_text'] as String;
  }

  Future<void> _pickAndTranslateFile() async {
    final picked = await FilePicker.platform.pickFiles(withData: false);
    if (picked == null || picked.files.isEmpty || picked.files.single.path == null) {
      return;
    }

    final filePath = picked.files.single.path!;
    setState(() {
      _selectedFilePath = filePath;
      _isLoading = true;
      _errorMessage = '';
    });

    try {
      final translatedText = await translateFile(filePath);
      if (!mounted) return;
      setState(() {
        _resultText = translatedText;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _errorMessage = 'File translation failed.';
      });
    } finally {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      key: const ValueKey<String>('file_translation_view'),
      width: double.infinity,
      height: double.infinity,
      color: isDark ? const Color(0xFF08050F) : const Color(0xFFF9EEFF),
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
          const SizedBox(height: 40),
          Expanded(
            child: Center(
              child: Card(
                child: SizedBox(
                  width: 980,
                  height: 420,
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'File Translation',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 16),
                        ElevatedButton(
                          onPressed: _isLoading ? null : _pickAndTranslateFile,
                          child: _isLoading
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Text('Choose file and translate'),
                        ),
                        if (_selectedFilePath.isNotEmpty) ...[
                          const SizedBox(height: 12),
                          Text('Selected: $_selectedFilePath'),
                        ],
                        if (_errorMessage.isNotEmpty) ...[
                          const SizedBox(height: 12),
                          Text(
                            _errorMessage,
                            style: const TextStyle(color: Colors.redAccent),
                          ),
                        ],
                        if (_resultText.isNotEmpty) ...[
                          const SizedBox(height: 12),
                          Expanded(
                            child: SingleChildScrollView(
                              child: Text(_resultText),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
