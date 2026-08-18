import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/controllers/whatsapp_pdf_bot_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_bl_rule = """   - Le BL (Bill of Lading, Connaissement maritime, ex: YMJAM450339005). Cherchez "BL", "B/L", ou une longue référence alphanumérique liée au navire/conteneur. S'il n'y en a pas, mettez une chaine vide ""."""

new_bl_rule = """   - Le BL (Bill of Lading). Cherchez EXACTEMENT les mentions "BL", "B/L", "B/L No" ou "Connaissement". NE PRENEZ JAMAIS la référence de "Voyage" ou de "Booking". S'il n'y a pas de mention claire de BL ou de Connaissement, mettez une chaine vide ""."""

content = content.replace(old_bl_rule, new_bl_rule)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated whatsapp_pdf_bot_api.py BL rules")
