import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

import '../services/api_service.dart';
import '../services/local_cache_service.dart';
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
  final String _selectedSourceLang = 'en';
  final String _selectedTargetLang = 'vi';
  String _selectedDomain = 'General';
  
  final FlutterTts flutterTts = FlutterTts();
  bool _isSpeakingSource = false;
  bool _isSpeakingTarget = false;

  final stt.SpeechToText _speech = stt.SpeechToText();
  bool _isListening = false;
  bool _speechAvailable = false;


  @override
  void initState() {
    super.initState();
    _initTts();
    _initSpeech();
    _inputController.addListener(_onInputChanged);
  }

  void _onInputChanged() {
    final text = _inputController.text;
    if (text.isEmpty) {
      setState(() {
        _outputText = '';
        _errorMessage = '';
      });
    }
  }

  void _initSpeech() async {
    _speechAvailable = await _speech.initialize(
      onStatus: (status) {
        if (mounted) {
          if (status == 'done' || status == 'notListening') {
            setState(() => _isListening = false);
          }
        }
      },
      onError: (errorNotification) {
        if (mounted) {
          setState(() => _isListening = false);
        }
      },
    );
    if (mounted) {
      setState(() {});
    }
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
    _speech.stop();
    _inputController.removeListener(_onInputChanged);
    _inputController.dispose();
    super.dispose();
  }

  void _handleMicPressed() async {
    if (_selectedSourceLang != 'en') {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Voice dictation is only available for English')),
      );
      return;
    }

    if (!_speechAvailable) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Speech recognition not available on this device/browser')),
      );
      return;
    }

    if (_isListening) {
      _speech.stop();
      setState(() => _isListening = false);
    } else {
      setState(() => _isListening = true);
      _speech.listen(
        onResult: (result) {
          setState(() {
            _inputController.text = result.recognizedWords;
          });
        },
        localeId: 'en_US',
      );
    }
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
      setState(() {
        _outputText = '';
      });
      
      final cachedResult = await LocalCacheService.getTranslation(inputText, _selectedTargetLang, _selectedDomain);
      if (cachedResult != null && cachedResult.isNotEmpty) {
        debugPrint("⚡ Đã tìm thấy trong Cache, không gọi API!");
        setState(() {
          _outputText = cachedResult;
        });
        return;
      }

      await ApiService.translateTextStream(
        text: inputText,
        sourceLang: _selectedSourceLang,
        targetLang: _selectedTargetLang,
        domain: _selectedDomain,
        onProgress: (chunk) {
          if (mounted) {
            setState(() {
              _outputText += chunk;
            });
          }
        },
      );
      
      if (_outputText.isNotEmpty) {
        await LocalCacheService.saveTranslation(inputText, _selectedTargetLang, _selectedDomain, _outputText);
      }
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
        final isMobile = constraints.maxWidth < 600;
        final base = isMobile ? 0.85 : (constraints.maxWidth / 1600).clamp(0.72, 1.0);
        
        return Container(
          key: const ValueKey<String>('text_translation_view'),
          width: double.infinity,
          height: double.infinity,
          color: isDark ? const Color(0xFF020204) : const Color(0xFFF4E9F8),
          padding: EdgeInsets.symmetric(
            horizontal: isMobile ? 16 : 42 * base,
            vertical: isMobile ? 16 : 24 * base,
          ),
          child: SingleChildScrollView(
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
                Center(
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
                    onMicPressed: _handleMicPressed,
                    isSpeakingSource: _isSpeakingSource,
                    isSpeakingTarget: _isSpeakingTarget,
                    isListening: _isListening,
                    isLoading: _isLoading,
                  ),
                ),
                if (_errorMessage.isNotEmpty) ...[
                  SizedBox(height: 8 * base),
                  Text(
                    _errorMessage,
                    style: const TextStyle(color: Colors.redAccent),
                  ),
                ],
                SizedBox(height: 24 * base),
                TranslationBottomNote(scale: base),
              ],
            ),
          ),
        );
      },
    );
  }
}
