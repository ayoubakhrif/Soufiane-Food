import os

filepath = "custom-addons/generate_bons/controllers/whatsapp_bon_api.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "'files': response_files",
    "'files': response_files,\n                'merge_pdfs': False"
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("api updated")
