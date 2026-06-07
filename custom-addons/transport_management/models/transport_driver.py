from odoo import models, fields, api

class TransportDriver(models.Model):
    _name = 'transport.driver'
    _description = 'Chauffeurs Transport'

    name = fields.Char(string='Nom', required=True)
    alias = fields.Char(string='Alias/Surnom')
    employee_id = fields.Many2one(
        'core.employee', 
        string='Employé', 
        domain="[('job_position_id.name', 'ilike', 'Chauffeur')]",
        help="Linked HR Employee. Filtered by job position 'Chauffeur'."
    )
    remorque = fields.Boolean(string='Remorque', default=False)

    
    current_monthly_salary = fields.Float(
        string='Salaire Actuel', 
        compute='_compute_current_monthly_salary',
        help="Salaire actuel défini dans la fiche employé."
    )

    monthly_summary_ids = fields.One2many('transport.driver.monthly.summary', 'driver_id', string='Suivi Salaire')
    advance_ids = fields.One2many('transport.driver.advance', 'driver_id', string='Avances')
    
    trip_ids = fields.One2many('transport.trip', 'driver_id', string='Voyages')
    remorque_trip_ids = fields.One2many('transport.trip.remorque', 'driver_remorque_id', string='Voyages Remorque')

    total_trip_count = fields.Integer(
        string='Nombre de Voyages',
        compute='_compute_total_trip_count',
        store=False
    )

    @api.depends('trip_ids', 'remorque_trip_ids')
    def _compute_total_trip_count(self):
        for rec in self:
            rec.total_trip_count = len(rec.trip_ids) + len(rec.remorque_trip_ids)

    @api.depends('employee_id')
    def _compute_current_monthly_salary(self):
        for rec in self:
            if rec.employee_id:
                # Use sudo() to allow transport users to see the salary without full HR access
                rec.current_monthly_salary = rec.employee_id.sudo().monthly_salary
            else:
                rec.current_monthly_salary = 0.0
