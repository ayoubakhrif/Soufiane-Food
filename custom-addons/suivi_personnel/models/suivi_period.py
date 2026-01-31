from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class SuiviPeriod(models.Model):
    _name = 'suivi.period'
    _description = 'Période Comptable'
    _order = 'date_start desc'

    name = fields.Char(string='Période', required=True)
    date_start = fields.Date(string='Date Début', required=True)
    date_end = fields.Date(string='Date Fin', required=True)
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'La période doit être unique !'),
    ]
