from odoo import models, fields, api

class DailyReport(models.Model):
    _name = 'suivi_mediouna.daily_report'
    _description = 'Rapport Journalier'
    _rec_name = 'date'
    _order = 'date desc'

    date = fields.Date(string='Jour', required=True, default=fields.Date.context_today)
    ville = fields.Selection([
        ('mediouna', 'Mediouna'),
        ('agadir', 'Agadir')
    ], string='Ville', required=True, default='mediouna')
    
    production_jour = fields.Float(string='Production de ce jour', compute='_compute_report_data', store=True)
    charges_jour = fields.Float(string='Charges (Salaires)', compute='_compute_report_data', store=True)
    benefice = fields.Float(string='Bénéfice', compute='_compute_report_data', store=True)

    @api.depends('date', 'ville')
    def _compute_report_data(self):
        for record in self:
            if not record.date or not record.ville:
                record.production_jour = 0.0
                record.charges_jour = 0.0
                record.benefice = 0.0
                continue
            
            # Fetch production for this date and ville
            productions = self.env['suivi_mediouna.production'].search([
                ('date', '=', record.date),
                ('ville', '=', record.ville)
            ])
            prod_total = sum(productions.mapped('montant'))

            # Fetch daily records
            daily_records = self.env['suivi_mediouna.daily_record'].search([
                ('date', '=', record.date)
            ])
            
            charges_total = 0.0
            if daily_records:
                # Sum the total_jour of lines for this specific ville
                lines = daily_records.mapped('line_ids').filtered(lambda l: l.ville == record.ville)
                charges_total = sum(lines.mapped('total_jour'))

            record.production_jour = prod_total
            record.charges_jour = charges_total
            record.benefice = prod_total - charges_total

    def action_print_pdf(self):
        return self.env.ref('suivi_mediouna.action_report_daily').report_action(self)
