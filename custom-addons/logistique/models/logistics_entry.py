from odoo import models, fields

class LogisticsEntry(models.Model):
    _name = 'logistique.entry'
    _description = 'Dossier Logistique'
    _rec_name = 'container_id'

    week = fields.Char(string='Semaine')
    prov_number = fields.Char(string='N° Prov')
    status = fields.Selection([
        ('in_progress', 'In Progress'),
        ('get_out', 'Get Out'),
        ('closed', 'Closed'),
    ], string='Status', default='in_progress')
    
    def_number = fields.Char(string='N° Def')
    
    ste_id = fields.Many2one('logistique.ste', string='Company (Ste)')
    supplier_id = fields.Many2one('logistique.supplier', string='Supplier')
    invoice_number = fields.Char(string='Invoice Number')
    article_id = fields.Many2one('logistique.article', string='Article')
    details = fields.Char(string='Details')
    weight = fields.Float(string='Weight')
    incoterm = fields.Char(string='Incoterm')
    free_time = fields.Integer(string='Free Time')
    shipping_id = fields.Many2one('logistique.shipping', string='Shipping Company')
    
    container_id = fields.Many2one('logistique.container', string='Container')
    
    bl_number = fields.Char(string='BL Number')
    eta = fields.Date(string='ETA')
    doc_status = fields.Char(string='Document Status')
    remarks = fields.Char(string='Remarks')
