import sys
import re

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "r", encoding="utf-8") as f:
    content = f.read()

pattern = r"('returned_qty': returned_qty,\n\s*'state': rec\.state,)"
replacement = r"\1\n                    'driver_name': rec.driver_id.name if rec.driver_id else 'Pas de chauffeur',"

content = re.sub(pattern, replacement, content)

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated api_exits with driver_name")
