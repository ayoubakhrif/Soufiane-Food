import os
import re

base_path = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2'

# 1. Create models/talon.py
talon_py_content = """from odoo import models, fields, api, _

class Finance2Talon(models.Model):
    _name = 'finance2.talon'
    _description = 'Talon de Chèques'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Référence Talon', required=True, tracking=True)
    ste_id = fields.Many2one('finance2.ste', string='Société', required=True, tracking=True)
    date_reception = fields.Date(string='Date de réception', tracking=True)
    
    first_cheque_number = fields.Char(string='Numéro de départ', required=True, tracking=True)
    num_chq = fields.Integer(string='Nombre de chèques', required=True, tracking=True, default=50)
    last_cheque_number = fields.Char(string='Numéro de fin', compute='_compute_last_cheque', store=True)
    
    etat = fields.Selection([
        ('coffre', 'En Coffre'),
        ('actif', 'Actif'),
        ('cloture', 'Clôturé'),
    ], string='État', default='coffre', tracking=True)

    cheque_ids = fields.One2many('finance2.cheque', 'talon_id', string='Chèques liés')
    
    used_chqs = fields.Integer(string='Utilisés', compute='_compute_metrics', store=True)
    unused_chqs = fields.Integer(string='Restants', compute='_compute_metrics', store=True)
    usage_percentage = fields.Float(string='% Utilisation', compute='_compute_metrics', store=True)
    last_used_chq = fields.Char(string='Dernier utilisé', compute='_compute_metrics', store=True)
    missing_chqs_text = fields.Text(string='Chèques manquants', compute='_compute_metrics', store=True)

    @api.depends('first_cheque_number', 'num_chq')
    def _compute_last_cheque(self):
        for rec in self:
            if rec.first_cheque_number and rec.first_cheque_number.isdigit() and rec.num_chq:
                length = len(rec.first_cheque_number)
                start_val = int(rec.first_cheque_number)
                end_val = start_val + rec.num_chq - 1
                rec.last_cheque_number = str(end_val).zfill(length)
            else:
                rec.last_cheque_number = False

    @api.depends('cheque_ids', 'cheque_ids.name', 'first_cheque_number', 'last_cheque_number')
    def _compute_metrics(self):
        for rec in self:
            cheques = rec.cheque_ids.filtered(lambda c: c.name and c.name.isdigit())
            rec.used_chqs = len(cheques)
            rec.unused_chqs = rec.num_chq - rec.used_chqs if rec.num_chq else 0
            rec.usage_percentage = (rec.used_chqs / rec.num_chq * 100) if rec.num_chq else 0.0
            
            if cheques:
                sorted_cheques = sorted([int(c.name) for c in cheques])
                rec.last_used_chq = str(sorted_cheques[-1]).zfill(len(rec.first_cheque_number or ''))
                
                # Check for missing
                if rec.first_cheque_number and rec.first_cheque_number.isdigit():
                    expected = set(range(int(rec.first_cheque_number), sorted_cheques[-1] + 1))
                    actual = set(sorted_cheques)
                    missing = sorted(list(expected - actual))
                    if missing:
                        rec.missing_chqs_text = ", ".join([str(m).zfill(len(rec.first_cheque_number)) for m in missing])
                    else:
                        rec.missing_chqs_text = False
                else:
                    rec.missing_chqs_text = False
            else:
                rec.last_used_chq = False
                rec.missing_chqs_text = False

    @api.constrains('cheque_ids')
    def _auto_update_etat(self):
        for rec in self:
            if rec.used_chqs == 0:
                rec.etat = 'coffre'
            elif rec.used_chqs > 0 and rec.used_chqs < rec.num_chq:
                rec.etat = 'actif'
            elif rec.used_chqs >= rec.num_chq:
                rec.etat = 'cloture'
"""
with open(os.path.join(base_path, 'models', 'talon.py'), 'w', encoding='utf-8') as f:
    f.write(talon_py_content)

# 2. Add to models/__init__.py
init_py_path = os.path.join(base_path, 'models', '__init__.py')
with open(init_py_path, 'r', encoding='utf-8') as f:
    init_py = f.read()
if 'import talon' not in init_py:
    with open(init_py_path, 'a', encoding='utf-8') as f:
        f.write("\nfrom . import talon\n")

# 3. Update models/cheque.py
cheque_py_path = os.path.join(base_path, 'models', 'cheque.py')
with open(cheque_py_path, 'r', encoding='utf-8') as f:
    cheque_py = f.read()

# Add talon_id field
if 'talon_id = fields.Many2one' not in cheque_py:
    new_field = "    talon_id = fields.Many2one('finance2.talon', string='Talon', tracking=True)\n\n    # Répartitions"
    cheque_py = cheque_py.replace("    # Répartitions", new_field)

# Add auto-linking logic
auto_link_code = """
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('talon_id') and vals.get('name') and vals.get('ste_id'):
                talon = self._find_matching_talon(vals['name'], vals['ste_id'])
                if talon:
                    vals['talon_id'] = talon.id
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if 'name' in vals or 'ste_id' in vals:
            for rec in self:
                if not rec.talon_id and rec.name and rec.ste_id:
                    talon = self._find_matching_talon(rec.name, rec.ste_id.id)
                    if talon:
                        rec.talon_id = talon.id
        return res

    def _find_matching_talon(self, chq_number, ste_id):
        if not chq_number or not chq_number.isdigit():
            return False
        num = int(chq_number)
        talons = self.env['finance2.talon'].search([('ste_id', '=', ste_id)])
        for t in talons:
            if t.first_cheque_number and t.last_cheque_number and t.first_cheque_number.isdigit() and t.last_cheque_number.isdigit():
                if int(t.first_cheque_number) <= num <= int(t.last_cheque_number):
                    return t
        return False
"""
if 'def _find_matching_talon' not in cheque_py:
    # Insert at the end of the class
    cheque_py = cheque_py + auto_link_code

