class StockCard {
  final int id;
  final int? productId;
  final String productName;
  final String lot;
  final String dum;
  final String calibre;
  final double weight;
  final double quantity;
  final double quantitySellable;
    final String frigo;
  final int? steId;
  final String steName;
  final String imageBase64;

  StockCard({
    required this.id,
    this.productId,
    required this.productName,
    required this.lot,
    required this.dum,
    required this.calibre,
    required this.weight,
    required this.quantity,
    required this.quantitySellable,
    required this.frigo,
    this.steId,
    required this.steName,
    required this.imageBase64,
  });

  factory StockCard.fromJson(Map<String, dynamic> json) {
    return StockCard(
      id: json['id'] is int ? json['id'] : int.tryParse(json['id'].toString()) ?? 0,
      productId: json['product_id'] as int?,
      productName: json['product_name'] as String? ?? '',
      lot: json['lot'] as String? ?? '',
      dum: json['dum'] as String? ?? '',
      calibre: json['calibre'] as String? ?? '',
      weight: (json['weight'] is num) ? (json['weight'] as num).toDouble() : 0.0,
      quantity: (json['quantity'] is num) ? (json['quantity'] as num).toDouble() : 0.0,
      quantitySellable: (json['quantity_sellable'] is num) ? (json['quantity_sellable'] as num).toDouble() : ((json['quantity'] is num) ? (json['quantity'] as num).toDouble() : 0.0),
            frigo: json['frigo'] as String? ?? 'stock_casa',
      steId: json['ste_id'] as int?,
      steName: json['ste_name'] as String? ?? '',
      imageBase64: json['image'] as String? ?? '',
    );
  }
}
