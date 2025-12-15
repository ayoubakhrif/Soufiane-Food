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
        action_data = False
        
        if self.target_type == 'action' and self.action_id:
            action_data = self.action_id.read()[0]
        
        elif self.target_type == 'menu' and self.menu_id:
            # Recursive lookup to find the first actionable menu
            target_menu = self._get_target_menu(self.menu_id)
            if target_menu and target_menu.action:
                action_data = target_menu.action.read()[0]
                
                # IMPORTANT: Set the active_id to the menu_id so the web client highlights the menu
                # We add 'menu_id' to the context, although standard actions use params.
                # However, resetting the breadcrumbs is handled by the client when switching apps.
                # We can try to clear breadcrumbs by using target='main' if applicable, 
                # but simply opening the action is usually standard.
                if not action_data.get('help'):
                     action_data['help'] = f'<p>Opened via Business App: {self.name}</p>'

        if action_data:
            # Return the action
            return action_data
        
        # Fallback: Reload if nothing found (shouldn't happen if configured correctly)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload', 
        }

    def _get_target_menu(self, menu):
        """Recursively find the first menu (depth-first) that has an action."""
        if menu.action:
            return menu
            
        # Find children, ordered by sequence
        # The search method implicitly filters by user access rights (ACLs/Groups)
        child_menus = self.env['ir.ui.menu'].search([
            ('parent_id', '=', menu.id)
        ], order='sequence,id')
        
        for child in child_menus:
             found = self._get_target_menu(child)
             if found:
                 return found
        return False
