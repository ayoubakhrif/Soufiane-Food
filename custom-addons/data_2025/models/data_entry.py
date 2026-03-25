from odoo import models, fields, api

class DataEntry(models.Model):
    _name = 'data.entry'
    _description = 'Entrée de Données 2025'
    _rec_name = 'bl'
    _order = 'id desc'

    bl = fields.Char(string='BL', required=True)
    article_id = fields.Many2one('achat.article', string='Article', required=True)
    ste_id = fields.Many2one('logistique.ste', string='Société', required=True)
    bad_date = fields.Date(string='Date of BAD')
    supplier_id = fields.Many2one('logistique.supplier', string='Supplier', required=True)
    eta = fields.Date(string='ETA')
    invoice = fields.Char(string='Invoice')
    free_time = fields.Integer(string='Free time')
    incoterm = fields.Selection([
        ('cfr', 'CFR'),
        ('fob', 'FOB'),
        ('emirate', 'EMIRATE'),
        ('exw', 'EXW'),
    ], string='Incoterm')
    surestarie = fields.Float(string='Surestarie')
    magasinage = fields.Float(string='Magasinage')
    thc = fields.Float(string='THC')
    freight = fields.Float(string='Freight')
    charge_transport = fields.Float(string='Charge de transport')
