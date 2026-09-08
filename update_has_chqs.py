import os

filepath = 'custom-addons/finance_2/controllers/whatsapp_finance_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("has_chqs = bool(benif_with_ctx.physical_chq_ids)", "has_chqs = bool(benif_with_ctx.physical_chq_ids) or bool(benif_with_ctx.get_finance2_cheques())")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated has_chqs logic")
