from odoo import models, fields, api

class AuditTest(models.Model):
    _name = 'audit.test'
    _description = 'Test Audit'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Titre', required=True, tracking=True)
    test_type = fields.Selection([
        ('exactitude', 'Exactitude'),
        ('cutoff', 'Cut-off'),
        ('classification', 'Classification')
    ], string='Test', required=True, tracking=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)
    
    document_ids = fields.Many2many(
        'ir.attachment', 
        'audit_test_ir_attachment_rel', 
        'test_id', 
        'attachment_id', 
        string='Documents (PDFs)'
    )
