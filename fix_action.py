import sys

with open("custom-addons/stock_casa_field/models/casa_field_stock_stock_exit.py", "r", encoding="utf-8") as f:
    content = f.read()

# We know where it starts
start_idx = content.find("def action_confirm(self):")
if start_idx != -1:
    end_pattern = "'move_id': move.id,\n            })"
    end_idx = content.find(end_pattern, start_idx) + len(end_pattern)
    
    old_code = content[start_idx:end_idx]
    
    new_code = """def action_register(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            
            domain = [
                ('product_id', '=', rec.product_id.id),
                ('lot', '=', rec.lot),
                ('dum', '=', rec.dum),
                ('frigo', '=', rec.frigo),
                ('state', '=', 'done')
            ]
            res = self.env['casa_field.stock.move'].read_group(domain, ['qty'], [])
            total_available = res[0]['qty'] if res and res[0]['qty'] else 0.0
            
            if rec.qty > total_available:
                raise UserError(_("Stock insuffisant ! Disponible : %s, Demandé : %s") % (total_available, rec.qty))
            
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
                    rec.move_id.write({'state': 'done', 'driver_id': rec.driver_id.id if rec.driver_id else False})
                rec.write({'state': 'done'})"""
    
    content = content[:start_idx] + new_code + content[end_idx:]

    with open("custom-addons/stock_casa_field/models/casa_field_stock_stock_exit.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Replaced successfully")
else:
    print("Could not find action_confirm")
