import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

class ApiService {
  static String? sessionId;

  // Base URL notes:
  // - Android emulator: http://10.0.2.2:8000
  // - Flutter web: http://127.0.0.1:8000
  // - Physical phone: use LAN IP (e.g. http://192.168.x.x:8000)
  // Current default:
  static const bool useLocalBackend = false; // Bật về false để chạy cloud

  static String get baseUrl {
    if (useLocalBackend) {
      if (kIsWeb) {
        final host = Uri.base.host;
        if (host.isNotEmpty && host != 'localhost') {
          return "http://$host:8000/api/v1";
        }
        return "http://127.0.0.1:8000/api/v1";
      }
      return "http://192.168.52.103:8000/api/v1";
    }
    
    // Production Railway Backend
    return "https://ai-translator-system-production.up.railway.app/api/v1";
  }

  static Future<void> translateTextStream({
    required String text,
    required String sourceLang,
    required String targetLang,
    String? domain,
    required void Function(String chunk) onProgress,
  }) async {
    try {
      final uri = Uri.parse('$baseUrl/translate');
      final request = http.Request('POST', uri);

      request.headers['Content-Type'] = 'application/json';
      if (sessionId != null) {
        request.headers['X-Session-ID'] = sessionId!;
      }

      final bodyData = {
        'text': text,
        'source_lang': sourceLang,
        'target_lang': targetLang,
      };
      if (domain != null) {
        bodyData['domain'] = domain.toLowerCase();
      }
      
      request.body = jsonEncode(bodyData);

      final streamedResponse = await request.send().timeout(const Duration(seconds: 30));

      final responseSessionId = streamedResponse.headers['x-session-id'];
      if (responseSessionId != null && responseSessionId.isNotEmpty) {
        sessionId = responseSessionId;
      }

      if (streamedResponse.statusCode != 200) {
        final bodyStr = await streamedResponse.stream.bytesToString();
        throw Exception('API error: ${streamedResponse.statusCode} - $bodyStr');
      }

      String buffer = '';
      await for (final value in streamedResponse.stream.transform(utf8.decoder)) {
        buffer += value;
        // Split by \n\n to get complete SSE events
        final events = buffer.split('\n\n');
        
        // Keep the last part in buffer if it's incomplete
        if (!buffer.endsWith('\n\n')) {
          buffer = events.removeLast();
        } else {
          buffer = '';
        }

        for (var event in events) {
          final lines = event.split('\n');
          for (var line in lines) {
            if (line.startsWith('data: ')) {
              final jsonStr = line.substring(6).trim();
              if (jsonStr.isEmpty) continue;
              try {
                final data = jsonDecode(jsonStr);
                if (data['error'] != null) {
                  throw Exception(data['error']);
                }
                if (data['chunk'] != null) {
                  onProgress(data['chunk'] as String);
                }
              } catch (e) {
                debugPrint('Error parsing SSE json: $e, line: $jsonStr');
              }
            }
          }
        }
      }
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

      final streamedResponse = await request.send().timeout(const Duration(seconds: 60));
      final response = await http.Response.fromStream(streamedResponse);

      debugPrint('translateFile statusCode: ${response.statusCode}');

      final responseSessionId = response.headers['x-session-id'];
      if (responseSessionId != null && responseSessionId.isNotEmpty) {
        sessionId = responseSessionId;
      }

      if (response.statusCode != 200) {
        final errorBody = utf8.decode(response.bodyBytes);
        throw Exception('File translation failed: ${response.statusCode} - $errorBody');
      }

      final utf8Body = utf8.decode(response.bodyBytes);
      final Map<String, dynamic> data = jsonDecode(utf8Body) as Map<String, dynamic>;
      return data;
    } catch (e) {
      if (e.toString().contains('Failed host lookup') || e.toString().contains('XMLHttpRequest')) {
        throw Exception('Lỗi kết nối máy chủ (CORS hoặc Server chưa bật). Chi tiết: $e');
      }
      rethrow;
    }
  }

  static Future<Map<String, dynamic>> checkFileStatus(int fileId) async {
    try {
      final uri = Uri.parse('$baseUrl/file/translate/$fileId/status');
      final headers = <String, String>{};
      if (sessionId != null) {
        headers['X-Session-ID'] = sessionId!;
      }

      final response = await http.get(uri, headers: headers).timeout(const Duration(seconds: 15));
      if (response.statusCode != 200) {
        final errorBody = utf8.decode(response.bodyBytes);
        throw Exception('Check status failed: ${response.statusCode} - $errorBody');
      }
      final utf8Body = utf8.decode(response.bodyBytes);
      return jsonDecode(utf8Body) as Map<String, dynamic>;
    } catch (e) {
      rethrow;
    }
  }
}
