import os
filepath = "custom-addons/generate_bons/controllers/whatsapp_bon_api.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "'file_name': f\"Facture_Proforma_{bon_reel.name}.pdf\",\n                'mimetype': 'application/pdf'",
    "'file_name': f\"Facture_Proforma_{bon_reel.name}.pdf\",\n                'mimetype': 'application/pdf',\n                'caption': f\"✅ Bon Proforma *{bon_reel.name}* généré avec succès !\""
)

content = content.replace(
    "'file_name': f\"Facture_Proforma_{bon_fictif.name}_Fictif.pdf\",\n                    'mimetype': 'application/pdf'",
    "'file_name': f\"Facture_Proforma_{bon_fictif.name}_Fictif.pdf\",\n                    'mimetype': 'application/pdf',\n                    'caption': f\"✅ Bon Proforma *{bon_fictif.name}* (Fictif - {poids_fictif}kg) généré !\""
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("api patched")
