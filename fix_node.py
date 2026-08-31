import os

filepath = "whatsapp_bridge/index.js"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    'apiUrl = GENERATE_BONS_ODOO_URL;',
    'targetOdooUrl = GENERATE_BONS_ODOO_URL;\n                isClientRequest = false;'
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("index.js fixed successfully.")
