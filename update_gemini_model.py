import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the hack that forces gemini-pro-latest
old_hack = """            gemini_model = gemini_model.replace('models/', '')
            # Forcer gemini-pro-latest si la valeur est l'ancienne qui crashait
            if gemini_model in ['gemini-1.5-flash-latest', 'gemini-flash-latest', 'gemini-1.5-flash']:
                gemini_model = 'gemini-pro-latest'

            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={api_key}\""""

new_hack = """            gemini_model = gemini_model.replace('models/', '')

            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={api_key}\""""

content = content.replace(old_hack, new_hack)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Removed forced gemini-pro-latest override.")
