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
                
                # CONTEXT INJECTION:
                # We must tell the web client that the 'active' root menu is self.menu_id
                # (e.g. Finance), even though we are opening a sub-action (e.g. Saisie).
                # This ensures the top navigation bar switches to the correct App.
                
                context_str = action_data.get('context', '{}')
                # Determine if context is a string or dict (read() usually returns string for context field)
                if isinstance(context_str, str):
                    # We append our key safely
                    context_str = context_str.strip()
                    if context_str == '{}':
                         action_data['context'] = f"{{'menu_id': {self.menu_id.id}}}"
                    else:
                        # Remove trailing brace, add comma, add our key, close brace
                        # A bit hacky string manipulation but standard for preserving complex python contexts
                        # Alternatively, we can rely on the client accepting a dict if we parse it,
                        # but keeping it as a string is safer for existing eval contexts.
                        action_data['context'] = f"{context_str[:-1]}, 'menu_id': {self.menu_id.id}}}"
                elif isinstance(context_str, dict):
                    context_str['menu_id'] = self.menu_id.id
                    action_data['context'] = context_str

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
