import os
import re

filepath = 'custom-addons/finance_2/views/cheque_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add button in Encaissement tree
old_tree_btn = '<button name="action_encaisser" type="object" icon="fa-check" string="Encaisser" class="oe_highlight" invisible="state != \'cloture\'"/>'
new_tree_btn = """<button name="action_encaisser" type="object" icon="fa-check" string="Encaisser" class="oe_highlight" invisible="state != 'cloture'"/>
                <button name="action_annuler_encaissement" type="object" icon="fa-undo" string="Annuler Encaissement" class="btn-danger" invisible="state != 'encaisse'"/>"""
content = content.replace(old_tree_btn, new_tree_btn)

# Modify Action Context for Encaissement
old_action_context = "<field name=\"context\">{'search_default_cloture': 1}</field>"
new_action_context = "<field name=\"context\">{'search_default_cloture': 1, 'group_by': ['date_encaissement:day']}</field>"
content = content.replace(old_action_context, new_action_context)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated XML view")
