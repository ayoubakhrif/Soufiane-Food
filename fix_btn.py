import os
import re

filepath = 'custom-addons/finance_2/views/cheque_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# I will add a new button "Remettre en Brouillon (Responsable)"
new_btn = """<button name="action_remettre_finance" string="Remettre à Finance (Brouillon)" type="object" groups="finance_2.group_finance2_manager" invisible="state not in ('reserve', 'actif')" confirm="Voulez-vous vraiment remettre ce chèque en brouillon ?"/>"""

content = content.replace(
    '<button name="action_remettre_finance" string="Remettre  Finance" type="object" invisible="state != \'reserve\'"/>',
    new_btn
)
# Note: due to unicode characters, I'll use regex or simple replace
