import 'dart:convert';

class PendingOperation {
  final String id;
  final String type; // 'entry', 'exit', 'transfer'
  final Map<String, dynamic> data;
  final DateTime createdAt;

  PendingOperation({
    required this.id,
    required this.type,
    required this.data,
    required this.createdAt,
  });

  Map<String, dynamic> toJson() => {
    'id': id,
    'type': type,
    'data': data,
    'createdAt': createdAt.toIso8601String(),
  };

  factory PendingOperation.fromJson(Map<String, dynamic> json) {
    return PendingOperation(
      id: json['id'] as String,
      type: json['type'] as String,
      data: json['data'] is String 
          ? jsonDecode(json['data'] as String) as Map<String, dynamic>
          : json['data'] as Map<String, dynamic>,
      createdAt: DateTime.parse(json['createdAt'] as String),
    );
  }
}
