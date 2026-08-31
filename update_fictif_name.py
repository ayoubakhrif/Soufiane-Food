import os

filepath = "custom-addons/generate_bons/controllers/whatsapp_bon_api.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "'company_id': company.id,\n                    'date': date_val,\n                    'line_ids': bon_lines_fictif",
    "'company_id': company.id,\n                    'date': date_val,\n                    'name': bon_reel.name,\n                    'line_ids': bon_lines_fictif"
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("python updated")
