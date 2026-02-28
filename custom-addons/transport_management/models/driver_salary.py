from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date

class TransportDriverMonthlySummary(models.Model):
    _name = 'transport.driver.monthly.summary'
    _description = 'Suivi Salaires Mensuels Chauffeur'
    _order = 'month desc'

    driver_id = fields.Many2one('transport.driver', string='Chauffeur', required=True, ondelete='cascade')
    month = fields.Char(string='Mois', required=True, help="Format: YYYY-MM")
    
    monthly_salary = fields.Float(string='Salaire Mensuel', required=True, readonly=True, help="Salaire mensuel de l'employé au moment de la création du suivi.")
    
    advance_ids = fields.One2many('transport.driver.advance', 'summary_id', string='Avances')
    
    total_advances = fields.Float(string='Total Avances', compute='_compute_total_advances', store=True)
    remaining_salary = fields.Float(string='Reste à payer', compute='_compute_remaining_salary', store=True)

    _sql_constraints = [
        ('driver_month_unique', 'unique(driver_id, month)', 'Un suivi existe déjà pour ce chauffeur et ce mois.')
    ]

    @api.depends('advance_ids.amount')
    def _compute_total_advances(self):
        for rec in self:
            rec.total_advances = sum(rec.advance_ids.mapped('amount'))

    @api.depends('monthly_salary', 'total_advances')
    def _compute_remaining_salary(self):
        for rec in self:
            rec.remaining_salary = rec.monthly_salary - rec.total_advances

class TransportDriverAdvance(models.Model):
    _name = 'transport.driver.advance'
    _description = 'Avance sur Salaire Chauffeur'
    _order = 'date desc'

    driver_id = fields.Many2one('transport.driver', string='Chauffeur', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    amount = fields.Float(string='Montant', required=True)
    comment = fields.Char(string='Commentaire')
    
    month = fields.Char(string='Mois', compute='_compute_month', store=True)
    summary_id = fields.Many2one('transport.driver.monthly.summary', string='Suivi Mensuel', ondelete='cascade', readonly=True)

    @api.depends('date')
    def _compute_month(self):
        for rec in self:
            if rec.date:
                rec.month = rec.date.strftime('%Y-%m')
            else:
                rec.month = False

    @api.model
    def create(self, vals):
        # 1. Ensure month is computed if date is provided in vals
        if 'date' in vals:
            target_date = fields.Date.from_string(vals['date'])
            month_str = target_date.strftime('%Y-%m')
            vals['month'] = month_str

        # 2. Get Driver
        driver_id = vals.get('driver_id')
        if not driver_id:
             raise ValidationError(_("Le chauffeur est obligatoire."))

        # 3. Find or Create Monthly Summary
        Summary = self.env['transport.driver.monthly.summary']
        summary = Summary.search([
            ('driver_id', '=', driver_id),
            ('month', '=', vals['month'])
        ], limit=1)

        if not summary:
            # Create new summary (Snapshot Salary)
            driver = self.env['transport.driver'].browse(driver_id)
            if not driver.employee_id:
                raise ValidationError(_("Impossible de créer une avance : Ce chauffeur n'est lié à aucun employé (pas de salaire de référence)."))
            
            # Use sudo() to bypass record rules (e.g. Suivi access) when reading the salary
            monthly_salary = driver.employee_id.sudo().monthly_salary
            
            summary = Summary.create({
                'driver_id': driver_id,
                'month': vals['month'],
                'monthly_salary': monthly_salary
            })

        vals['summary_id'] = summary.id
        
        # 4. Check Constraints (Pre-creation check for better UX, though post-create works too)
        # We need to simulate the addition.
        current_remaining = summary.remaining_salary
        if vals.get('amount', 0) > current_remaining:
             raise ValidationError(_(
                 "Le montant de l'avance (%(amount)s) dépasse le salaire restant pour ce mois (%(remaining)s).\n"
                 "Salaire Mensuel : %(salary)s\n"
                 "Total Déjà Avancé : %(advanced)s"
             ) % {
                 'amount': vals.get('amount', 0),
                 'remaining': current_remaining,
                 'salary': summary.monthly_salary,
                 'advanced': summary.total_advances
             })

        return super(TransportDriverAdvance, self).create(vals)

    def write(self, vals):
        # Prevent changing date if it changes the month (too complex to handle moving between summaries)
        if 'date' in vals:
            for rec in self:
                old_month = rec.month
                new_date = fields.Date.from_string(vals['date'])
                new_month = new_date.strftime('%Y-%m')
                if old_month != new_month:
                    raise ValidationError(_("Impossible de changer le mois d'une avance déjà enregistrée. Veuillez supprimer et recréer."))

        # Check constraint on amount change
        if 'amount' in vals:
            for rec in self:
                # Calculate what the new remaining would be
                diff = vals['amount'] - rec.amount
                if rec.summary_id.remaining_salary - diff < 0:
                     raise ValidationError(_(
                         "Le nouveau montant dépasse le salaire restant."
                     ))

        return super(TransportDriverAdvance, self).write(vals)
