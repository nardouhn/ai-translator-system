import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  static String? sessionId;

  // Base URL notes:
  // - Android emulator: http://10.0.2.2:8000
  // - Flutter web: http://127.0.0.1:8000
  // - Physical phone: use LAN IP (e.g. http://192.168.x.x:8000)
  // Current default for Android emulator:
  static const String baseUrl = "http://10.0.2.2:8000/api/v1";

  static Future<String> translateText({
    required String text,
    required String sourceLang,
    required String targetLang,
  }) async {
    final headers = <String, String>{
      'Content-Type': 'application/json',
    };

    if (sessionId != null) {
      headers['X-Session-ID'] = sessionId!;
    }

    final response = await http.post(
      Uri.parse('$baseUrl/translate'),
      headers: headers,
      body: jsonEncode({
        'text': text,
        'source_lang': sourceLang,
        'target_lang': targetLang,
      }),
    );

    print('translate statusCode: ${response.statusCode}');
    print('translate body: ${response.body}');

    final responseSessionId = response.headers['x-session-id'];
    if (responseSessionId != null && responseSessionId.isNotEmpty) {
      sessionId = responseSessionId;
    }

    if (response.statusCode != 200) {
      throw Exception('API error: ${response.statusCode}');
    }

    final Map<String, dynamic> data = jsonDecode(response.body) as Map<String, dynamic>;
    return data['translated_text'] as String;
  }
}
