import os

base_path = r'c:\odoo-repos\Soufiane-Food\custom-addons\finance_2'

# 1. models/comparison.py
comparison_py = """from odoo import models, fields, api
from datetime import datetime

class Finance2Comparison(models.Model):
    _name = 'finance2.comparison'
    _description = 'Audit et Comparaison (Ancien vs V2)'
    _order = 'date_audit desc'

    name = fields.Char(string='Nom de l\\'audit', required=True, default=lambda self: f"Audit du {fields.Date.context_today(self).strftime('%d/%m/%Y')}")
    date_audit = fields.Datetime(string='Date d\\'exécution', default=fields.Datetime.now, readonly=True)
    line_ids = fields.One2many('finance2.comparison.line', 'comparison_id', string='Résultats')

    def action_run_comparison(self):
        self.ensure_one()
        # Vider les anciennes lignes pour ce run si on relance
        self.line_ids.unlink()

        # Récupérer les données
        physicals = self.env['finance.cheque.physical'].search([])
        cheques_v2 = self.env['finance2.cheque'].search([])

        # Dictionnaires pour accès rapide (Clé: (numéro, nom_société))
        v1_dict = {}
        for p in physicals:
            if not p.name: continue
            ste_name = p.ste_id.name.strip().upper() if p.ste_id and p.ste_id.name else "INCONNU"
            v1_dict[(p.name.strip(), ste_name)] = p

        v2_dict = {}
        for c in cheques_v2:
            if not c.name: continue
            ste_name = c.ste_id.name.strip().upper() if c.ste_id and c.ste_id.name else "INCONNU"
            v2_dict[(c.name.strip(), ste_name)] = c

        all_keys = set(v1_dict.keys()).union(set(v2_dict.keys()))
        
        lines_to_create = []
        for key in all_keys:
            num, ste = key
            p = v1_dict.get(key)
            c = v2_dict.get(key)

            if p and not c:
                # Seulement V1
                lines_to_create.append({
                    'comparison_id': self.id,
                    'cheque_number': p.name,
                    'ste_name': p.ste_id.name if p.ste_id else "Inconnu",
                    'status': 'only_v1',
                    'v1_amount': p.amount_total,
                    'v2_amount': 0.0,
                    'diff_details': "Manquant dans Finance V2",
                })
            elif c and not p:
                # Seulement V2
                lines_to_create.append({
                    'comparison_id': self.id,
                    'cheque_number': c.name,
                    'ste_name': c.ste_id.name if c.ste_id else "Inconnu",
                    'status': 'only_v2',
                    'v1_amount': 0.0,
                    'v2_amount': c.amount_total,
                    'diff_details': "Nouveau ou absent de l'ancien module",
                })
            elif c and p:
                # Sur les deux, on compare
                diffs = []
                # Montant
                if abs(p.amount_total - c.amount_total) > 0.01:
                    diffs.append(f"Montant (Ancien: {p.amount_total} | V2: {c.amount_total})")
                # Date Emission
                if p.date_emission != c.date_emission:
                    d1 = p.date_emission.strftime('%d/%m/%Y') if p.date_emission else 'N/A'
                    d2 = c.date_emission.strftime('%d/%m/%Y') if c.date_emission else 'N/A'
                    diffs.append(f"Émission ({d1} vs {d2})")
                # Date Echeance
                if p.date_echeance != c.date_echeance:
                    d1 = p.date_echeance.strftime('%d/%m/%Y') if p.date_echeance else 'N/A'
                    d2 = c.date_echeance.strftime('%d/%m/%Y') if c.date_echeance else 'N/A'
                    diffs.append(f"Échéance ({d1} vs {d2})")
                
                if diffs:
                    lines_to_create.append({
                        'comparison_id': self.id,
                        'cheque_number': c.name,
                        'ste_name': c.ste_id.name if c.ste_id else "Inconnu",
                        'status': 'diff',
                        'v1_amount': p.amount_total,
                        'v2_amount': c.amount_total,
                        'diff_details': " | ".join(diffs),
                    })
                else:
                    lines_to_create.append({
                        'comparison_id': self.id,
                        'cheque_number': c.name,
                        'ste_name': c.ste_id.name if c.ste_id else "Inconnu",
                        'status': 'ok',
                        'v1_amount': p.amount_total,
                        'v2_amount': c.amount_total,
                        'diff_details': "Identiques",
                    })

        if lines_to_create:
            self.env['finance2.comparison.line'].create(lines_to_create)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


class Finance2ComparisonLine(models.Model):
    _name = 'finance2.comparison.line'
    _description = 'Ligne d\\'audit Comparatif'

    comparison_id = fields.Many2one('finance2.comparison', string='Audit', ondelete='cascade')
    cheque_number = fields.Char(string='Numéro du chèque')
    ste_name = fields.Char(string='Société')
    
    status = fields.Selection([
        ('only_v1', 'Manquant dans V2'),
        ('only_v2', 'Nouveau dans V2'),
        ('diff', 'Différence détectée'),
        ('ok', 'Identique')
    ], string='Statut')
    
    v1_amount = fields.Float(string='Montant (Ancien)')
    v2_amount = fields.Float(string='Montant (V2)')
    diff_details = fields.Text(string='Détails')
"""
with open(os.path.join(base_path, 'models', 'comparison.py'), 'w', encoding='utf-8') as f:
    f.write(comparison_py)

