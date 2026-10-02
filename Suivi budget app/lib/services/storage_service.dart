import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/user_session.dart';

class StorageService {
  static const String _keySession = 'user_session';
  static const String _keyServerUrl = 'server_url';
  static const String defaultServerUrl = 'https://gestia-soufianefoods.cloud';

  static Future<void> saveSession(UserSession session) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keySession, jsonEncode(session.toJson()));
  }

  static Future<UserSession?> getSession() async {
    final prefs = await SharedPreferences.getInstance();
    final data = prefs.getString(_keySession);
    if (data == null || data.isEmpty) return null;
    try {
      final json = jsonDecode(data);
      return UserSession.fromJson(json);
    } catch (_) {
      return null;
    }
  }

  static Future<void> clearSession() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_keySession);
  }

  static Future<void> saveServerUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyServerUrl, url);
  }

  static Future<String> getServerUrl() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyServerUrl) ?? defaultServerUrl;
  }
}
