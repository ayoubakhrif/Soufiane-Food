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
        config = self.env['suivi.presence.config'].get_main_config()
        off_in_med = config.official_check_in_mediouna if config else 9.0
        off_out_med = config.official_check_out_mediouna if config else 17.0
        off_in_agadir = config.official_check_in_agadir if config else 9.0
        off_out_agadir = config.official_check_out_agadir if config else 17.0
        
        ot_coeff = config.overtime_coefficient if config else 1.0

        for record in self:
            if not record.date:
                record.line_ids = [(5, 0, 0)]
                continue

            user_tz = pytz.timezone('Africa/Casablanca')
            dt_start = user_tz.localize(datetime.combine(record.date, time.min)).astimezone(pytz.utc)
            dt_end = user_tz.localize(datetime.combine(record.date, time.max)).astimezone(pytz.utc)

            employees = self.env['suivi.employee'].search([
                ('payroll_site', 'in', ['mediouna', 'agadir'])
            ])

            emp_data = {}
            for emp in employees:
                emp_data[emp] = {
                    'entree': False,
                    'sortie': False,
                    'ville': emp.payroll_site,
                    'site_travail': False,
                    'salaire_journalier': (emp.monthly_salary / 26.0) if emp.monthly_salary else 0.0,
                }

            presences = self.env['suivi.presence'].search([
                ('employee_id', 'in', employees.ids),
                ('datetime', '>=', dt_start),
                ('datetime', '<=', dt_end)
            ])

            for p in presences:
                emp = p.employee_id
                if emp in emp_data:
                    if p.type == 'entree':
                        emp_data[emp]['entree'] = p.datetime
                        emp_data[emp]['site_travail'] = p.site
                    elif p.type == 'sortie':
                        emp_data[emp]['sortie'] = p.datetime
                        # In case entry is missing but sortie exists
                        if not emp_data[emp]['site_travail']:
                            emp_data[emp]['site_travail'] = p.site

            lines = [(5, 0, 0)]
            for emp, data in emp_data.items():
                entree = data['entree']
                sortie = data['sortie']
                p_site = data['ville']
                site_travail = data['site_travail']

                
                heures_supp = 0.0
                montant_heures_supp = 0.0

                if entree and sortie:
                    local_in = entree.astimezone(user_tz)
                    local_out = sortie.astimezone(user_tz)
                    in_f = local_in.hour + local_in.minute / 60.0
                    out_f = local_out.hour + local_out.minute / 60.0
                    
                    if p_site == 'agadir':
                        c_off_in = off_in_agadir
                        c_off_out = off_out_agadir
                    else:
                        c_off_in = off_in_med
                        c_off_out = off_out_med
                    
                    std_hours = max(0, c_off_out - c_off_in)
                    worked_hours = max(0, out_f - in_f)
                    heures_supp = max(0, worked_hours - std_hours)

                    hourly_rate = 0.0
                    if std_hours > 0:
                        hourly_rate = data['salaire_journalier'] / std_hours
                        montant_heures_supp = heures_supp * hourly_rate * ot_coeff

                total_jour = data['salaire_journalier'] + montant_heures_supp

                lines.append((0, 0, {
                    'employee_id': emp.id,
                    'heure_entree': entree,
                    'heure_sortie': sortie,
                    'ville': p_site,
                    'salaire_journalier': data['salaire_journalier'],
                    'heures_supp': heures_supp,
                    'montant_heures_supp': montant_heures_supp,
                    'total_jour': total_jour,
                }))
            
            record.line_ids = lines

class DailyRecordLine(models.Model):
    _name = 'suivi_mediouna.daily_record.line'
    _description = 'Ligne de Record Journalier'
    _order = 'ville desc, employee_id asc'

    daily_record_id = fields.Many2one('suivi_mediouna.daily_record', string='Record', ondelete='cascade')
    employee_id = fields.Many2one('suivi.employee', string='Employé')
    heure_entree = fields.Datetime(string="Heure d'entrée")
    heure_sortie = fields.Datetime(string="Heure de sortie")
    ville = fields.Selection([
        ('mediouna', 'Mediouna'),
        ('casa', 'Casa'),
        ('agadir', 'Agadir')
    ], string='Ville de Travail')
    salaire_journalier = fields.Float(string='Salaire de Base (Jour)')
    heures_supp = fields.Float(string='Heures Supp.')
    montant_heures_supp = fields.Float(string='Montant H. Supp.')
    total_jour = fields.Float(string='Total Jour')