init_py = os.path.join(base_path, 'models', '__init__.py')
with open(init_py, 'r', encoding='utf-8') as f:
    if 'comparison' not in f.read():
        with open(init_py, 'a', encoding='utf-8') as f2:
            f2.write('\nfrom . import comparison\n')

# 2. views/comparison_views.xml
comparison_views_xml = """<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Vue Recherche pour les Lignes -->
    <record id="view_finance2_comparison_line_search" model="ir.ui.view">
        <field name="name">finance2.comparison.line.search</field>
        <field name="model">finance2.comparison.line</field>
        <field name="arch" type="xml">
            <search string="Recherche Lignes Audit">
                <field name="cheque_number"/>
                <field name="ste_name"/>
                <filter string="Anomalies (Manquants ou Différents)" name="anomalies" domain="[('status', 'in', ['only_v1', 'diff'])]"/>
                <filter string="Manquant dans V2" name="only_v1" domain="[('status', '=', 'only_v1')]"/>
                <filter string="Différence détectée" name="diff" domain="[('status', '=', 'diff')]"/>
                <filter string="Nouveau dans V2" name="only_v2" domain="[('status', '=', 'only_v2')]"/>
                <filter string="Identiques" name="ok" domain="[('status', '=', 'ok')]"/>
                <group expand="0" string="Regrouper par">
                    <filter string="Statut" name="group_status" context="{'group_by':'status'}"/>
                    <filter string="Société" name="group_ste" context="{'group_by':'ste_name'}"/>
                </group>
            </search>
        </field>
    </record>

    <!-- Vue Formulaire pour l'Audit (Run) -->
    <record id="view_finance2_comparison_form" model="ir.ui.view">
        <field name="name">finance2.comparison.form</field>
        <field name="model">finance2.comparison</field>
        <field name="arch" type="xml">
            <form string="Audit Comparatif">
                <header>
                    <button name="action_run_comparison" string="Lancer / Rafraîchir l'Audit" type="object" class="oe_highlight"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1>
                            <field name="name" placeholder="Nom de l'audit"/>
                        </h1>
                    </div>
                    <group>
                        <field name="date_audit"/>
                    </group>
                    
                    <notebook>
                        <page string="Résultats de la Comparaison">
                            <field name="line_ids">
                                <tree decoration-danger="status == 'only_v1'" decoration-warning="status == 'diff'" decoration-info="status == 'only_v2'" decoration-success="status == 'ok'">
                                    <field name="cheque_number"/>
                                    <field name="ste_name"/>
                                    <field name="status" widget="badge" decoration-danger="status == 'only_v1'" decoration-warning="status == 'diff'" decoration-info="status == 'only_v2'" decoration-success="status == 'ok'"/>
                                    <field name="v1_amount"/>
                                    <field name="v2_amount"/>
                                    <field name="diff_details"/>
                                </tree>
                            </field>
                        </page>
                    </notebook>
                </sheet>
            </form>
        </field>
    </record>

    <!-- Vue Liste pour les Audits -->
    <record id="view_finance2_comparison_tree" model="ir.ui.view">
        <field name="name">finance2.comparison.tree</field>
        <field name="model">finance2.comparison</field>
        <field name="arch" type="xml">
            <tree string="Audits Comparatifs">
                <field name="name"/>
                <field name="date_audit"/>
            </tree>
        </field>
    </record>

    <!-- Action -->
    <record id="action_finance2_comparison" model="ir.actions.act_window">
        <field name="name">Audits Comparatifs (Ancien vs V2)</field>
        <field name="res_model">finance2.comparison</field>
        <field name="view_mode">tree,form</field>
    </record>

    <!-- Menu -->
    <menuitem id="menu_finance2_comparison" name="Audit Comparatif" parent="menu_finance2_root" action="action_finance2_comparison" sequence="99"/>
</odoo>
"""
with open(os.path.join(base_path, 'views', 'comparison_views.xml'), 'w', encoding='utf-8') as f:
    f.write(comparison_views_xml)

# 3. Update __manifest__.py
manifest_path = os.path.join(base_path, '__manifest__.py')
with open(manifest_path, 'r', encoding='utf-8') as f:
    manifest = f.read()

if 'views/comparison_views.xml' not in manifest:
    manifest = manifest.replace(
        "'views/talon_views.xml',",
        "'views/talon_views.xml',\n        'views/comparison_views.xml',"
    )
    with open(manifest_path, 'w', encoding='utf-8') as f:
        f.write(manifest)

# 4. Update ir.model.access.csv
security_path = os.path.join(base_path, 'security', 'ir.model.access.csv')
with open(security_path, 'a', encoding='utf-8') as f:
    f.write("access_finance2_comparison,finance2.comparison,model_finance2_comparison,finance_2.group_finance2_user,1,1,1,1\n")
    f.write("access_finance2_comparison_line,finance2.comparison.line,model_finance2_comparison_line,finance_2.group_finance2_user,1,1,1,1\n")

print("Comparison module setup completed.")
