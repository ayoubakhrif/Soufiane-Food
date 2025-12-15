from odoo import models, fields, api

class BusinessApp(models.Model):
    _name = 'business.app'
    _description = 'Business Application'
    _order = 'sequence, id'

    name = fields.Char(string='App Name', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)
    icon = fields.Image(string='Icon', max_width=128, max_height=128)
    background_color = fields.Char(string='Background Color', default='#FFFFFF', help="Hex color code (e.g., #FFFFFF)")
    sequence = fields.Integer(string='Sequence', default=10)
    
    target_type = fields.Selection([
        ('menu', 'Menu'),
        ('action', 'Action')
    ], string='Target Type', required=True, default='menu')
    
    menu_id = fields.Many2one('ir.ui.menu', string='Menu to Open')
    action_id = fields.Reference(selection=[('ir.actions.act_window', 'Window Action'), ('ir.actions.client', 'Client Action'), ('ir.actions.report', 'Report Action')], string='Action to Trigger')
    
    group_ids = fields.Many2many('res.groups', string='Allowed Groups', help="Users in these groups will see this app.")

    def open_app(self):
        self.ensure_one()
        if self.target_type == 'menu' and self.menu_id:
            # Redirect to the menu. The web client handles menu IDs usually by hash.
            # However, returning an action that points to a menu isn't standard in Odoo backend actions directly.
            # We usually return the action associated with the menu.
            if self.menu_id.action:
                action = self.menu_id.action.read()[0]
                # We can also add a context to highlight the menu if needed, 
                # but Odoo 17 web client handles routing via menu_id in URL.
                return action
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',  # Fallback if no action
            }

        elif self.target_type == 'action' and self.action_id:
            return self.action_id.read()[0]
            
        return {'type': 'ir.actions.act_window_close'}
