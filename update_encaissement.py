import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update State
old_state = """    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('reserve', 'Réserve'),
        ('actif', 'Actif'),
        ('cloture', 'Clôturé'),
        ('annule', 'Annulé'),
    ], string='État', default='brouillon', tracking=True, required=True)"""

new_state = """    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('reserve', 'Réserve'),
        ('actif', 'Actif'),
        ('cloture', 'Clôturé'),
        ('encaisse', 'Encaissé'),
        ('annule', 'Annulé'),
    ], string='État', default='brouillon', tracking=True, required=True)"""

content = content.replace(old_state, new_state)

# 2. Add Encaissement fields
old_logistique = """    # Suivi Logistique
    remis_a_id = fields.Many2one('finance2.personne', string='Remis à', tracking=True)"""

new_logistique = """    # Encaissement
    date_encaissement = fields.Date(string="Date d'encaissement", tracking=True)
    montant_encaisse = fields.Float(string="Montant encaissé", tracking=True)

    # Suivi Logistique
    remis_a_id = fields.Many2one('finance2.personne', string='Remis à', tracking=True)"""

content = content.replace(old_logistique, new_logistique)

# 3. Add action_encaisser
old_action_cloturer = """    def action_cloturer(self):
        for rec in self:
            missing_fields = []
            if not rec.amount_total:
                missing_fields.append("Montant Total")
            if not rec.date_echeance:
                missing_fields.append("Date d'échéance")
                
            if missing_fields:
                raise UserError("Vous ne pouvez pas clôturer ce chèque car les informations suivantes sont manquantes : " + ", ".join(missing_fields))
                
            rec.state = 'cloture'"""

new_action_cloturer = """    def action_cloturer(self):
        for rec in self:
            missing_fields = []
            if not rec.amount_total:
                missing_fields.append("Montant Total")
            if not rec.date_echeance:
                missing_fields.append("Date d'échéance")
                
            if missing_fields:
                raise UserError("Vous ne pouvez pas clôturer ce chèque car les informations suivantes sont manquantes : " + ", ".join(missing_fields))
                
            rec.state = 'cloture'

    def action_encaisser(self):
        for rec in self:
            if rec.state != 'cloture':
                raise UserError("Seuls les chèques clôturés peuvent être encaissés.")
            if not rec.date_encaissement:
                raise UserError("Veuillez renseigner la date d'encaissement.")
            if not rec.montant_encaisse:
                raise UserError("Veuillez renseigner le montant encaissé.")
                
            rec.state = 'encaisse'
            
            if rec.montant_encaisse != rec.amount_total:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Attention',
                        'message': 'Le montant encaissé est différent du montant total du chèque.',
                        'type': 'warning',
                        'sticky': False,
                    }
                }"""

content = content.replace(old_action_cloturer, new_action_cloturer)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)


# Update cheque_views.xml
filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/views/cheque_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Form view statusbar
old_statusbar = """statusbar_visible="brouillon,reserve,actif,cloture,annule\"/>"""
new_statusbar = """statusbar_visible="brouillon,reserve,actif,cloture,encaisse,annule\"/>"""
content = content.replace(old_statusbar, new_statusbar)

# Add encaissement fields to form
old_form_fields = """                            <field name="date_emission"/>
                            <field name="date_echeance"/>"""

new_form_fields = """                            <field name="date_emission"/>
                            <field name="date_echeance"/>
                            <field name="date_encaissement" attrs="{'invisible': [('state', 'in', ['brouillon', 'reserve', 'actif'])]}"/>
                            <field name="montant_encaisse" attrs="{'invisible': [('state', 'in', ['brouillon', 'reserve', 'actif'])]}"/>"""

content = content.replace(old_form_fields, new_form_fields)

# Create Encaissement view and action
new_views = """
    <!-- Vue Liste : Encaissement -->
    <record id="view_finance2_encaissement_tree" model="ir.ui.view">
        <field name="name">finance2.encaissement.tree</field>
        <field name="model">finance2.cheque</field>
        <field name="arch" type="xml">
            <tree string="Encaissement" editable="bottom" create="false" decoration-success="state == 'encaisse'" decoration-warning="state == 'cloture'">
                <field name="name" readonly="1"/>
                <field name="ste_id" readonly="1"/>
                <field name="benif_id" readonly="1"/>
                <field name="amount_total" readonly="1" sum="Total Chèques"/>
                <field name="date_encaissement" attrs="{'readonly': [('state', '=', 'encaisse')]}"/>
                <field name="montant_encaisse" attrs="{'readonly': [('state', '=', 'encaisse')]}" sum="Total Encaissé"/>
                <field name="state" readonly="1" widget="badge" decoration-success="state == 'encaisse'" decoration-warning="state == 'cloture'"/>
                <button name="action_encaisser" type="object" icon="fa-check" string="Encaisser" class="oe_highlight" attrs="{'invisible': [('state', '!=', 'cloture')]}"/>
            </tree>
        </field>
    </record>

    <!-- Action Encaissement -->
    <record id="action_finance2_encaissement" model="ir.actions.act_window">
        <field name="name">Encaissements</field>
        <field name="res_model">finance2.cheque</field>
        <field name="view_mode">tree,form</field>
        <field name="domain">[('state', 'in', ['cloture', 'encaisse'])]</field>
        <field name="context">{'search_default_cloture': 1}</field>
        <field name="view_id" ref="view_finance2_encaissement_tree"/>
    </record>
"""

# Inject before the menu items
content = content.replace("    <!-- Action -->", new_views + "\n    <!-- Action -->")

# Search view: add filter for cloture
old_search = """                <filter string="Actif" name="actif" domain="[('state', '=', 'actif')]"/>"""
new_search = """                <filter string="Actif" name="actif" domain="[('state', '=', 'actif')]"/>
                <filter string="Clôturé" name="cloture" domain="[('state', '=', 'cloture')]"/>
                <filter string="Encaissé" name="encaisse" domain="[('state', '=', 'encaisse')]"/>"""
content = content.replace(old_search, new_search)

# Menu items
old_menu = """    <menuitem id="menu_finance2_cheques" name="Chèques Physiques" parent="menu_finance2_root" action="action_finance2_cheque" sequence="10"/>"""
new_menu = """    <menuitem id="menu_finance2_cheques" name="Chèques Physiques" parent="menu_finance2_root" action="action_finance2_cheque" sequence="10"/>
    <menuitem id="menu_finance2_encaissement" name="Encaissement" parent="menu_finance2_root" action="action_finance2_encaissement" sequence="20"/>"""
content = content.replace(old_menu, new_menu)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated cheque.py and cheque_views.xml for encaissement")
