import os

filepath = "whatsapp_bridge/index.js"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Add constants
if "GENERATE_BONS_GROUP_ID" not in content:
    content = content.replace(
        'const NUMBER_TO_WORDS_GROUP_ID = "120363409052445823@g.us";',
        'const NUMBER_TO_WORDS_GROUP_ID = "120363409052445823@g.us";\nconst GENERATE_BONS_GROUP_ID = "120363430689222541@g.us";\nconst GENERATE_BONS_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/generate_bon?db=soufianefoods";'
    )

# Add routing
if "else if (from === GENERATE_BONS_GROUP_ID)" not in content:
    content = content.replace(
        '} else if (from === NUMBER_TO_WORDS_GROUP_ID) {',
        '} else if (from === GENERATE_BONS_GROUP_ID) {\n                apiUrl = GENERATE_BONS_ODOO_URL;\n            } else if (from === NUMBER_TO_WORDS_GROUP_ID) {'
    )

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("index.js patched successfully.")