with open(cheque_py_path, 'w', encoding='utf-8') as f:
    f.write(cheque_py)


# 4. Create views/talon_views.xml
talon_xml_content = """<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_finance2_talon_form" model="ir.ui.view">
        <field name="name">finance2.talon.form</field>
        <field name="model">finance2.talon</field>
        <field name="arch" type="xml">
            <form string="Talon">
                <header>
                    <field name="etat" widget="statusbar" statusbar_visible="coffre,actif,cloture" options="{'clickable': '1'}"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1>
                            <field name="name" placeholder="Référence du Talon..."/>
                        </h1>
                    </div>
                    
                    <div class="alert alert-danger text-center" role="alert" invisible="not missing_chqs_text">
                        <strong>Attention !</strong> Les chèques suivants sont manquants / sautés : <field name="missing_chqs_text" readonly="1"/>
                    </div>
                    
                    <group>
                        <group>
                            <field name="ste_id"/>
                            <field name="date_reception"/>
                        </group>
                        <group>
                            <field name="first_cheque_number"/>
                            <field name="num_chq"/>
                            <field name="last_cheque_number"/>
                        </group>
                    </group>
                    
                    <group string="Indicateurs">
                        <group>
                            <field name="used_chqs"/>
                            <field name="unused_chqs"/>
                        </group>
                        <group>
                            <field name="last_used_chq"/>
                            <field name="usage_percentage" widget="progressbar"/>
                        </group>
                    </group>
                    
                    <notebook>
                        <page string="Chèques liés">
                            <field name="cheque_ids">
                                <tree>
                                    <field name="name"/>
                                    <field name="date_emission"/>
                                    <field name="amount_total" sum="Total"/>
                                    <field name="state" widget="badge"/>
                                </tree>
                            </field>
                        </page>
                    </notebook>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_follower_ids" widget="mail_followers"/>
                    <field name="activity_ids" widget="mail_activity"/>
                    <field name="message_ids" widget="mail_thread"/>
                </div>
            </form>
        </field>
    </record>

    <record id="view_finance2_talon_tree" model="ir.ui.view">
        <field name="name">finance2.talon.tree</field>
        <field name="model">finance2.talon</field>
        <field name="arch" type="xml">
            <tree string="Talons">
                <field name="name"/>
                <field name="ste_id"/>
                <field name="first_cheque_number"/>
                <field name="last_cheque_number"/>
                <field name="usage_percentage" widget="progressbar"/>
                <field name="etat" widget="badge" decoration-info="etat == 'coffre'" decoration-success="etat == 'actif'" decoration-muted="etat == 'cloture'"/>
            </tree>
        </field>
    </record>

    <record id="action_finance2_talon" model="ir.actions.act_window">
        <field name="name">Talons</field>
        <field name="res_model">finance2.talon</field>
        <field name="view_mode">tree,form</field>
    </record>
</odoo>
"""
with open(os.path.join(base_path, 'views', 'talon_views.xml'), 'w', encoding='utf-8') as f:
    f.write(talon_xml_content)

# 5. Add to __manifest__.py
manifest_path = os.path.join(base_path, '__manifest__.py')
with open(manifest_path, 'r', encoding='utf-8') as f:
    manifest = f.read()

if 'views/talon_views.xml' not in manifest:
    manifest = manifest.replace("'views/cheque_views.xml',", "'views/cheque_views.xml',\n        'views/talon_views.xml',")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        f.write(manifest)

# 6. Update views/cheque_views.xml to add talon menu and talon_id field
cheque_views_path = os.path.join(base_path, 'views', 'cheque_views.xml')
with open(cheque_views_path, 'r', encoding='utf-8') as f:
    cheque_views = f.read()

if '<field name="talon_id"/>' not in cheque_views:
    cheque_views = cheque_views.replace('<field name="benif_id"/>', '<field name="benif_id"/>\n                            <field name="talon_id"/>')
    cheque_views = cheque_views.replace('<field name="benif_id" readonly="1"/>', '<field name="benif_id" readonly="1"/>\n                <field name="talon_id" readonly="1"/>')
    
    # Add Menu
    if 'menu_finance2_talons' not in cheque_views:
        talon_menu = '    <menuitem id="menu_finance2_talons" name="Talons" parent="menu_finance2_root" action="action_finance2_talon" sequence="15"/>\n'
        cheque_views = cheque_views.replace('<menuitem id="menu_finance2_encaissement"', talon_menu + '    <menuitem id="menu_finance2_encaissement"')
        
    with open(cheque_views_path, 'w', encoding='utf-8') as f:
        f.write(cheque_views)

# 7. Update security
security_path = os.path.join(base_path, 'security', 'ir.model.access.csv')
with open(security_path, 'r', encoding='utf-8') as f:
    security = f.read()

if 'access_finance2_talon' not in security:
    security += "access_finance2_talon_user,finance2.talon_user,model_finance2_talon,finance_2.group_finance2_user,1,1,1,0\n"
    security += "access_finance2_talon_manager,finance2.talon_manager,model_finance2_talon,finance_2.group_finance2_manager,1,1,1,1\n"
    with open(security_path, 'w', encoding='utf-8') as f:
        f.write(security)

print("Talon implementation script completed.")
