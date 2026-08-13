import re

# 1. Update cheque.py
filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add total_inspection to cheque
old_totals = """    total_change = fields.Float(string='Total Change', compute='_compute_totals')
    total_repartitions = fields.Float(string='Total Répartitions', compute='_compute_totals')

    @api.depends('repartition_ids.amount', 'repartition_ids.type')
    def _compute_totals(self):
        for rec in self:
            rec.total_surestarie = sum(r.amount for r in rec.repartition_ids if r.type == 'surestarie')
            rec.total_magasinage = sum(r.amount for r in rec.repartition_ids if r.type == 'magasinage')
            rec.total_change = sum(r.amount for r in rec.repartition_ids if r.type == 'change')
            rec.total_repartitions = sum(r.amount for r in rec.repartition_ids)"""

new_totals = """    total_change = fields.Float(string='Total Change', compute='_compute_totals')
    total_inspection = fields.Float(string='Total Inspection', compute='_compute_totals')
    total_repartitions = fields.Float(string='Total Répartitions', compute='_compute_totals')

    @api.depends('repartition_ids.amount', 'repartition_ids.type')
    def _compute_totals(self):
        for rec in self:
            rec.total_surestarie = sum(r.amount for r in rec.repartition_ids if r.type == 'surestarie')
            rec.total_magasinage = sum(r.amount for r in rec.repartition_ids if r.type == 'magasinage')
            rec.total_change = sum(r.amount for r in rec.repartition_ids if r.type == 'change')
            rec.total_inspection = sum(r.amount for r in rec.repartition_ids if r.type == 'inspection')
            rec.total_repartitions = sum(r.amount for r in rec.repartition_ids)"""

content = content.replace(old_totals, new_totals)

# Add inspection to repartition type
old_type = """    type = fields.Selection([
        ('surestarie', 'Surestarie'),
        ('magasinage', 'Magasinage'),
        ('change', 'Change')
    ], string='Type')"""

new_type = """    type = fields.Selection([
        ('surestarie', 'Surestarie'),
        ('magasinage', 'Magasinage'),
        ('change', 'Change'),
        ('inspection', 'Inspection')
    ], string='Type')"""

content = content.replace(old_type, new_type)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

# 2. Update cheque_views.xml
filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/views/cheque_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_view_totals = """                            <field name="total_magasinage"/>
                            <field name="total_surestarie"/>
                            <field name="total_change"/>"""

new_view_totals = """                            <field name="total_magasinage"/>
                            <field name="total_surestarie"/>
                            <field name="total_change"/>
                            <field name="total_inspection"/>"""

content = content.replace(old_view_totals, new_view_totals)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

# 3. Update whatsapp_pdf_bot_api.py
filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/controllers/whatsapp_pdf_bot_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_mapping = """                type_val = False
                if inv_type in ['surestarie', 'magasinage', 'change']:
                    type_val = inv_type"""

new_mapping = """                type_val = False
                if inv_type in ['surestarie', 'magasinage', 'change', 'inspection']:
                    type_val = inv_type"""

content = content.replace(old_mapping, new_mapping)

# Add Hapag prompt
old_prompt_rules = """- PRIORITÉ: Si le mot "MAGASINAGE" apparait, c'est obligatoirement "magasinage"."""

new_prompt_rules = """- PRIORITÉ: Si le mot "MAGASINAGE" apparait, c'est obligatoirement "magasinage".
- NOTE SPÉCIALE HAPAG-LLOYD : Si le bénéficiaire est Hapag-Lloyd (ou Hapag) et que la facture contient une ligne "INSPECTION FEE", vous devez prendre le MONTANT TOTAL de la facture (ex: TOTAL H.T. ou Total Général) et retourner UN SEUL élément JSON avec ce montant total et le type "inspection"."""

content = content.replace(old_prompt_rules, new_prompt_rules)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated cheque.py, cheque_views.xml, and whatsapp_pdf_bot_api.py with inspection")
