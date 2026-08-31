import os

filepath = "custom-addons/generate_bons/controllers/whatsapp_bon_api.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "new_qte = art['qte'] * ratio",
    "new_qte = int(round(art['qte'] * ratio))"
)

content = content.replace(
    "'qte': art['qte'],",
    "'qte': int(round(art['qte'])),"
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("python code updated")
