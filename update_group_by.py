import os

base_path = r'c:\odoo-repos\Soufiane-Food\custom-addons\finance_2'
comparison_py = os.path.join(base_path, 'models', 'comparison.py')
comparison_views = os.path.join(base_path, 'views', 'comparison_views.xml')

# 1. Add line_count field in comparison.py
with open(comparison_py, 'r', encoding='utf-8') as f:
    content = f.read()

if 'line_count = fields.Integer' not in content:
    content = content.replace(
        "line_ids = fields.One2many('finance2.comparison.line', 'comparison_id', string='Résultats')",
        "line_ids = fields.One2many('finance2.comparison.line', 'comparison_id', string='Résultats')\n    line_count = fields.Integer(compute='_compute_line_count', string='Nombre de lignes')"
    )
    
    compute_method = """
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    def action_view_lines(self):
        self.ensure_one()
        return {
            'name': 'Lignes d\\'Audit',
            'type': 'ir.actions.act_window',
            'res_model': 'finance2.comparison.line',
            'view_mode': 'tree,form',
            'domain': [('comparison_id', '=', self.id)],
            'context': {'search_default_group_status': 1},
        }
"""
    content = content.replace("def action_run_comparison(self):", compute_method + "\n    def action_run_comparison(self):")
    with open(comparison_py, 'w', encoding='utf-8') as f:
        f.write(content)

# 2. Add Smart Button in XML and update tree
with open(comparison_views, 'r', encoding='utf-8') as f:
    xml_content = f.read()

# Add smart button inside <sheet>
if 'name="action_view_lines"' not in xml_content:
    smart_button = """
                    <div class="oe_button_box" name="button_box">
                        <button name="action_view_lines" type="object" class="oe_stat_button" icon="fa-list">
                            <field name="line_count" widget="statinfo" string="Résultats"/>
                        </button>
                    </div>
"""
    xml_content = xml_content.replace("<sheet>\n", "<sheet>\n" + smart_button)

# Also create the action for lines if missing so it can be called (wait, action is returned as dict so it's fine, but let's define a standalone tree for it)
tree_line = """
    <record id="view_finance2_comparison_line_tree" model="ir.ui.view">
        <field name="name">finance2.comparison.line.tree</field>
        <field name="model">finance2.comparison.line</field>
        <field name="arch" type="xml">
            <tree string="Résultats de l'Audit" decoration-danger="status == 'only_v1'" decoration-warning="status == 'diff'" decoration-info="status == 'only_v2'" decoration-success="status == 'ok'">
                <field name="cheque_number"/>
                <field name="ste_name"/>
                <field name="status" widget="badge" decoration-danger="status == 'only_v1'" decoration-warning="status == 'diff'" decoration-info="status == 'only_v2'" decoration-success="status == 'ok'"/>
                <field name="v1_amount"/>
                <field name="v2_amount"/>
                <field name="diff_details"/>
            </tree>
        </field>
    </record>
"""
if 'name="finance2.comparison.line.tree"' not in xml_content:
    xml_content = xml_content.replace('<!-- Vue Formulaire pour l\'Audit (Run) -->', tree_line + '\n    <!-- Vue Formulaire pour l\'Audit (Run) -->')
    
with open(comparison_views, 'w', encoding='utf-8') as f:
    f.write(xml_content)

print("Smart button and line_count added.")
