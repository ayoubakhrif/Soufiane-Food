import sys

with open("custom-addons/stock_casa_field/models/casa_field_stock_stock_exit.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add state
old_state = """    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'ConfirmÃ©'),
        ('delivered', 'LivrÃ©'),
        ('cancel', 'AnnulÃ©'),
    ], string='Ã‰tat', default='draft', required=True)"""
new_state = """    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('registered', 'Enregistré'),
        ('done', 'Confirmé'),
        ('delivered', 'Livré'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', required=True)"""
content = content.replace(old_state, new_state)

# Add action_register and update action_confirm
old_action_confirm = """    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue

            # Create Stock Move
            move = self.env['casa_field.stock.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'frigo': rec.frigo,
                'qty': -rec.qty,
                'weight': rec.weight,
                'calibre': rec.calibre,
                'move_type': 'exit',
                'state': 'done',
                'date': rec.date,
                'reference': rec.name,
                'res_model': 'casa_field.stock.exit',
                'res_id': rec.id,
                'client_id': rec.client_id.id if rec.client_id else False,
                'driver_id': rec.driver_id.id if rec.driver_id else False,
            })
            
            rec.write({
                'state': 'done',
                'move_id': move.id,
            })"""

new_actions = """    def action_register(self):
        for rec in self:
            if rec.state != 'draft':
                continue
                
            # Create Stock Move in registered state
            move = self.env['casa_field.stock.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'frigo': rec.frigo,
                'qty': -rec.qty,
                'weight': rec.weight,
                'calibre': rec.calibre,
                'move_type': 'exit',
                'state': 'registered',
                'date': rec.date,
                'reference': rec.name,
                'res_model': 'casa_field.stock.exit',
                'res_id': rec.id,
                'client_id': rec.client_id.id if rec.client_id else False,
                'driver_id': rec.driver_id.id if rec.driver_id else False,
            })
            
            rec.write({
                'state': 'registered',
                'move_id': move.id,
            })

    def action_confirm(self):
        for rec in self:
            if rec.state not in ['draft', 'registered']:
                continue

            if rec.state == 'draft':
                # Create Stock Move
                move = self.env['casa_field.stock.move'].create({
                    'product_id': rec.product_id.id,
                    'lot': rec.lot,
                    'dum': rec.dum,
                    'frigo': rec.frigo,
                    'qty': -rec.qty,
                    'weight': rec.weight,
                    'calibre': rec.calibre,
                    'move_type': 'exit',
                    'state': 'done',
                    'date': rec.date,
                    'reference': rec.name,
                    'res_model': 'casa_field.stock.exit',
                    'res_id': rec.id,
                    'client_id': rec.client_id.id if rec.client_id else False,
                    'driver_id': rec.driver_id.id if rec.driver_id else False,
                })
                rec.write({'state': 'done', 'move_id': move.id})
            elif rec.state == 'registered':
                if rec.move_id:
                    rec.move_id.write({'state': 'done'})
                rec.write({'state': 'done'})"""
content = content.replace(old_action_confirm, new_actions)

with open("custom-addons/stock_casa_field/models/casa_field_stock_stock_exit.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated exit model")
