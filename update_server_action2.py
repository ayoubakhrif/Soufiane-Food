import os
import re

filepath = 'custom-addons/tanger_med/data/server_actions.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_code = """for record in records:
    existing = env['sutra.dossier'].search([('logistics_id', '=', record.id)])
    if not existing:
        env['sutra.dossier'].create({'logistics_id': record.id})"""

new_code = """valid_states = ['attente_ml', 'analyse', 'visite', 'en_cours_chargement', 'sortie_plein', 'rentree_vide', 'arrive_depot']
for record in records:
    if record.tanger_med_state in valid_states:
        existing = env['sutra.dossier'].search([('logistics_id', '=', record.id)])
        if not existing:
            env['sutra.dossier'].create({'logistics_id': record.id})"""

content = content.replace(old_code, new_code)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated server action")
