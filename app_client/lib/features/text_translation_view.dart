import 'package:flutter/material.dart';

import '../services/api_service.dart';
import '../widgets/domain_selector.dart';
import '../widgets/translation_bottom_note.dart';
import '../widgets/translation_dual_panel.dart';
import '../widgets/translation_top_bar.dart';

class TextTranslationView extends StatefulWidget {
  const TextTranslationView({
    super.key,
    required this.isDarkMode,
    required this.onToggleTheme,
    required this.onSwitchToFile,
  });

  final bool isDarkMode;
  final VoidCallback onToggleTheme;
  final VoidCallback onSwitchToFile;

  @override
  State<TextTranslationView> createState() => _TextTranslationViewState();
}

class _TextTranslationViewState extends State<TextTranslationView> {
  final TextEditingController _inputController = TextEditingController();
  bool _isLoading = false;
  String _outputText = '';
  String _errorMessage = '';
  String _selectedSourceLang = 'en';
  String _selectedTargetLang = 'vi';

  @override
  void dispose() {
    _inputController.dispose();
    super.dispose();
  }

  Future<void> _handleTranslate() async {
    final inputText = _inputController.text.trim();
    if (inputText.isEmpty) {
      setState(() {
        _errorMessage = 'Please enter text to translate';
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    try {
      final result = await ApiService.translateText(
        text: inputText,
        sourceLang: _selectedSourceLang,
        targetLang: _selectedTargetLang,
      );
      if (!mounted) return;
      setState(() {
        _outputText = result;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _errorMessage = 'Translation failed. Please try again.';
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

    return LayoutBuilder(
      builder: (context, constraints) {
        final base = (constraints.maxWidth / 1600).clamp(0.72, 1.0);
        return Container(
          key: const ValueKey<String>('text_translation_view'),
          width: double.infinity,
          height: double.infinity,
          color: isDark ? const Color(0xFF020204) : const Color(0xFFF4E9F8),
          padding: EdgeInsets.symmetric(
            horizontal: 42 * base,
            vertical: 24 * base,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TranslationTopBar(
                scale: base,
                pageTitle: 'File Translation',
                onPagePressed: widget.onSwitchToFile,
                isDarkMode: widget.isDarkMode,
                onToggleTheme: widget.onToggleTheme,
              ),
              SizedBox(height: 64 * base),
              DomainSelector(scale: base),
              SizedBox(height: 46 * base),
              Expanded(child: Center(child: TranslationDualPanel(scale: base))),
              SizedBox(height: 20 * base),
              TextField(
                controller: _inputController,
                minLines: 1,
                maxLines: 3,
                decoration: InputDecoration(
                  hintText: 'Enter text to translate',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12 * base)),
                ),
              ),
              SizedBox(height: 12 * base),
              Row(
                children: [
                  DropdownButton<String>(
                    value: _selectedSourceLang,
                    items: const [
                      DropdownMenuItem(value: 'en', child: Text('EN')),
                      DropdownMenuItem(value: 'vi', child: Text('VI')),
                    ],
                    onChanged: (value) {
                      if (value == null) return;
                      setState(() {
                        _selectedSourceLang = value;
                      });
                    },
                  ),
                  SizedBox(width: 12 * base),
                  DropdownButton<String>(
                    value: _selectedTargetLang,
                    items: const [
                      DropdownMenuItem(value: 'vi', child: Text('VI')),
                      DropdownMenuItem(value: 'en', child: Text('EN')),
                    ],
                    onChanged: (value) {
                      if (value == null) return;
                      setState(() {
                        _selectedTargetLang = value;
                      });
                    },
                  ),
                  SizedBox(width: 16 * base),
                  ElevatedButton(
                    onPressed: _isLoading ? null : _handleTranslate,
                    child: _isLoading
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Translate'),
                  ),
                ],
              ),
              if (_errorMessage.isNotEmpty) ...[
                SizedBox(height: 8 * base),
                Text(
                  _errorMessage,
                  style: const TextStyle(color: Colors.redAccent),
                ),
              ],
              if (_outputText.isNotEmpty) ...[
                SizedBox(height: 8 * base),
                Text('Result: $_outputText'),
              ],
              TranslationBottomNote(scale: base),
            ],
          ),
        );
      },
    );
  }
}
