import sys
import re

with open("custom-addons/stock_casa_field/models/casa_field_stock_stock_stock.py", "r", encoding="utf-8") as f:
    content = f.read()

pattern = r"quantity = fields\.Float\(string='Quantit.*?readonly=True\)"
replacement = "quantity = fields.Float(string='Quantité (Physique)', readonly=True)\n    quantity_sellable = fields.Float(string='Quantité (Vendable)', readonly=True)"

content = re.sub(pattern, replacement, content)

with open("custom-addons/stock_casa_field/models/casa_field_stock_stock_stock.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated stock model fields")
