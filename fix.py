with open('custom-addons/finance_2/controllers/whatsapp_finance_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

bad_str = """                week_match = re.match(r"^(?:w|s|semaine|week)\s*0*(\d{1,2})$", param)
                if week_match:
                    only_encaisse = bool(week_match.group(1))
            week_num = int(week_match.group(2))"""

good_str = """                week_match = re.match(r"^(?:w|s|semaine|week)\s*0*(\d{1,2})$", param)
                if week_match:
                    week_num = int(week_match.group(1))"""

content = content.replace(bad_str, good_str)

with open('custom-addons/finance_2/controllers/whatsapp_finance_api.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed successfully")
