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
        
        if self.target_type == 'action' and self.action_id:
            return self.action_id.read()[0]
        
        elif self.target_type == 'menu' and self.menu_id:
            # URL Redirection to force App Switch
            # The backend cannot switch the top-level App Menu via context or params reliably.
            # The only way to switch the "App" (and top navigation bar) is to change the URL hash.
            # We redirect to /web#menu_id=<ROOT_ID>.
            
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web#menu_id={self.menu_id.id}',
                'target': 'self', # This replaces the current page, effectively switching apps
            }

        return {'type': 'ir.actions.act_window_close'}

    # _get_target_menu is no longer needed for this approach as we delegate resolution to the client via URL
    # checking for child actions is handled by Odoo's default menu loading logic.
