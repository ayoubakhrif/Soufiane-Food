class Agent {
  final int id;
  final String name;
  final String phone;
  final String role; // 'agent' or 'driver'

  Agent({
    required this.id,
    required this.name,
    required this.phone,
    this.role = 'agent',
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
