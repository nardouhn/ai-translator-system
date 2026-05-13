import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'package:crypto/crypto.dart';

class LocalCacheService {
  static String _generateKey(String sourceText, String targetLang, String domain) {
    final bytes = utf8.encode("${sourceText.trim()}_${targetLang}_${domain.toLowerCase()}");
    final digest = md5.convert(bytes);
    return 'trans_${digest.toString()}';
  }

  static Future<void> saveTranslation(String sourceText, String targetLang, String domain, String translatedText) async {
    final prefs = await SharedPreferences.getInstance();
    final key = _generateKey(sourceText, targetLang, domain);
    await prefs.setString(key, translatedText);
  }

  static Future<String?> getTranslation(String sourceText, String targetLang, String domain) async {
    final prefs = await SharedPreferences.getInstance();
    final key = _generateKey(sourceText, targetLang, domain);
    return prefs.getString(key);
  }
}
