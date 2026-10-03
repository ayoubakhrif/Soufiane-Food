import sys
import re

with open("lib/screens/stock_consultation_screen.dart", "r", encoding="utf-8") as f:
    content = f.read()

# Top summary
if "double _totalQuantitySellable = 0;" not in content:
    content = content.replace("double _totalQuantity = 0;", "double _totalQuantity = 0;\n  double _totalQuantitySellable = 0;")
    content = content.replace("_totalQuantity = _filteredStock.fold(0, (sum, item) => sum + item.quantity);", "_totalQuantity = _filteredStock.fold(0, (sum, item) => sum + item.quantity);\n    _totalQuantitySellable = _filteredStock.fold(0, (sum, item) => sum + item.quantitySellable);")

    # Replace Total Unités with regex
    content = re.sub(
        r"const Text\('Total Unit.*?s', style: TextStyle\(color: Colors\.black54, fontSize: 12\)\),\s*Text\(\s*_totalQuantity\.toStringAsFixed\(0\),\s*style: TextStyle\(color: Colors\.blue\.shade900, fontWeight: FontWeight\.bold, fontSize: 16\),\s*\),",
        "const Text('Physique / Vendable', style: TextStyle(color: Colors.black54, fontSize: 12)),\n                    Text(\n                      '${_totalQuantity.toStringAsFixed(0)} / ${_totalQuantitySellable.toStringAsFixed(0)}',\n                      style: TextStyle(color: Colors.blue.shade900, fontWeight: FontWeight.bold, fontSize: 16),\n                    ),",
        content
    )

    # Replace Unités row with regex
    row_pattern = r"Column\(\s*crossAxisAlignment: CrossAxisAlignment\.start,\s*children: \[\s*const Text\('Unit.*?s', style: TextStyle\(fontSize: 11, color: Colors\.black54\)\),\s*Text\(\s*stock\.quantity\.toStringAsFixed\(0\),\s*style: const TextStyle\(fontWeight: FontWeight\.bold, fontSize: 15\),\s*\),\s*\],\s*\),"
    
    new_cols = """Column(
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
    
    content = re.sub(row_pattern, new_cols, content)

    with open("lib/screens/stock_consultation_screen.dart", "w", encoding="utf-8") as f:
        f.write(content)
    print("Fixed stock UI successfully")
else:
    print("Already fixed")
