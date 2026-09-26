import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../models/agent.dart';
import '../models/pending_operation.dart';

// Stockage universel Web / Mobile / Desktop
class LocalStorageService {
  static Agent? _currentAgent;
  static Agent? get currentAgent => _currentAgent;
  static final List<PendingOperation> _inMemoryQueue = [];

  static Future<void> saveAgentSession(Agent agent) async {
    _currentAgent = agent;
  }

  static Future<Agent?> getAgentSession() async {
    return _currentAgent;
  }

  static Future<void> clearSession() async {
    _currentAgent = null;
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
