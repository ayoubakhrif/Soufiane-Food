from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta

class FinanceEffet(models.Model):
    _name = 'finance.effet'
    _description = 'Finance Effet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'serie'

    # Required Fields
    emitter = fields.Selection([
        ('nawfal', 'Nawfal'),
        ('dahrouch', 'Dahrouch'),
        ('talon', 'Talon')
    ], string='Émetteur', required=True, tracking=True)
    
    serie = fields.Char(string='Série / Référence', required=True, tracking=True)
    
    date_emission = fields.Date(string='Date d’émission', required=True, default=fields.Date.context_today, tracking=True)
    date_echeance = fields.Date(string='Date d’échéance', required=True, tracking=True)
    date_encaissement = fields.Date(string='Date d’encaissement', tracking=True)
    
    ste_id = fields.Many2one('finance.ste', string='Société', required=True, tracking=True)
    benif_id = fields.Many2one('finance.benif', string='Bénificiaire', required=True, tracking=True)
    talon_id = fields.Many2one('finance.talon', string='Talon', tracking=True, domain="[('ste_id', '=', ste_id)]")
    
    montant = fields.Float(string='Montant', required=True, tracking=True)
    comment = fields.Text(string='Commentaire', tracking=True)

    # Computed Fields
    state = fields.Selection([
        ('encaisse', 'Encaissé'),
        ('non_encaisse', 'Non encaissé'),
    ], string='État', compute='_compute_state', store=True, tracking=True)

    # Business Logic
    @api.depends('date_encaissement')
    def _compute_state(self):
        for rec in self:
            if rec.date_encaissement:
                rec.state = 'encaisse'
            else:
                rec.state = 'non_encaisse'

    # -------------------------------------------------------------------
    # Calculate TALON
    # -------------------------------------------------------------------
    def _find_talon_logic(self):
        self.ensure_one()
        if not self.serie or not self.ste_id:
            return False
            
        if not self.serie.isdigit():
            return False

        serie_num = int(self.serie)

        talons = self.env['finance.talon'].search([
            ('ste_id', '=', self.ste_id.id),
            ('num_chq', '>', 0),
            ('name', '!=', False),
        ])

        for talon in talons:
            if not talon.name or not talon.name.isdigit():
                continue

            start = int(talon.name)
            end = start + talon.num_chq - 1

            if start <= serie_num <= end:
                return talon
        return False

    @api.onchange('serie', 'ste_id')
    def _onchange_find_talon(self):
        """Détecte automatiquement le talon en fonction de la société + numéro de série."""
        for rec in self:
            rec.talon_id = rec._find_talon_logic()

    @api.model
    def cron_find_all_talons(self):
        """Met à jour les talons pour tous les effets."""
        records = self.search([])
        for rec in records:
            found = rec._find_talon_logic()
            if found and rec.talon_id != found:
                rec.talon_id = found

    # -------------------------------------------------------------------
    # SEQUENCE INTEGRITY CHECK
    # -------------------------------------------------------------------
    def _check_sequence_integrity(self, vals):
        """
        Ensures that effets are created in strict sequence (N+1).
        Blocks creation if there is a gap or backward numbering.
        """
        serie_str = vals.get('serie')
        ste_id = vals.get('ste_id')

        if not serie_str or not ste_id or not str(serie_str).isdigit():
            return 

        serie_num = int(serie_str)

        talons = self.env['finance.talon'].search([
            ('ste_id', '=', ste_id),
            ('num_chq', '>', 0),
            ('name', '!=', False),
        ])
        
        target_talon = False
        for talon in talons:
            if not talon.name.isdigit(): continue
            start = int(talon.name)
            end = start + talon.num_chq - 1
            if start <= serie_num <= end:
                target_talon = talon
                break
        
        if not target_talon:
             return 

        last_effet = self.search([
            ('talon_id', '=', target_talon.id),
            ('serie', '!=', False)
        ], order='serie desc', limit=1)

        if not last_effet:
            return 

        last_num = int(last_effet.serie)
        expected_num = last_num + 1

        if serie_num <= last_num:
            return
        
        if serie_num != expected_num:
             raise ValidationError(
                 f"Dernier effet saisi : {last_num}\n"
                 f"Attention🚫 Effet attendu : {expected_num}\n"
                 f"Effet saisi actuelle : {serie_num}\n\n"
                 f"Veuillez sasir d'abord l'effet : {expected_num}\n\n"
                 "Veuillez saisir les effets dans l'ordre strict, sans saut numéro."
             )

    @api.model
    def create(self, vals):
        self._check_sequence_integrity(vals)
        return super().create(vals)


    # Constraints
    @api.constrains('montant')
    def _check_amount(self):
        for rec in self:
            if rec.montant <= 0:
                raise ValidationError("Le montant doit être supérieur à 0.")

    @api.constrains('date_emission', 'date_echeance')
    def _check_dates(self):
        for rec in self:
            if rec.date_emission and rec.date_echeance and rec.date_echeance < rec.date_emission:
                raise ValidationError("La date d’échéance ne peut pas être antérieure à la date d’émission.")

    _sql_constraints = [
        ('unique_serie_ste', 'unique(serie, ste_id)', 'La référence (Série) doit être unique par société.')
    ]
