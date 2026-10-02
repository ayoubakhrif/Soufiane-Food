class CategoryModel {
  final int id;
  final String name;
  final double limit;
  final double spent;
  final double remaining;
  final double percentage;
  final bool hasObjective;
  final bool isExceeded;

  CategoryModel({
    required this.id,
    required this.name,
    this.limit = 0.0,
    this.spent = 0.0,
    this.remaining = 0.0,
    this.percentage = 0.0,
    this.hasObjective = false,
    this.isExceeded = false,
  });

  factory CategoryModel.fromJson(Map<String, dynamic> json) {
    return CategoryModel(
      id: json['id'] is int ? json['id'] : int.tryParse(json['id'].toString()) ?? 0,
      name: json['name'] ?? '',
      limit: (json['limit'] is num) ? (json['limit'] as num).toDouble() : 0.0,
      spent: (json['spent'] is num) ? (json['spent'] as num).toDouble() : 0.0,
      remaining: (json['remaining'] is num) ? (json['remaining'] as num).toDouble() : 0.0,
      percentage: (json['percentage'] is num) ? (json['percentage'] as num).toDouble() : 0.0,
      hasObjective: json['has_objective'] == true,
      isExceeded: json['is_exceeded'] == true,
    );
  }
}
