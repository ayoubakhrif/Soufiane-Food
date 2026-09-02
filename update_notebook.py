import os

file_path = r'c:\odoo-repos\Soufiane-Food\custom-addons\finance_2\views\personne_views.xml'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_tree = """                                <tree>
                                    <field name="name"/>
                                    <field name="date_emission"/>
                                    <field name="amount_total" sum="Total"/>
                                    <field name="state" widget="badge"/>
                                    <button name="action_open_chq_vide" string="Voir Chèque" type="object" icon="fa-file-pdf-o" invisible="not chq_vide_pdf"/>
                                    <button name="action_open_doc_pdf" string="Voir Doc" type="object" icon="fa-file-text-o" invisible="not doc_pdf"/>
                                    <field name="chq_vide_pdf" column_invisible="1"/>
                                    <field name="doc_pdf" column_invisible="1"/>
                                </tree>"""

new_tree = """                                <tree>
                                    <field name="name" string="Chèque"/>
                                    <field name="date_emission"/>
                                    <field name="date_echeance"/>
                                    <field name="date_encaissement"/>
                                    <field name="amount_total" string="Crédit" sum="Total Crédit"/>
                                    <field name="montant_encaisse" string="Encaissement" sum="Total Encaissé"/>
                                    <field name="state" widget="badge"/>
                                    <button name="action_open_chq_vide" string="Voir Chèque" type="object" icon="fa-file-pdf-o" invisible="not chq_vide_pdf"/>
                                    <button name="action_open_doc_pdf" string="Voir Doc" type="object" icon="fa-file-text-o" invisible="not doc_pdf"/>
                                    <field name="chq_vide_pdf" column_invisible="1"/>
                                    <field name="doc_pdf" column_invisible="1"/>
                                </tree>"""

# Let's use a regex or string replacement. Since there might be some encoding issues with strings from git diffs, I'll use standard replace
content = content.replace(old_tree, new_tree)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated tree view")
