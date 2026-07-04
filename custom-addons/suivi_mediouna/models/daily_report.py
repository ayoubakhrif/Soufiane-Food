from odoo import models, fields, api

class DailyReport(models.Model):
    _name = 'suivi_mediouna.daily_report'
    _description = 'Rapport Journalier'
    _rec_name = 'date'
    _order = 'date desc'

    date = fields.Date(string='Jour', required=True, default=fields.Date.context_today)
    
    production_jour = fields.Float(string='Production de ce jour', compute='_compute_report_data', store=True)
    charges_jour = fields.Float(string='Charges de ce jour', compute='_compute_report_data', store=True)
    benefice = fields.Float(string='Bénéfice', compute='_compute_report_data', store=True)

    @api.depends('date')
    def _compute_report_data(self):
        for record in self:
            if not record.date:
                record.production_jour = 0.0
                record.charges_jour = 0.0
                record.benefice = 0.0
                continue
            
            # Fetch production
            productions = self.env['suivi_mediouna.production'].search([
                ('date', '=', record.date)
            ])
            prod_total = sum(productions.mapped('montant'))

            # Fetch daily records (charges)
            # Find the daily_record for this date
            daily_records = self.env['suivi_mediouna.daily_record'].search([
                ('date', '=', record.date)
            ])
            charges_total = 0.0
            if daily_records:
                # Sum the salaire_journalier of all lines in these records
                charges_total = sum(daily_records.mapped('line_ids.salaire_journalier'))
            else:
                # If no daily_record exists yet, we could force-fetch or just return 0.
                # Assuming the user creates a daily_record for the day to compute it.
                # Or we can compute it directly from presences.
                pass

            record.production_jour = prod_total
            record.charges_jour = charges_total
            record.benefice = prod_total - charges_total
