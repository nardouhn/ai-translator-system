import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;

class ApiService {
  static String? sessionId;

  // Base URL notes:
  // - Android emulator: http://10.0.2.2:8000
  // - Flutter web: http://127.0.0.1:8000
  // - Physical phone: use LAN IP (e.g. http://192.168.x.x:8000)
  // Current default:
  static String get baseUrl {
    if (kIsWeb) {
      final host = Uri.base.host;
      if (host.isNotEmpty && host != 'localhost') {
        return "http://$host:8000/api/v1";
      }
      return "http://127.0.0.1:8000/api/v1";
    }
    return "http://10.0.2.2:8000/api/v1";
  }

  static Future<String> translateText({
    required String text,
    required String sourceLang,
    required String targetLang,
    String? domain,
  }) async {
    try {
      final headers = <String, String>{
        'Content-Type': 'application/json',
      };

      if (sessionId != null) {
        headers['X-Session-ID'] = sessionId!;
      }

      final bodyData = {
        'text': text,
        'source_lang': sourceLang,
        'target_lang': targetLang,
      };
      if (domain != null) {
        bodyData['domain'] = domain.toLowerCase();
      }

      final response = await http.post(
        Uri.parse('$baseUrl/translate'),
        headers: headers,
        body: jsonEncode(bodyData),
      );

      debugPrint('translate statusCode: ${response.statusCode}');
      debugPrint('translate body: ${response.body}');

      final responseSessionId = response.headers['x-session-id'];
      if (responseSessionId != null && responseSessionId.isNotEmpty) {
        sessionId = responseSessionId;
      }

      if (response.statusCode != 200) {
        throw Exception('API error: ${response.statusCode} - ${response.body}');
      }

      final Map<String, dynamic> data = jsonDecode(response.body) as Map<String, dynamic>;
      return data['translated_text'] as String;
    } catch (e) {
      if (e.toString().contains('Failed host lookup') || e.toString().contains('XMLHttpRequest')) {
        throw Exception('Lỗi kết nối máy chủ (CORS hoặc Server chưa bật). Chi tiết: $e');
      }
      rethrow;
    }
  }

  static Future<Map<String, dynamic>> translateFile({
    String? filePath,
    Uint8List? fileBytes,
    String? fileName,
    required String sourceLang,
    required String targetLang,
    required String domain,
  }) async {
    try {
      final uri = Uri.parse('$baseUrl/file/translate');
      final request = http.MultipartRequest('POST', uri);

      if (sessionId != null) {
        request.headers['X-Session-ID'] = sessionId!;
      }

      request.fields['source_lang'] = sourceLang;
      request.fields['target_lang'] = targetLang;
      request.fields['domain'] = domain.toLowerCase();

      if (kIsWeb) {
        if (fileBytes == null) {
          throw Exception('Lỗi: Không đọc được dữ liệu file trên Web');
        }
        if (fileName == null) {
          throw Exception('Lỗi: Thiếu tên file trên Web');
        }
        request.files.add(http.MultipartFile.fromBytes(
          'upload_file',
          fileBytes,
          filename: fileName,
        ));
      } else if (filePath != null) {
        request.files.add(await http.MultipartFile.fromPath('upload_file', filePath));
      } else {
        throw Exception('Either fileBytes or filePath must be provided');
      }

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      debugPrint('translateFile statusCode: ${response.statusCode}');

      final responseSessionId = response.headers['x-session-id'];
      if (responseSessionId != null && responseSessionId.isNotEmpty) {
        sessionId = responseSessionId;
      }

      if (response.statusCode != 200) {
        throw Exception('File translation failed: ${response.statusCode} - ${response.body}');
      }

      final Map<String, dynamic> data = jsonDecode(response.body) as Map<String, dynamic>;
      return data;
    } catch (e) {
      if (e.toString().contains('Failed host lookup') || e.toString().contains('XMLHttpRequest')) {
        throw Exception('Lỗi kết nối máy chủ (CORS hoặc Server chưa bật). Chi tiết: $e');
      }
      rethrow;
    }
  }
}
