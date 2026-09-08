import os

filepath = 'custom-addons/tanger_med/models/tanger_med_entry.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

method_code = """
    def action_generate_missing_sutra_records(self):
        valid_states = ['attente_ml', 'analyse', 'visite', 'en_cours_chargement', 'sortie_plein', 'rentree_vide', 'arrive_depot']
        for record in self:
            if record.tanger_med_state in valid_states:
                existing = self.env['sutra.dossier'].search([('logistics_id', '=', record.id)])
                if not existing:
                    self.env['sutra.dossier'].create({'logistics_id': record.id})
"""
if "def action_generate_missing_sutra_records" not in content:
    content = content + "\n" + method_code
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

xml_path = 'custom-addons/tanger_med/data/server_actions.xml'
with open(xml_path, 'r', encoding='utf-8') as f:
    xml_content = f.read()

import re
xml_content = re.sub(
    r'<field name="code">.*?</field>',
    '<field name="code">\nif records:\n    records.action_generate_missing_sutra_records()\n            </field>',
    xml_content,
    flags=re.DOTALL,
    count=1
)

with open(xml_path, 'w', encoding='utf-8') as f:
    f.write(xml_content)

print("Updated python model and xml action")
