from odoo import models, fields, api

class Kal3iyaAdvance(models.Model):
    _name = 'kal3iya.advance'
    _description = 'Avances'

client_id = fields.Many2one('kal3iya.client', required=True)
amount = fields.Float(required=True)
date_entry = fields.Date(required=True)
driver_id = fields.Many2one('kal3iya.driver')
note = fields.Char()
