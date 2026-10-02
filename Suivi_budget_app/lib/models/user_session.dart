class UserSession {
  final int id;
  final String name;
  final String login;
  final String? serverUrl;

  UserSession({
    required this.id,
    required this.name,
    required this.login,
    this.serverUrl,
  });

  factory UserSession.fromJson(Map<String, dynamic> json) {
    return UserSession(
      id: json['id'] is int ? json['id'] : int.tryParse(json['id'].toString()) ?? 0,
      name: json['name'] ?? '',
      login: json['login'] ?? '',
      serverUrl: json['serverUrl'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'login': login,
      'serverUrl': serverUrl,
    };
  }
}
