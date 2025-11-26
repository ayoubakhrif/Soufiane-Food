from odoo import models, fields, api

class Kal3iyadriver(models.Model):
    _name = 'kal3iya.driver'
    _description = 'Chauffeurs'

    name = fields.Char(string='Chauffeur', required=True)
    phone = fields.Char(string='Téléphone')
    advance_ids = fields.One2many('kal3iya.advance', 'driver_id', string='Avances')
    total_avance = fields.Float(string='Total avances', compute='_compute_total_advance', store=True)

    @api.depends('advance_ids.amount')
    def _compute_total_advance(self):
        for rec in self:
            rec.total_advance = sum(rec.advance_ids.mapped('amount'))
