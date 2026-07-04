from odoo import models, fields, api
import pytz
from datetime import datetime, time

class DailyRecord(models.Model):
    _name = 'suivi_mediouna.daily_record'
    _description = 'Record Journalier'
    _rec_name = 'date'
    _order = 'date desc'

    date = fields.Date(string='Jour', required=True, default=fields.Date.context_today)
    
    line_ids = fields.One2many(
        'suivi_mediouna.daily_record.line', 
        'daily_record_id', 
        string='Employés', 
        compute='_compute_line_ids', 
        store=True,
        readonly=True
    )

    @api.depends('date')
    def _compute_line_ids(self):
        for record in self:
            if not record.date:
                record.line_ids = [(5, 0, 0)]
                continue

            user_tz = pytz.timezone('Africa/Casablanca')
            # Convert date to datetime at start and end of day in target TZ, then to UTC
            dt_start = user_tz.localize(datetime.combine(record.date, time.min)).astimezone(pytz.utc)
            dt_end = user_tz.localize(datetime.combine(record.date, time.max)).astimezone(pytz.utc)

            # Fetch presences for the day in Mediouna and Agadir
            presences = self.env['suivi.presence'].search([
                ('datetime', '>=', dt_start),
                ('datetime', '<=', dt_end),
                ('site', 'in', ['mediouna', 'agadir'])
            ])

            # Group by employee
            emp_data = {}
            for p in presences:
                emp = p.employee_id
                if emp not in emp_data:
                    emp_data[emp] = {
                        'entree': False,
                        'sortie': False,
                        'ville': p.site,
                        'salaire_journalier': (emp.monthly_salary / 26.0) if emp.monthly_salary else 0.0
                    }
                
                if p.type == 'entree':
                    emp_data[emp]['entree'] = p.datetime
                elif p.type == 'sortie':
                    emp_data[emp]['sortie'] = p.datetime

            # Create lines
            lines = [(5, 0, 0)]
            for emp, data in emp_data.items():
                lines.append((0, 0, {
                    'employee_id': emp.id,
                    'heure_entree': data['entree'],
                    'heure_sortie': data['sortie'],
                    'ville': data['ville'],
                    'salaire_journalier': data['salaire_journalier'],
                }))
            
            record.line_ids = lines

class DailyRecordLine(models.Model):
    _name = 'suivi_mediouna.daily_record.line'
    _description = 'Ligne de Record Journalier'

    daily_record_id = fields.Many2one('suivi_mediouna.daily_record', string='Record', ondelete='cascade')
    employee_id = fields.Many2one('suivi.employee', string='Employé')
    heure_entree = fields.Datetime(string="Heure d'entrée")
    heure_sortie = fields.Datetime(string="Heure de sortie")
    ville = fields.Selection([
        ('mediouna', 'Mediouna'),
        ('casa', 'Casa'),
        ('agadir', 'Agadir')
    ], string='Ville de Travail')
    salaire_journalier = fields.Float(string='Salaire Journalier')
