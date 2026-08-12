import re

# 1. Update whatsapp_pdf_bot_api.py (Prompt)
filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/controllers/whatsapp_pdf_bot_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_cma_note = """   (NOTE SPÉCIALE CMA : Pour le bénéficiaire "CMA", les frais de "magasinage" et de "surestarie" apparaissent souvent sur la MÊME facture. Vous DEVEZ OBLIGATOIREMENT suivre ces règles de calcul :
   - Le montant du "magasinage" est la SOMME EXACTE de tous les montants qui se trouvent sous le titre "(L) Terminal full storage at destination". ATTENTION: Lisez UNIQUEMENT les montants de la colonne "Montant Total".
   - Le montant de la "surestarie" est la SOMME EXACTE de tous les montants qui se trouvent sous le titre "(C) Detention & Demurrage Import Charge". ATTENTION: Lisez UNIQUEMENT les montants de la colonne "Montant Total". CELA INCLUT AUSSI la "Taxe Regionale" (qui se trouve sous "Charges Diverses").
   Extrayez ces deux totaux calculés comme DEUX éléments séparés dans votre tableau JSON, l'un avec le type "magasinage" et l'autre avec le type "surestarie")."""

new_cma_note = """   (NOTE SPÉCIALE CMA : Pour le bénéficiaire "CMA", NE FAITES PAS LA SOMME. Vous DEVEZ OBLIGATOIREMENT extraire CHAQUE montant séparément :
   - Pour chaque montant sous "(L) Terminal full storage at destination", créez un élément JSON séparé avec le type "magasinage".
   - Pour chaque montant sous "(C) Detention & Demurrage Import Charge" (ainsi que la "Taxe Regionale"), créez un élément JSON séparé avec le type "surestarie".
   ATTENTION: Lisez UNIQUEMENT les montants de la colonne "Montant Total". Vous devez retourner autant d'éléments dans le JSON qu'il y a de lignes de montants dans le tableau.)"""

content = content.replace(old_cma_note, new_cma_note)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

# 2. Update cheque.py (Computed Fields)
filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_fields = """    amount_total = fields.Float(string='Montant Total', tracking=True)

    type = fields.Selection([('cheque', 'Chèque'), ('effet', 'Effet')], string='Type', default='cheque', tracking=True)"""

new_fields = """    amount_total = fields.Float(string='Montant Total', tracking=True)
    
    total_surestarie = fields.Float(string='Total Surestarie', compute='_compute_totals')
    total_magasinage = fields.Float(string='Total Magasinage', compute='_compute_totals')
    total_change = fields.Float(string='Total Change', compute='_compute_totals')

    @api.depends('repartition_ids.amount', 'repartition_ids.type')
    def _compute_totals(self):
        for rec in self:
            rec.total_surestarie = sum(r.amount for r in rec.repartition_ids if r.type == 'surestarie')
            rec.total_magasinage = sum(r.amount for r in rec.repartition_ids if r.type == 'magasinage')
            rec.total_change = sum(r.amount for r in rec.repartition_ids if r.type == 'change')

    type = fields.Selection([('cheque', 'Chèque'), ('effet', 'Effet')], string='Type', default='cheque', tracking=True)"""

content = content.replace(old_fields, new_fields)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)


# 3. Update cheque_views.xml (View)
filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/views/cheque_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_view = """                            <field name="amount_total"/>
                            <field name="type"/>"""

new_view = """                            <field name="amount_total"/>
                            <field name="total_magasinage"/>
                            <field name="total_surestarie"/>
                            <field name="total_change"/>
                            <field name="type"/>"""

content = content.replace(old_view, new_view)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated prompt, models, and views successfully.")
