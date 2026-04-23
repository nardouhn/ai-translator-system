import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_tts/flutter_tts.dart';

import '../services/api_service.dart';
import '../widgets/domain_dropdown.dart';
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
  String _selectedDomain = 'General';
  
  final FlutterTts flutterTts = FlutterTts();
  bool _isSpeakingSource = false;
  bool _isSpeakingTarget = false;

  @override
  void initState() {
    super.initState();
    _initTts();
  }

  void _initTts() {
    flutterTts.setCompletionHandler(() {
      if (mounted) {
        setState(() {
          _isSpeakingSource = false;
          _isSpeakingTarget = false;
        });
      }
    });
  }

  Future<void> _handleSpeakSource() async {
    final text = _inputController.text;
    if (text.isEmpty) return;

    if (_isSpeakingSource) {
      await flutterTts.stop();
      setState(() => _isSpeakingSource = false);
      return;
    }

    await flutterTts.stop();
    setState(() {
      _isSpeakingSource = true;
      _isSpeakingTarget = false;
    });

    String voiceLang = _selectedSourceLang == 'vi' ? 'vi-VN' : 'en-US';
    await flutterTts.setLanguage(voiceLang);
    await flutterTts.speak(text);
  }

  Future<void> _handleSpeakTarget() async {
    if (_outputText.isEmpty) return;

    if (_isSpeakingTarget) {
      await flutterTts.stop();
      setState(() => _isSpeakingTarget = false);
      return;
    }

    await flutterTts.stop();
    setState(() {
      _isSpeakingSource = false;
      _isSpeakingTarget = true;
    });

    String voiceLang = _selectedTargetLang == 'vi' ? 'vi-VN' : 'en-US';
    await flutterTts.setLanguage(voiceLang);
    await flutterTts.speak(_outputText);
  }

  void _handleCopy() {
    if (_outputText.isNotEmpty) {
      Clipboard.setData(ClipboardData(text: _outputText));
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Copied to clipboard!')),
      );
    }
  }

  @override
  void dispose() {
    flutterTts.stop();
    _inputController.dispose();
    super.dispose();
  }

  Future<void> _handleTranslate() async {
    final inputText = _inputController.text; // Không dùng trim()
    if (inputText.isEmpty) {
      setState(() {
        _errorMessage = 'Please enter text to translate';
      });
      return;
    }

    if (inputText.length > 5000) {
      setState(() {
        _errorMessage = 'Text exceeds 5000 characters limit';
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
        domain: _selectedDomain, // Try to pass domain if API supports it
      );
      if (!mounted) return;
      setState(() {
        _outputText = result;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = 'Translation failed. Please try again.';
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Lỗi hệ thống: $e'),
          backgroundColor: Colors.redAccent,
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
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
              DomainDropdown(
                scale: base,
                selectedDomain: _selectedDomain,
                onDomainChanged: (newValue) {
                  setState(() {
                    _selectedDomain = newValue;
                  });
                },
              ),
              SizedBox(height: 46 * base),
              Expanded(
                child: Center(
                  child: TranslationDualPanel(
                    scale: base,
                    inputController: _inputController,
                    outputText: _outputText,
                    sourceLangName: _selectedSourceLang == 'en' ? 'English' : 'Vietnamese',
                    targetLangName: _selectedTargetLang == 'en' ? 'English' : 'Vietnamese',
                    onTranslate: _handleTranslate,
                    onCopy: _handleCopy,
                    onSpeakSource: _handleSpeakSource,
                    onSpeakTarget: _handleSpeakTarget,
                    isSpeakingSource: _isSpeakingSource,
                    isSpeakingTarget: _isSpeakingTarget,
                    isLoading: _isLoading,
                  ),
                ),
              ),
              if (_errorMessage.isNotEmpty) ...[
                SizedBox(height: 8 * base),
                Text(
                  _errorMessage,
                  style: const TextStyle(color: Colors.redAccent),
                ),
              ],
              TranslationBottomNote(scale: base),
            ],
          ),
        );
      },
    );
  }
}
