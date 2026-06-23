from odoo import models, fields, api
from odoo.exceptions import ValidationError

class DocumentConfig(models.Model):
    _name = 'logistique.document.config'
    _description = 'Configuration de Document'

    name = fields.Selection([
        ('invoice', 'Facture Commerciale'),
        ('packing', 'Packing List'),
        ('bl', 'Bill of Lading'),
        ('fito', 'Fito Sanitaire'),
        ('origin', 'Certificate of Origin'),
        ('health', 'Health Certificate'),
        ('fumigation', 'Fumigation Certificate'),
        ('other', 'Autre')
    ], string='Document', required=True)

    line_ids = fields.One2many('logistique.document.config.line', 'config_id', string='Champs Requis')


class DocumentConfigLine(models.Model):
    _name = 'logistique.document.config.line'
    _description = 'Ligne de Configuration de Document'

    config_id = fields.Many2one('logistique.document.config', string='Configuration', ondelete='cascade')
    name = fields.Char(string='Champ', required=True)
    comment = fields.Char(string='Commentaire', help="Notes que l'IA doit prendre en considération")
    
    document_type = fields.Selection([
        ('invoice', 'Facture Commerciale'),
        ('packing', 'Packing List'),
        ('bl', 'Bill of Lading'),
        ('fito', 'Fito Sanitaire'),
        ('origin', 'Certificate of Origin'),
        ('health', 'Health Certificate'),
        ('fumigation', 'Fumigation Certificate'),
        ('other', 'Autre')
    ], string='Document Lié', required=False)

    @api.constrains('document_type')
    def _check_document_type(self):
        for line in self:
            if line.document_type and line.config_id and line.config_id.name == line.document_type:
                raise ValidationError("Le document lié ne peut pas être le même que le document principal de cette configuration.")
