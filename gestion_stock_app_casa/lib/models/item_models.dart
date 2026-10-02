class ProductItem {
  final int id;
  final String name;

  ProductItem({required this.id, required this.name});

  factory ProductItem.fromJson(Map<String, dynamic> json) {
    return ProductItem(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
    );
  }
}

class ClientItem {
  final int id;
  final String name;

  ClientItem({required this.id, required this.name});

  factory ClientItem.fromJson(Map<String, dynamic> json) {
    return ClientItem(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
    );
  }
}

class GarageItem {
  final String key;
  final String label;

  GarageItem({required this.key, required this.label});

  factory GarageItem.fromJson(Map<String, dynamic> json) {
    return GarageItem(
      key: json['key'] as String? ?? '',
      label: json['label'] as String? ?? '',
    );
  }
}

class DriverItem {
  final int id;
  final String name;

  DriverItem({required this.id, required this.name});

  factory DriverItem.fromJson(Map<String, dynamic> json) {
    return DriverItem(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
    );
  }
}

class OrderLine {
  final int? productId;
  final String productName;
  final double quantity;
  final double weight;
  final double tonnage;
  final String note;

  OrderLine({
    this.productId,
    required this.productName,
    required this.quantity,
    required this.weight,
    required this.tonnage,
    required this.note,
  });

  factory OrderLine.fromJson(Map<String, dynamic> json) {
    return OrderLine(
      productId: json['product_id'] as int?,
      productName: json['product_name'] as String? ?? '',
      quantity: (json['quantity'] is num) ? (json['quantity'] as num).toDouble() : 0.0,
      weight: (json['weight'] is num) ? (json['weight'] as num).toDouble() : 0.0,
      tonnage: (json['tonnage'] is num) ? (json['tonnage'] as num).toDouble() : 0.0,
      note: json['note'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'product_id': productId,
    'quantity': quantity,
    'weight': weight,
    'note': note,
  };
}

class Order {
  final int id;
  final String name;
  final String date;
  final String commercialName;
  final String clientName;
  final List<OrderLine> lines;

  Order({
    required this.id,
    required this.name,
    required this.date,
    required this.commercialName,
    required this.clientName,
    required this.lines,
  });

  factory Order.fromJson(Map<String, dynamic> json) {
    var list = json['lines'] as List? ?? [];
    List<OrderLine> linesList = list.map((i) => OrderLine.fromJson(i)).toList();
    
    return Order(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      date: json['date'] as String? ?? '',
      commercialName: json['commercial_name'] as String? ?? '',
      clientName: json['client_name'] as String? ?? '',
      lines: linesList,
    );
  }
}
