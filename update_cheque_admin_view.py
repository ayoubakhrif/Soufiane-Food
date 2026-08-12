import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/views/cheque_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add the admin notebook page before the closing notebook tag
old_notebook_end = """                        </page>
                    </notebook>
                </sheet>"""

new_notebook_end = """                        </page>
                        <page string="Administration" groups="finance_2.group_finance2_admin">
                            <group>
                                <field name="state" string="Forcer l'état"/>
                            </group>
                        </page>
                    </notebook>
                </sheet>"""

content = content.replace(old_notebook_end, new_notebook_end)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated cheque_views.xml with admin page")
