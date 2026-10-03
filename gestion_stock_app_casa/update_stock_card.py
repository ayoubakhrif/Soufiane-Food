import sys

with open("lib/models/stock_card.dart", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("final double quantity;", "final double quantity;\n  final double quantitySellable;")
content = content.replace("required this.quantity,", "required this.quantity,\n    required this.quantitySellable,")
content = content.replace(
    "quantity: (json['quantity'] is num) ? (json['quantity'] as num).toDouble() : 0.0,",
    "quantity: (json['quantity'] is num) ? (json['quantity'] as num).toDouble() : 0.0,\n      quantitySellable: (json['quantity_sellable'] is num) ? (json['quantity_sellable'] as num).toDouble() : ((json['quantity'] is num) ? (json['quantity'] as num).toDouble() : 0.0),"
)

with open("lib/models/stock_card.dart", "w", encoding="utf-8") as f:
    f.write(content)
