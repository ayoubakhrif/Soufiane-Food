class ExpenseModel {
  final int id;
  final String date;
  final double amount;
  final int categoryId;
  final String categoryName;
  final String description;
  final bool hasReceipt;

  ExpenseModel({
    required this.id,
    required this.date,
    required this.amount,
    required this.categoryId,
    required this.categoryName,
    required this.description,
    required this.hasReceipt,
  });

  factory ExpenseModel.fromJson(Map<String, dynamic> json) {
    return ExpenseModel(
      id: json['id'] is int ? json['id'] : int.tryParse(json['id'].toString()) ?? 0,
      date: json['date']?.toString() ?? '',
      amount: (json['amount'] is num) ? (json['amount'] as num).toDouble() : 0.0,
      categoryId: json['category_id'] is int ? json['category_id'] : int.tryParse(json['category_id'].toString()) ?? 0,
      categoryName: json['category_name']?.toString() ?? 'Général',
      description: json['description']?.toString() ?? '',
      hasReceipt: json['has_receipt'] == true,
    );
  }
}
