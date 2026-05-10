import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'package:crypto/crypto.dart';

class LocalCacheService {
  static String _generateKey(String sourceText, String targetLang) {
    final bytes = utf8.encode("${sourceText.trim()}_$targetLang");
    final digest = md5.convert(bytes);
    return 'trans_${digest.toString()}';
  }

  static Future<void> saveTranslation(String sourceText, String targetLang, String translatedText) async {
    final prefs = await SharedPreferences.getInstance();
    final key = _generateKey(sourceText, targetLang);
    await prefs.setString(key, translatedText);
  }

  static Future<String?> getTranslation(String sourceText, String targetLang) async {
    final prefs = await SharedPreferences.getInstance();
    final key = _generateKey(sourceText, targetLang);
    return prefs.getString(key);
  }
}
