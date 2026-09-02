import os

base_path = r'c:\odoo-repos\Soufiane-Food\custom-addons\finance_2'

# 1. Update cheque.py
cheque_model = os.path.join(base_path, 'models', 'cheque.py')
with open(cheque_model, 'r', encoding='utf-8') as f:
    content = f.read()

new_methods = """    def action_annuler(self):
        for rec in self:
            rec.state = 'annule'

    def action_open_chq_vide(self):
        self.ensure_one()
        if not self.chq_vide_pdf:
            return
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/finance2.cheque/{self.id}/chq_vide_pdf',
            'target': 'new',
        }

    def action_open_doc_pdf(self):
        self.ensure_one()
        if not self.doc_pdf:
            return
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/finance2.cheque/{self.id}/doc_pdf',
            'target': 'new',
        }"""

content = content.replace("    def action_annuler(self):\n        for rec in self:\n            rec.state = 'annule'", new_methods)

with open(cheque_model, 'w', encoding='utf-8') as f:
    f.write(content)

# 2. Update personne_views.xml
personne_views = os.path.join(base_path, 'views', 'personne_views.xml')
with open(personne_views, 'r', encoding='utf-8') as f:
    views_content = f.read()

old_tree = """                                <tree>
                                    <field name="name"/>
                                    <field name="date_emission"/>
                                    <field name="amount_total" sum="Total"/>
                                    <field name="state" widget="badge"/>
                                </tree>"""

new_tree = """                                <tree>
                                    <field name="name"/>
                                    <field name="date_emission"/>
                                    <field name="amount_total" sum="Total"/>
                                    <field name="state" widget="badge"/>
                                    <button name="action_open_chq_vide" string="Voir Chèque" type="object" icon="fa-file-pdf-o" invisible="not chq_vide_pdf"/>
                                    <button name="action_open_doc_pdf" string="Voir Doc" type="object" icon="fa-file-text-o" invisible="not doc_pdf"/>
                                    <field name="chq_vide_pdf" column_invisible="1"/>
                                    <field name="doc_pdf" column_invisible="1"/>
                                </tree>"""

views_content = views_content.replace(old_tree, new_tree)

with open(personne_views, 'w', encoding='utf-8') as f:
    f.write(views_content)

print("Added buttons to open PDFs")
