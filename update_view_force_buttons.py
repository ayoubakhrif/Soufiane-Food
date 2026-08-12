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
                    
                    <field name="is_admin" invisible="1"/>
                    <field name="admin_state" widget="statusbar" statusbar_visible="brouillon,reserve,actif,cloture" options="{'clickable': '1'}" attrs="{'invisible': [('is_admin', '=', False)]}"/>
                    <field name="state" widget="statusbar" statusbar_visible="brouillon,reserve,actif,cloture" attrs="{'invisible': [('is_admin', '=', True)]}"/>
                </header>"""

new_header = """                <header>
                    <button name="action_confirmer" string="Réserve" type="object" class="oe_highlight" states="brouillon"/>
                    <button name="action_remettre_finance" string="Remettre à la finance" type="object" class="oe_highlight" states="reserve"/>
                    <button name="action_mettre_actif" string="Actif" type="object" class="oe_highlight" states="reserve"/>
                    <button name="action_cloturer" string="Clôturer" type="object" class="oe_highlight" states="actif"/>
                    <button name="action_annuler" string="Annuler" type="object" states="brouillon,reserve,actif"/>
                    
                    <!-- Boutons Admin -->
                    <button name="force_brouillon" string="Forcer Brouillon" type="object" groups="finance_2.group_finance2_admin" attrs="{'invisible': [('state', '=', 'brouillon')]}"/>
                    <button name="force_reserve" string="Forcer Réserve" type="object" groups="finance_2.group_finance2_admin" attrs="{'invisible': [('state', '=', 'reserve')]}"/>
                    <button name="force_actif" string="Forcer Actif" type="object" groups="finance_2.group_finance2_admin" attrs="{'invisible': [('state', '=', 'actif')]}"/>
                    <button name="force_cloture" string="Forcer Clôturé" type="object" groups="finance_2.group_finance2_admin" attrs="{'invisible': [('state', '=', 'cloture')]}"/>

                    <field name="state" widget="statusbar" statusbar_visible="brouillon,reserve,actif,cloture"/>
                </header>"""

content = content.replace(old_header, new_header)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated cheque_views.xml with force buttons")
