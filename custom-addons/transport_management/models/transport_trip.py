from odoo import models, fields, api
from datetime import date
from calendar import monthrange

class TransportTrip(models.Model):
    _name = 'transport.trip'
    _description = 'Transport Trip'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    date = fields.Date(string='Date de voyage', required=True, default=fields.Date.context_today)
    driver_id = fields.Many2one('transport.driver', string='Chauffeur', required=True, tracking=True)
    client_id = fields.Many2one('transport.client', string='Client', required=True, tracking=True)
    
    # Deprecated fields (kept for data safety, but hidden in views)
    driver = fields.Char(string='Chauffeur (Legacy)')
    client = fields.Char(string='Client (Legacy)')
    
    trip_type = fields.Selection([
        ('tanger_med', 'Tanger Med'),
        ('soufiane', 'Soufiane'),
        ('la_zone', 'La zone'),
        ('client', 'Client'),
        ('mestapha', 'Mestapha'),
    ], string='Type de voyage', tracking=True)
    charge_fuel = fields.Float(string='Gazoil', tracking=True)
    charge_driver = fields.Float(string='Déplacement Chauffeur', tracking=True)
    charge_adblue = fields.Float(string='AdBlue', tracking=True)
    charge_salary = fields.Float(
        string='Salaire',
        store=True,
        tracking=True
    )
    charge_mixed = fields.Float(string='Mixe (A préciser sur commentaire)', tracking=True)
    note = fields.Text(string='Commentaire (Mixe)')
    going_price = fields.Float(string='Prix allée', tracking=True)
    returning_price = fields.Float(string='Prix de retour', tracking=True)
    total_price = fields.Float(
        string='Prix allée retour',
        compute='_compute_total_price',
        store=True,
        tracking=True
    )
    profit = fields.Float(
        string='Bénéfice',
        compute='_compute_profit',
        store=True,
        tracking=True
    )
    is_paid = fields.Boolean(string='Payé', default=False, tracking=True)
    total_amount = fields.Float(
        string='Montant des charges',
        compute='_compute_total_amount',
        store=True,
        tracking=True
    )

    def action_confirm_paid(self):
        for record in self:
            record.is_paid = True

    def action_set_unpaid(self):
        for record in self:
            record.is_paid = False

    @api.depends(
        'charge_fuel',
        'charge_driver',
        'charge_adblue',
        'charge_mixed',
        'charge_salary'
    )
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = (
                (record.charge_fuel or 0.0) +
                (record.charge_driver or 0.0) +
                (record.charge_adblue or 0.0) +
                (record.charge_mixed or 0.0) +
                (record.charge_salary or 0.0) 
            )

    @api.depends('going_price', 'returning_price')
    def _compute_total_price(self):
        for rec in self:
            rec.total_price = rec.going_price + rec.returning_price

    @api.depends('total_price', 'total_amount')
    def _compute_profit(self):
        for rec in self:
            rec.profit = rec.total_price - rec.total_amount



    
    def _recompute_monthly_salary(self, driver_id, trip_date):
        """
        Recompute salary allocation for all trips of a specific driver in a specific month.
        This ensures that the monthly salary is evenly distributed across valid trips.
        """
        if not driver_id or not trip_date:
            return

        # 1. Determine the month range
        if isinstance(trip_date, str):
            trip_date = fields.Date.from_string(trip_date)
            
        month_start = trip_date.replace(day=1)
        month_end = trip_date.replace(day=monthrange(trip_date.year, trip_date.month)[1])

        # 2. Fetch Driver's Monthly Salary
        driver = self.env['transport.driver'].browse(driver_id)
        employee = driver.employee_id
        
        # Safety check: If no salary is defined, set charge to 0.0
        monthly_salary = employee.monthly_salary if employee else 0.0

        # 3. Find all trips for this driver in this month
        trips = self.search([
            ('driver_id', '=', driver_id),
            ('date', '>=', month_start),
            ('date', '<=', month_end),
        ])

        trip_count = len(trips)

        # 4. Calculate Allocation
        if trip_count > 0:
            if monthly_salary > 0:
                salary_per_trip = monthly_salary / trip_count
            else:
                salary_per_trip = 0.0
            
            # 5. Update trips (avoid recursion loop using basic write if needed, though safe here)
            # We use write, but since charge_salary is not a computed field anymore and 
            # we are not triggering write on driver_id/date, no infinite loop should occur.
            trips.write({'charge_salary': salary_per_trip})

    @api.model
    def create(self, vals):
        record = super().create(vals)
        # Recompute for the new trip's context
        if record.driver_id and record.date:
            self._recompute_monthly_salary(record.driver_id.id, record.date)
        return record
    
    def write(self, vals):
        # 1. Capture contexts BEFORE write (old state)
        # We only care if driver_id or date is changing, but checking everything is safer/easier
        contexts_to_recompute = set()
        for rec in self:
            if rec.driver_id and rec.date:
                contexts_to_recompute.add((rec.driver_id.id, rec.date))

        # 2. Perform Write
        res = super().write(vals)

        # 3. Capture contexts AFTER write (new state)
        for rec in self:
            if rec.driver_id and rec.date:
                contexts_to_recompute.add((rec.driver_id.id, rec.date))

        # 4. Recompute all affected contexts
        for driver_id, trip_date in contexts_to_recompute:
            self._recompute_monthly_salary(driver_id, trip_date)

        return res

    def unlink(self):
        # 1. Capture contexts BEFORE unlink
        contexts_to_recompute = set()
        for rec in self:
            if rec.driver_id and rec.date:
                contexts_to_recompute.add((rec.driver_id.id, rec.date))

        # 2. Perform Unlink
        res = super().unlink()

        # 3. Recompute remaining trips in those contexts
        for driver_id, trip_date in contexts_to_recompute:
            self._recompute_monthly_salary(driver_id, trip_date)

        return res