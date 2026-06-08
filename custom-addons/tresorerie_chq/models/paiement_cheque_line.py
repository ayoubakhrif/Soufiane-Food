from odoo import models, fields, api
from odoo.exceptions import ValidationError


class TresorerieChqCheque(models.Model):
    """
    Represents a physical cheque received within a paiement and its lifecycle workflow.
    """
    _name = 'tresorerie_chq.cheque'
    _description = 'Suivi de Chèque'
    _order = 'sequence, check_date, id'

    sequence = fields.Integer(string='Séquence', default=10)
    
    paiement_id = fields.Many2one(
        'tresorerie_chq.paiement',
        string='Paiement',
        required=True,
        ondelete='cascade',
    )

    client_id = fields.Many2one(
        'tresorerie_chq.client',
        string='Client',
        related='paiement_id.client_id',
        store=True,
        readonly=True,
    )

    owner_id = fields.Many2one(
        'tresorerie_chq.effets.owner',
        string='Porteur',
        ondelete='restrict',
        help="Laisser vide si le chèque est au nom du client. "
             "Sélectionner le porteur si le chèque est un effet de commerce.",
    )

    # Specific field for "Soufiane" client
    soufiane_owner_id = fields.Many2one(
        'tresorerie_chq.effets.owner',
        string='Client soufiane',
        ondelete='restrict',
    )

    check_date = fields.Date(
        string="Date d'échéance",
        required=False,
    )

    allow_no_date = fields.Boolean(
        related='client_id.allow_no_date',
        string="Autoriser sans échéance",
        readonly=True,
    )
    amount = fields.Float(
        string='Montant',
        required=True,
        digits=(10, 2),
    )
    
    # Restrict input to 7 characters at the database and UI levels
    note = fields.Char(
        string='N° chèque',
        size=7,
    )

    scan_chq = fields.Binary(
        string="Scan Chèque",
        attachment=True,
        help="Fichier de scan ou photo du chèque"
    )
    scan_chq_name = fields.Char(string="Nom du fichier chèque")

    ai_raw_prediction = fields.Text(string="Prédiction IA brute", readonly=True)
    is_ai_extracted = fields.Boolean(string="Extrait par IA", readonly=True)

    core_ste_id = fields.Many2one('core.ste', string='Société')
    reception_date = fields.Date(string='Date de réception')
    bank_send_date = fields.Date(string="Date d'envoi au banque")
    unpaid_date = fields.Date(string="Date impayé")

    bank_id = fields.Many2one(
        'tresorerie_chq.bank',
        string='Banque',
    )

    owner_display = fields.Char(
        string='Porteur',
        compute='_compute_owner_display',
        store=False,
    )

    owner_cin = fields.Char(
        string="CIN Porteur",
        compute="_compute_owner_cin",
        inverse="_inverse_owner_cin",
        store=True,
    )

    state = fields.Selection([
        ('stock', 'En stock'),
        ('remis', 'Remis au client'),
        ('banque', 'Envoyé à la banque'),
        ('encaisse', 'Encaissé'),
        ('impaye', 'Impayé'),
    ], default='stock', string='État', required=True, tracking=True)

    is_manager = fields.Boolean(
        compute='_compute_is_manager',
        string='Est Responsable',
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends_context('uid')
    def _compute_is_manager(self):
        is_manager = self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager')
        for rec in self:
            rec.is_manager = is_manager

    @api.depends('owner_id', 'paiement_id.client_id')
    def _compute_owner_display(self):
        for line in self:
            if line.owner_id:
                line.owner_display = line.owner_id.name
            elif line.paiement_id.client_id:
                line.owner_display = line.paiement_id.client_id.name
            else:
                line.owner_display = ''

    @api.depends('owner_id', 'owner_id.cin')
    def _compute_owner_cin(self):
        for rec in self:
            rec.owner_cin = rec.owner_id.cin if rec.owner_id else ''

    def _inverse_owner_cin(self):
        for rec in self:
            if rec.owner_cin and not rec.owner_id:
                raise ValidationError("❌ Veuillez sélectionner un porteur avant de renseigner le CIN.")
            if rec.owner_id:
                rec.owner_id.cin = rec.owner_cin

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('note')
    def _check_cheque_number(self):
        for rec in self:
            if rec.note:
                num = rec.note.strip()
                if not num.isdigit():
                    raise ValidationError("❌ Le numéro de chèque doit contenir uniquement des chiffres.")
                if len(num) > 7:
                    raise ValidationError("Le numéro de chèque doit comporter au maximum 7 chiffres.")

    @api.constrains('check_date', 'client_id', 'paiement_id')
    def _check_required_date(self):
        for rec in self:
            client = rec.client_id or rec.paiement_id.client_id
            if not rec.check_date and (not client or not client.allow_no_date):
                raise ValidationError("❌ La date d'échéance est requise pour ce client.")

    # ------------------------------------------------------------------
    # Workflow Actions
    # ------------------------------------------------------------------
    def action_stock(self):
        """Reset to stock (admin only)."""
        for rec in self:
            if not self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager'):
                raise ValidationError("❌ Seul un administrateur peut remettre en stock librement.")
            rec.state = 'stock'

    def action_remis(self):
        """Deliver to client."""
        for rec in self:
            if not self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager'):
                if rec.state not in ['stock', 'impaye']:
                    raise ValidationError("❌ Le chèque doit être en stock ou impayé pour être remis au client.")
            rec.state = 'remis'

    def action_banque(self):
        """Send to bank."""
        for rec in self:
            if not rec.bank_send_date:
                raise ValidationError("❌ La 'Date d'envoi au banque' est obligatoire pour envoyer le chèque à la banque.")
            if not self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager'):
                if rec.state not in ['stock', 'impaye']:
                    raise ValidationError("❌ Le chèque doit être en stock ou impayé pour être envoyé à la banque.")
            rec.state = 'banque'

    def action_encaisse(self):
        """Mark as cashed/cleared."""
        for rec in self:
            if not self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager'):
                if rec.state != 'banque':
                    raise ValidationError("❌ Le chèque doit être envoyé à la banque pour pouvoir être encaissé.")
            rec.state = 'encaisse'

    def action_impaye(self):
        """Mark as unpaid/bounced."""
        for rec in self:
            if not rec.unpaid_date:
                raise ValidationError("❌ La 'Date impayé' est obligatoire pour marquer ce chèque comme impayé.")
            if not rec.owner_cin:
                raise ValidationError("❌ Le champ CIN du porteur doit être renseigné pour marquer ce chèque comme impayé.")
            if not self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager'):
                if rec.state != 'banque':
                    raise ValidationError("❌ Le chèque doit être envoyé à la banque pour pouvoir être marqué impayé.")
            rec.state = 'impaye'


class TresorerieChqEffet(models.Model):
    """
    Represents a physical commercial paper (effet) received within a paiement and its lifecycle workflow.
    """
    _name = 'tresorerie_chq.effet'
    _description = 'Suivi d\'Effet'
    _order = 'sequence, check_date, id'

    sequence = fields.Integer(string='Séquence', default=10)

    paiement_id = fields.Many2one(
        'tresorerie_chq.paiement',
        string='Paiement',
        required=True,
        ondelete='cascade',
    )

    client_id = fields.Many2one(
        'tresorerie_chq.client',
        string='Client',
        related='paiement_id.client_id',
        store=True,
        readonly=True,
    )

    owner_id = fields.Many2one(
        'tresorerie_chq.effets.owner',
        string='Porteur',
        ondelete='restrict',
        help="Laisser vide si l'effet est au nom du client. "
             "Sélectionner le porteur si l'effet est un effet de commerce.",
    )

    # Specific field for "Soufiane" client
    soufiane_owner_id = fields.Many2one(
        'tresorerie_chq.effets.owner',
        string='Client soufiane',
        ondelete='restrict',
    )

    check_date = fields.Date(
        string="Date d'échéance",
        required=False,
    )

    allow_no_date = fields.Boolean(
        related='client_id.allow_no_date',
        string="Autoriser sans échéance",
        readonly=True,
    )
    amount = fields.Float(
        string='Montant',
        required=True,
        digits=(10, 2),
    )
    note = fields.Char(string='N° effet')

    scan_effet = fields.Binary(
        string="Scan Effet",
        attachment=True,
        help="Fichier de scan ou photo de l'effet"
    )
    scan_effet_name = fields.Char(string="Nom du fichier effet")

    ai_raw_prediction = fields.Text(string="Prédiction IA brute", readonly=True)
    is_ai_extracted = fields.Boolean(string="Extrait par IA", readonly=True)

    core_ste_id = fields.Many2one('core.ste', string='Société')
    reception_date = fields.Date(string='Date de réception')
    bank_send_date = fields.Date(string="Date d'envoi au banque")
    unpaid_date = fields.Date(string="Date impayé")

    bank_id = fields.Many2one(
        'tresorerie_chq.bank',
        string='Banque',
    )

    owner_display = fields.Char(
        string='Porteur',
        compute='_compute_owner_display',
        store=False,
    )

    owner_cin = fields.Char(
        string="CIN Porteur",
        compute="_compute_owner_cin",
        inverse="_inverse_owner_cin",
        store=True,
    )

    state = fields.Selection([
        ('stock', 'En stock'),
        ('remis', 'Remis au client'),
        ('banque', 'Envoyé à la banque'),
        ('encaisse', 'Encaissé'),
        ('impaye', 'Impayé'),
    ], default='stock', string='État', required=True, tracking=True)

    is_manager = fields.Boolean(
        compute='_compute_is_manager',
        string='Est Responsable',
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends_context('uid')
    def _compute_is_manager(self):
        is_manager = self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager')
        for rec in self:
            rec.is_manager = is_manager

    @api.depends('owner_id', 'paiement_id.client_id')
    def _compute_owner_display(self):
        for line in self:
            if line.owner_id:
                line.owner_display = line.owner_id.name
            elif line.paiement_id.client_id:
                line.owner_display = line.paiement_id.client_id.name
            else:
                line.owner_display = ''

    @api.depends('owner_id', 'owner_id.cin')
    def _compute_owner_cin(self):
        for rec in self:
            rec.owner_cin = rec.owner_id.cin if rec.owner_id else ''

    def _inverse_owner_cin(self):
        for rec in self:
            if rec.owner_cin and not rec.owner_id:
                raise ValidationError("❌ Veuillez sélectionner un porteur avant de renseigner le CIN.")
            if rec.owner_id:
                rec.owner_id.cin = rec.owner_cin

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('check_date', 'client_id', 'paiement_id')
    def _check_required_date(self):
        for rec in self:
            client = rec.client_id or rec.paiement_id.client_id
            if not rec.check_date and (not client or not client.allow_no_date):
                raise ValidationError("❌ La date d'échéance est requise pour ce client.")

    # ------------------------------------------------------------------
    # Workflow Actions
    # ------------------------------------------------------------------
    def action_stock(self):
        """Reset to stock (admin only)."""
        for rec in self:
            if not self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager'):
                raise ValidationError("❌ Seul un administrateur peut remettre en stock librement.")
            rec.state = 'stock'

    def action_remis(self):
        """Deliver to client."""
        for rec in self:
            if not self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager'):
                if rec.state not in ['stock', 'impaye']:
                    raise ValidationError("❌ L'effet doit être en stock ou impayé pour être remis au client.")
            rec.state = 'remis'

    def action_banque(self):
        """Send to bank."""
        for rec in self:
            if not rec.bank_send_date:
                raise ValidationError("❌ La 'Date d'envoi au banque' est obligatoire pour envoyer l'effet à la banque.")
            if not self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager'):
                if rec.state not in ['stock', 'impaye']:
                    raise ValidationError("❌ L'effet doit être en stock ou impayé pour être envoyé à la banque.")
            rec.state = 'banque'

    def action_encaisse(self):
        """Mark as cashed/cleared."""
        for rec in self:
            if not self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager'):
                if rec.state != 'banque':
                    raise ValidationError("❌ L'effet doit être envoyé à la banque pour pouvoir être encaissé.")
            rec.state = 'encaisse'

    def action_impaye(self):
        """Mark as unpaid/bounced."""
        for rec in self:
            if not rec.unpaid_date:
                raise ValidationError("❌ La 'Date impayé' est obligatoire pour marquer cet effet comme impayé.")
            if not rec.owner_cin:
                raise ValidationError("❌ Le champ CIN du porteur doit être renseigné pour marquer cet effet comme impayé.")
            if not self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager'):
                if rec.state != 'banque':
                    raise ValidationError("❌ L'effet doit être envoyé à la banque pour pouvoir être marqué impayé.")
            rec.state = 'impaye'
