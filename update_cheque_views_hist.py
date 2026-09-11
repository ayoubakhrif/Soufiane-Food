import os
import re

filepath = 'custom-addons/finance_2/views/cheque_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add button
old_btn = """<button name="action_annuler" string="Annuler" type="object" invisible="state not in ('brouillon', 'actif', 'reserve')"/>"""
new_btn = """<button name="action_annuler" string="Annuler" type="object" invisible="state not in ('brouillon', 'actif', 'reserve')"/>
                    <button name="action_reporter_cheque" string="Reporter le chèque" type="object" invisible="not week or not journal" confirm="Voulez-vous reporter ce chèque ? Cela effacera la date d'émission et le journal actuels."/>"""
content = content.replace(old_btn, new_btn)

# Add field history_journals
old_field = """<field name="journal"/>"""
new_field = """<field name="journal"/>
                            <field name="history_journals" invisible="not history_journals"/>"""
content = content.replace(old_field, new_field, 1)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated cheque_views.xml")
