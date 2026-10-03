from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CasaStockExit(models.Model):
    returned_qty = fields.Float(string='Quantité Retournée', compute='_compute_returned_qty', store=True)
    return_ids = fields.One2many('casa_field.stock.return', 'exit_id', string='Retours')

    @api.depends('return_ids.qty', 'return_ids.state')
    def _compute_returned_qty(self):
        for rec in self:
            rec.returned_qty = sum(rec.return_ids.filtered(lambda r: r.state == 'done').mapped('qty'))

    def action_view_returns(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Retours Client',
            'view_mode': 'tree,form',
            'res_model': 'casa_field.stock.return',
            'domain': [('exit_id', '=', self.id)],
            'context': {'default_exit_id': self.id},
        }

    _name = 'casa_field.stock.exit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Sortie Stock Casa'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', readonly=True, default='/')
    order_reference = fields.Char(string='Référence Commande')
    product_id = fields.Many2one('casa_field.stock.product', string='Produit', required=True)
    qty = fields.Float(string='Quantité', required=True)
    weight = fields.Float(string='Poids unit (Kg)')
    tonnage = fields.Float(string='Tonnage', compute='_compute_tonnage', store=True)
    

    
    date = fields.Date(string='Date', required=True)
    lot = fields.Char(string='Lot')
    dum = fields.Char(string='DUM')
    calibre = fields.Char(string='Calibre')
    
    
    frigo = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
        ('stock_casa', 'Stock Casa'),
    ], string='Frigo')
    
    client_id = fields.Many2one('casa_field.stock.client', string='Client')
    driver_id = fields.Many2one('casa_field.stock.driver', string='Chauffeur')
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Confirmé'),
        ('delivered', 'Livré'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', required=True)

    move_id = fields.Many2one('casa_field.stock.move', string='Mouvement Stock', readonly=True)
    cancel_move_id = fields.Many2one('casa_field.stock.move', string='Mouvement d\'Annulation', readonly=True)

    @api.depends('return_ids.qty', 'return_ids.state')
    def _compute_returned_qty(self):
        for rec in self:
            rec.returned_qty = sum(rec.return_ids.filtered(lambda r: r.state == 'done').mapped('qty'))

    def action_new_return(self):
        self.ensure_one()
        return {
            'name': 'Nouveau Retour',
            'type': 'ir.actions.act_window',
            'res_model': 'casa_field.stock.return',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_exit_id': self.id,
                'default_driver_id': self.driver_id.id,
            }
        }

    @api.depends('qty', 'weight')
    def _compute_tonnage(self):
        for rec in self:
            rec.tonnage = rec.qty * rec.weight

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('casa_field.stock.exit') or '/'
        return super(CasaStockExit, self).create(vals)

    def write(self, vals):
        for rec in self:
            if rec.state in ('done', 'delivered'):
                forbidden_fields = [
                    'product_id', 'qty', 'weight',
                    'date', 'lot', 'dum', 'frigo', 'client_id', 'driver_id'
                ]
                if any(f in vals for f in forbidden_fields):
                    raise UserError(_("Les opérations Confirmées ou Livrées ne peuvent pas être modifiées. Utilisez 'Annuler' et créez une nouvelle opération."))
        return super(CasaStockExit, self).write(vals)

    def action_register(self):
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
                rec._send_whatsapp_notification()
            elif rec.state == 'registered':
                if rec.move_id:
                    rec.move_id.write({'state': 'done', 'driver_id': rec.driver_id.id if rec.driver_id else False})
                rec.write({'state': 'done'})
                rec._send_whatsapp_notification()

    def _send_whatsapp_notification(self):
        import requests
        import logging
        _logger = logging.getLogger(__name__)
        
        for rec in self:
            try:
                client_name = rec.client_id.name if rec.client_id else 'Inconnu'
                driver_name = rec.driver_id.name if rec.driver_id else 'Inconnu'
                product_name = rec.product_id.name if rec.product_id else 'Produit'
                
                msg = "*Sortie de Stock*\n"
                msg += f"Client : {client_name}\n"
                msg += f"Chauffeur : {driver_name}\n"
                msg += f"Produit : {product_name}\n"
                msg += f"Quantité : {rec.qty} colis\n"
                msg += f"Poids unitaire : {rec.weight} Kg\n"
                msg += f"Tonnage Total : *{rec.tonnage} Kg*"
                
                payload = {
                    "group_id": "120363049891261462@g.us",
                    "text": msg
                }
                
                requests.post("http://172.17.0.1:3000/api/send", json=payload, timeout=5)
            except Exception as e:
                _logger.error(f"Failed to send WhatsApp notification for exit {rec.id}: {str(e)}")

    def action_cancel(self):
        for rec in self:
            if rec.state not in ('done', 'delivered'):
                raise UserError(_("Vous ne pouvez annuler que des sorties Confirmées ou Livrées."))
            
            if rec.return_ids.filtered(lambda r: r.state == 'done'):
                raise UserError(_("Impossible d'annuler une sortie ayant des retours clients confirmés. Veuillez d'abord annuler les retours associés."))

            # Create Reversal Move
            cancel_move = self.env['casa_field.stock.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'frigo': rec.frigo,
                'qty': rec.qty,
                'move_type': 'cancel_exit',
                'state': 'done',
                'date': fields.Datetime.now(),
                'reference': rec.name,

                'weight': rec.weight,
                'calibre': rec.calibre,
                'client_id': rec.client_id.id,
                'driver_id': rec.driver_id.id,
                'res_model': 'casa_field.stock.exit',
                'res_id': rec.id,
            })
            rec.write({
                'state': 'cancel',
                'cancel_move_id': cancel_move.id
            })

    def action_deliver(self):
        for rec in self:
            if rec.state != 'done':
                raise UserError(_("Seules les sorties à l'état 'Confirmé' peuvent être marquées comme 'Livré'."))
            rec.write({'state': 'delivered'})

    def action_reset_confirmed(self):
        for rec in self:
            if rec.state != 'delivered':
                raise UserError(_("Seules les sorties à l'état 'Livré' peuvent être remises en 'Confirmé'."))
            rec.write({'state': 'done'})

    @api.constrains('qty')
    def _check_qty_positive(self):
        for rec in self:
            if rec.qty <= 0:
                raise UserError(_("La Quantité doit être strictement positive."))
