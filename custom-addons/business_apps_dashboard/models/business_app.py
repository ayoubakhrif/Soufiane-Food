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
        
        action_id = False
        menu_id = False

        if self.target_type == 'action' and self.action_id:
            action_id = self.action_id.id
            # If we have a menu_id set manually, use it. Otherwise, let Odoo resolve it or it might be empty.
            if self.menu_id:
                menu_id = self.menu_id.id
        
        elif self.target_type == 'menu' and self.menu_id:
            menu_id = self.menu_id.id
            # Try to fund the action from the menu itself
            if self.menu_id.action:
                action_id = self.menu_id.action.id
            else:
                # If root menu has no action, find first child
                # We need to re-implement _get_target_menu or similar logic just to get the action ID
                target_menu = self._get_target_menu(self.menu_id)
                if target_menu and target_menu.action:
                    action_id = target_menu.action.id

        if menu_id:
            url = f'/web#menu_id={menu_id}'
            if action_id:
                url += f'&action={action_id}'
            
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'self',
            }
            
        return {'type': 'ir.actions.act_window_close'}

    def _get_target_menu(self, menu):
        """Recursively find the first menu (depth-first) that has an action."""
        if menu.action:
            return menu
            
        # Find children, ordered by sequence
        child_menus = self.env['ir.ui.menu'].search([
            ('parent_id', '=', menu.id)
        ], order='sequence,id')
        
        for child in child_menus:
             found = self._get_target_menu(child)
             if found:
                 return found
        return False
