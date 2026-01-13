from odoo import models, fields

class DouaneDocument(models.Model):
    _name = 'douane.document'
    _description = 'Document Douane'

    entry_id = fields.Many2one('logistique.entry', string='Dossier', required=True, ondelete='cascade')
    
    type = fields.Selection([
        ('onssa', 'ONSSA'),
        ('invoice_prelevement', 'Facture prélévement'),
        ('analyse', 'Analyse'),
        ('bs', 'Bulletin de sortie'),
        ('dum', 'DUM'),
        ('estimation', 'Estimation'),
    ], string='Type de document', required=True)
    
    file = fields.Binary(string='Fichier', required=True, attachment=True)
    file_name = fields.Char(string='Nom du fichier')
    note = fields.Char(string='Note')
