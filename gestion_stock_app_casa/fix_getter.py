import sys
import re

with open("lib/screens/stock_consultation_screen.dart", "r", encoding="utf-8") as f:
    content = f.read()

pattern = r"  double get _totalQuantity \{\n    return _filteredStock\.fold\(0\.0, \(sum, item\) => sum \+ item\.quantity\);\n  \}"
replacement = """  double get _totalQuantity {
    return _filteredStock.fold(0.0, (sum, item) => sum + item.quantity);
  }
  
  double get _totalQuantitySellable {
    return _filteredStock.fold(0.0, (sum, item) => sum + item.quantitySellable);
  }"""

content = re.sub(pattern, replacement, content)

with open("lib/screens/stock_consultation_screen.dart", "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed getter")
