import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/views/cheque_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Update the header
old_header = """                <header>
                    <button name="action_confirmer" string="Réserve" type="object" class="oe_highlight" states="brouillon"/>
                    <button name="action_remettre_finance" string="Remettre à la finance" type="object" class="oe_highlight" states="reserve"/>
                    <button name="action_mettre_actif" string="Actif" type="object" class="oe_highlight" states="reserve"/>
                    <button name="action_cloturer" string="Clôturer" type="object" class="oe_highlight" states="actif"/>
                    <button name="action_annuler" string="Annuler" type="object" states="brouillon,reserve,actif"/>
                    <field name="state" widget="statusbar" statusbar_visible="brouillon,reserve,actif,cloture"/>
                </header>
                <sheet>"""

new_header = """                <header>
                    <button name="action_confirmer" string="Réserve" type="object" class="oe_highlight" states="brouillon"/>
                    <button name="action_remettre_finance" string="Remettre à la finance" type="object" class="oe_highlight" states="reserve"/>
                    <button name="action_mettre_actif" string="Actif" type="object" class="oe_highlight" states="reserve"/>
                    <button name="action_cloturer" string="Clôturer" type="object" class="oe_highlight" states="actif"/>
                    <button name="action_annuler" string="Annuler" type="object" states="brouillon,reserve,actif"/>
                    
                    <field name="is_admin" invisible="1"/>
                    <field name="state" widget="statusbar" statusbar_visible="brouillon,reserve,actif,cloture" options="{'clickable': '1'}" attrs="{'invisible': [('is_admin', '=', False)]}"/>
                    <field name="state" widget="statusbar" statusbar_visible="brouillon,reserve,actif,cloture" attrs="{'invisible': [('is_admin', '=', True)]}"/>
                </header>
                <sheet>"""

content = content.replace(old_header, new_header)

# Remove the Administration notebook page
old_notebook_end = """                        <page string="Administration" groups="finance_2.group_finance2_admin">
                            <group>
                                <field name="state" string="Forcer l'état"/>
                            </group>
                        </page>
                    </notebook>
                </sheet>"""

new_notebook_end = """                    </notebook>
                </sheet>"""

content = content.replace(old_notebook_end, new_notebook_end)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated cheque_views.xml with clickable statusbar")
