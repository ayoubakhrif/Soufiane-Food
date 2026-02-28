from odoo import models, fields

class AchatOrigin(models.Model):
    _name = 'achat.origin'
    _description = 'Purchase Origin'
    _order = 'name'

    name = fields.Char(
        string='Origin',
        required=True
    )

    code = fields.Char(
        string='Code',
        help="Short code (ex: ES, FR, BR)"
    )

    active = fields.Boolean(
        default=True
    )

    note = fields.Text(
        string='Notes'
    )

    _sql_constraints = [
        ('achat_origin_name_unique', 'unique(name)', 'This origin already exists.')
    ]
