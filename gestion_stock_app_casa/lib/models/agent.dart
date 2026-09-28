class Agent {
  final int id;
  final String name;
  final String phone;
  final String role;

  Agent({
    required this.id,
    required this.name,
    required this.phone,
    required this.role,
  });

  factory Agent.fromJson(Map<String, dynamic> json) {
    return Agent(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      phone: json['phone'] as String? ?? '',
      role: json['role'] as String? ?? 'agent',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'phone': phone,
    'role': role,
  };
}
