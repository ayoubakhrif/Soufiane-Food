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
