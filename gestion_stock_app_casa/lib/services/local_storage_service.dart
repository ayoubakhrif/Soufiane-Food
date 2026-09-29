import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/agent.dart';
import '../models/pending_operation.dart';

// Stockage universel Web / Mobile / Desktop
class LocalStorageService {
  static Agent? _currentAgent;
  static Agent? get currentAgent => _currentAgent;
  static final List<PendingOperation> _inMemoryQueue = [];

  static Future<void> saveAgentSession(Agent agent) async {
    _currentAgent = agent;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('agent_session', jsonEncode(agent.toJson()));
    } catch (e) {
      debugPrint('Error saving session: $e');
    }
  }

  static Future<Agent?> getAgentSession() async {
    if (_currentAgent != null) return _currentAgent;
    try {
      final prefs = await SharedPreferences.getInstance();
      final String? agentStr = prefs.getString('agent_session');
      if (agentStr != null) {
        _currentAgent = Agent.fromJson(jsonDecode(agentStr));
        return _currentAgent;
      }
    } catch (e) {
      debugPrint('Error loading session: $e');
    }
    return null;
  }

  static Future<void> clearSession() async {
    _currentAgent = null;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('agent_session');
    } catch (e) {
      debugPrint('Error clearing session: $e');
    }
  }

  static Future<List<PendingOperation>> getPendingOperations() async {
    return List.unmodifiable(_inMemoryQueue);
  }

  static Future<void> savePendingOperation(PendingOperation op) async {
    _inMemoryQueue.add(op);
  }

  static Future<void> removePendingOperation(String id) async {
    _inMemoryQueue.removeWhere((item) => item.id == id);
  }
}
