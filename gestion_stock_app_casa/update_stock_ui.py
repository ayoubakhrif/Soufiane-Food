import sys
import re

with open("lib/screens/stock_consultation_screen.dart", "r", encoding="utf-8") as f:
    content = f.read()

# Top summary
content = content.replace("double _totalQuantity = 0;", "double _totalQuantity = 0;\n  double _totalQuantitySellable = 0;")
content = content.replace("_totalQuantity = _filteredStock.fold(0, (sum, item) => sum + item.quantity);", "_totalQuantity = _filteredStock.fold(0, (sum, item) => sum + item.quantity);\n    _totalQuantitySellable = _filteredStock.fold(0, (sum, item) => sum + item.quantitySellable);")
content = content.replace(
    "const Text('Total UnitÃ©s', style: TextStyle(color: Colors.black54, fontSize: 12)),\n                    Text(\n                      _totalQuantity.toStringAsFixed(0),\n                      style: TextStyle(color: Colors.blue.shade900, fontWeight: FontWeight.bold, fontSize: 16),\n                    ),",
    "const Text('Physique / Vendable', style: TextStyle(color: Colors.black54, fontSize: 12)),\n                    Text(\n                      '${_totalQuantity.toStringAsFixed(0)} / ${_totalQuantitySellable.toStringAsFixed(0)}',\n                      style: TextStyle(color: Colors.blue.shade900, fontWeight: FontWeight.bold, fontSize: 16),\n                    ),"
)

# Row details
old_row = """                                        const Divider(height: 16),
                                        Row(
                                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                          children: [
                                            Column(
                                              crossAxisAlignment: CrossAxisAlignment.start,
                                              children: [
                                                const Text('UnitÃ©s', style: TextStyle(fontSize: 11, color: Colors.black54)),
                                                Text(
                                                  stock.quantity.toStringAsFixed(0),
                                                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                                                ),
                                              ],
                                            ),"""
new_row = """                                        const Divider(height: 16),
                                        Row(
                                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                          children: [
                                            Column(
                                              crossAxisAlignment: CrossAxisAlignment.start,
                                              children: [
                                                const Text('Physique', style: TextStyle(fontSize: 11, color: Colors.black54)),
                                                Text(
                                                  stock.quantity.toStringAsFixed(0),
                                                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                                                ),
                                              ],
                                            ),
                                            Column(
                                              crossAxisAlignment: CrossAxisAlignment.start,
                                              children: [
                                                const Text('Vendable', style: TextStyle(fontSize: 11, color: Colors.black54)),
                                                Text(
                                                  stock.quantitySellable.toStringAsFixed(0),
                                                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Colors.blue),
                                                ),
                                              ],
                                            ),"""
content = content.replace(old_row, new_row)

with open("lib/screens/stock_consultation_screen.dart", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated UI")
