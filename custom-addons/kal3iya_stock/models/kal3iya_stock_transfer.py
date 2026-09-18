from odoo import models, fields, api, _
from odoo.exceptions import UserError

class Kal3iyaStockTransfer(models.Model):
    _name = 'kal3iya.stock.transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Transfert Stock Kal3iya entre Garages'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', readonly=True, default='/')
    product_id = fields.Many2one('kal3iya.stock.product', string='Produit', required=True)
    qty = fields.Float(string='Quantité', required=True)
    weight = fields.Float(string='Poids (Kg)')
    tonnage = fields.Float(string='Tonnage', compute='_compute_tonnage', store=True)

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    lot = fields.Char(string='Lot')
    dum = fields.Char(string='DUM')
    calibre = fields.Char(string='Calibre')

    garage_source = fields.Selection([
        ('garage1', 'Garage 1'),
        ('garage2', 'Garage 2'),
        ('garage3', 'Garage 3'),
        ('garage4', 'Garage 4'),
        ('garage5', 'Garage 5'),
        ('garage6', 'Garage 6'),
        ('garage7', 'Garage 7'),
        ('garage8', 'Garage 8'),
        ('terrasse', 'Terrasse'),
        ('fenidek', 'Fenidek'),
    ], string='Garage Source', required=True)

    garage_dest = fields.Selection([
        ('garage1', 'Garage 1'),
        ('garage2', 'Garage 2'),
        ('garage3', 'Garage 3'),
        ('garage4', 'Garage 4'),
        ('garage5', 'Garage 5'),
        ('garage6', 'Garage 6'),
        ('garage7', 'Garage 7'),
        ('garage8', 'Garage 8'),
        ('terrasse', 'Terrasse'),
        ('fenidek', 'Fenidek'),
    ], string='Garage Destination', required=True)

    frigo_source = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
        ('stock_kal3iya', 'Stock Kal3iya'),
    ], string='Frigo Source')

    frigo_dest = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
        ('stock_kal3iya', 'Stock Kal3iya'),
    ], string='Frigo Destination', default='stock_kal3iya')

    ste_id = fields.Many2one('kal3iya.stock.ste', string='Société')
    agent_id = fields.Many2one('kal3iya.stock.agent', string='Agent de Stock')

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Confirmé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', required=True)

    move_out_id = fields.Many2one('kal3iya.stock.move', string='Mouvement Sortie Source', readonly=True)
    move_in_id = fields.Many2one('kal3iya.stock.move', string='Mouvement Entrée Cible', readonly=True)

    @api.depends('qty', 'weight')
    def _compute_tonnage(self):
        for rec in self:
            rec.tonnage = rec.qty * (rec.weight or 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('kal3iya.stock.transfer') or '/'
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            if rec.qty <= 0:
                raise UserError(_("La quantité transférée doit être supérieure à zéro."))
            if rec.garage_source == rec.garage_dest and rec.frigo_source == rec.frigo_dest:
                raise UserError(_("Le garage source et le garage de destination doivent être différents."))

            # 1. Mouvement de sortie (garage source, qté négative)
            move_out = self.env['kal3iya.stock.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'calibre': rec.calibre,
                'weight': rec.weight,
                'garage': rec.garage_source,
                'frigo': rec.frigo_source,
                'ste_id': rec.ste_id.id if rec.ste_id else False,
                'qty': -abs(rec.qty),
                'move_type': 'exit',
                'reference': f"{rec.name} (Sortie Transfert)",
                'res_model': rec._name,
                'res_id': rec.id,
                'date': rec.date,
            })

            # 2. Mouvement d'entrée (garage destination, qté positive)
            move_in = self.env['kal3iya.stock.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'calibre': rec.calibre,
                'weight': rec.weight,
                'garage': rec.garage_dest,
                'frigo': rec.frigo_dest,
                'ste_id': rec.ste_id.id if rec.ste_id else False,
                'qty': abs(rec.qty),
                'move_type': 'entry',
                'reference': f"{rec.name} (Entrée Transfert)",
                'res_model': rec._name,
                'res_id': rec.id,
                'date': rec.date,
            })

            rec.write({
                'move_out_id': move_out.id,
                'move_in_id': move_in.id,
                'state': 'done',
            })

    def action_cancel(self):
        for rec in self:
            if rec.state != 'done':
                continue
            # Reversal
            if rec.move_out_id:
                self.env['kal3iya.stock.move'].create({
                    'product_id': rec.product_id.id,
                    'lot': rec.lot,
                    'dum': rec.dum,
                    'calibre': rec.calibre,
                    'weight': rec.weight,
                    'garage': rec.garage_source,
                    'frigo': rec.frigo_source,
                    'ste_id': rec.ste_id.id if rec.ste_id else False,
                    'qty': abs(rec.qty),
                    'move_type': 'cancel_exit',
                    'reference': f"Reversal {rec.name}",
                    'res_model': rec._name,
                    'res_id': rec.id,
                })
            if rec.move_in_id:
                self.env['kal3iya.stock.move'].create({
                    'product_id': rec.product_id.id,
                    'lot': rec.lot,
                    'dum': rec.dum,
                    'calibre': rec.calibre,
                    'weight': rec.weight,
                    'garage': rec.garage_dest,
                    'frigo': rec.frigo_dest,
                    'ste_id': rec.ste_id.id if rec.ste_id else False,
                    'qty': -abs(rec.qty),
                    'move_type': 'cancel_entry',
                    'reference': f"Reversal {rec.name}",
                    'res_model': rec._name,
                    'res_id': rec.id,
                })
            rec.write({'state': 'cancel'})
