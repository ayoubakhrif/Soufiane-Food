from odoo import models, fields, api
from odoo.exceptions import ValidationError
import base64

class CoreEmployeeDocument(models.Model):
    _name = 'core.employee.document'
    _description = 'Employee Documents'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    employee_id = fields.Many2one(
        'core.employee',
        string='Employee',
        required=True,
        ondelete='cascade'
    )

    doc_type = fields.Selection([
        ('cdd', 'Contrat CDD'),
        ('cdi', 'Contrat CDI'),
        ('procuration', 'Procuration engagement'),
        ('cin', 'CIN'),
        ('diplome', 'Diplôme'),
    ], string='Type de document', required=True, tracking=True)

    document_file = fields.Binary(
        string='Document',
        required=True,
        attachment=True
    )
    filename = fields.Char(string='Nom du fichier')

    issue_date = fields.Date(string='Date d’éxpiration')
    note = fields.Text(string='Remarque')

    @api.constrains('employee_id', 'doc_type')
    def _check_unique_document(self):
        for rec in self:
            domain = [
                ('employee_id', '=', rec.employee_id.id),
                ('doc_type', '=', rec.doc_type),
                ('id', '!=', rec.id),
            ]
            if self.search_count(domain):
                raise ValidationError("Un document de ce type existe déjà pour cet employé.")

    @api.constrains('document_file')
    def _check_file_size(self):
        MAX_SIZE = 5 * 1024 * 1024  # 5 Mo
        for rec in self:
            if rec.document_file:
                file_size = len(base64.b64decode(rec.document_file))
                if file_size > MAX_SIZE:
                    raise ValidationError(
                        "Le fichier PDF ne doit pas dépasser 5 Mo."
                    )