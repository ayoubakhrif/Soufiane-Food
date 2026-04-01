from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PortnetEntry(models.Model):
    _name = 'portnet.entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Entrée Portnet'
    _order = 'id desc'

    name = fields.Char(
        string='Référence',
        required=True,
        copy=False,
        default='/',
        tracking=True,
    )

    article_id = fields.Many2one(
        'achat.article',
        string='Article',
        required=True,
        tracking=True,
    )

    origin_id = fields.Many2one(
        'achat.origin',
        string='Origine',
        required=True,
        tracking=True,
    )

    supplier_id = fields.Many2one(
        'logistique.supplier',
        string='Fournisseur',
        required=True,
        tracking=True,
    )

    incoterm = fields.Selection(
        selection=[
            ('cfr', 'CFR'),
            ('fob', 'FOB'),
            ('exw', 'EXW'),
        ],
        string='Incoterm',
        required=True,
        tracking=True,
    )

    invoice = fields.Char(
        string='Facture',
        required=True,
        tracking=True,
    )

    ste_id = fields.Many2one(
        'logistique.ste',
        string='Société',
        required=True,
        tracking=True,
    )

    note = fields.Text(
        string='Notes',
        tracking=True,
    )

    provenance = fields.Many2one(
        'achat.origin',
        string='Provenance',
        required=True,
        tracking=True,
    )

    device = fields.Selection(
        selection=[
            ('usd', 'USD'),
            ('eur', 'EUR'),
        ],
        string='Devise',
        required=True,
        tracking=True,
    )

    gross = fields.Float(string='Poids brut (kg)', required=True, tracking=True)
    net = fields.Float(string='Poids net (kg)', required=True, tracking=True)
    valeur = fields.Float(string='Valeur', required=True, tracking=True)
    nomenclature = fields.Char(string='Nomenclature', tracking=True)
    avance = fields.Float(string='Avance', tracking=True)

    total_fob = fields.Float(string='Total FOB', required=True, tracking=True)
    total_freight = fields.Float(string='Total Freight', tracking=True)  # required only when incoterm=cfr (enforced in view)

    total_cfr = fields.Float(
        string='Total CFR',
        compute='_compute_total_cfr',
        store=True,
        tracking=True,
    )

    payment_terms = fields.Boolean(string='Payment terms', tracking=True)
    date_invoice = fields.Date(string='Date facture', required=True, tracking=True)

    state = fields.Selection(
        selection=[
            ('new', 'Nouveau'),
            ('domicilied', 'Domicilié'),
            ('regle', 'Réglé'),
            ('annule', 'Annulé'),
        ],
        string='État',
        default='new',
        tracking=True,
    )

    # ── Computed ─────────────────────────────────────────────────────────────

    @api.depends('total_fob', 'total_freight')
    def _compute_total_cfr(self):
        for rec in self:
            rec.total_cfr = rec.total_fob + rec.total_freight

    @api.onchange('article_id')
    def _onchange_article_id(self):
        if self.article_id:
            company_article = self.article_id.company_article_id
            if company_article:
                self.nomenclature = company_article.nomenclature

    # ── Valeur validation (only called on Domicilier) ───────────────────────

    def _check_valeur(self):
        """Block the Domicilier transition when valeur differs from the
        article's reference value stored in company.article.value,
        based on user groups:
        - Admin: Always allowed
        - Manager: Allowed if valeur <= ref_value
        - User: Allowed only if valeur == ref_value
        """
        for rec in self:
            if not rec.article_id:
                continue
            company_article = rec.article_id.company_article_id
            if not company_article:
                continue
            ref_value = company_article.value
            # Only enforce when a reference value has been set (> 0)
            if not ref_value:
                continue

            # 1. Admins: Always allowed
            if self.env.user.has_group('portnet.group_portnet_admin'):
                continue

            # 2. Managers: Allowed if <= ref_value
            if self.env.user.has_group('portnet.group_portnet_manager'):
                if rec.valeur > ref_value:
                    raise ValidationError(
                        "En tant que Responsable Portnet, vous ne pouvez pas domicilier "
                        "une valeur (%.2f) strictement supérieure à la valeur "
                        "de référence de l'article \"%s\" (%.2f).\n"
                        "Veuillez corriger la valeur ou demander à un administrateur."
                        % (rec.valeur, company_article.display_name, ref_value)
                    )
                continue

            # 3. Normal Users: Allowed ONLY if == ref_value
            if rec.valeur != ref_value:
                raise ValidationError(
                    "La valeur saisie (%.2f) doit être égale à la valeur "
                    "de référence de l'article \"%s\" (%.2f).\n"
                    "Veuillez corriger la valeur pour domicilier."
                    % (rec.valeur, company_article.display_name, ref_value)
                )

    # ── State transitions ─────────────────────────────────────────────────────

    def action_domicilier(self):
        self._check_valeur()
        self.write({'state': 'domicilied'})

    def action_regler(self):
        self.write({'state': 'regle'})

    def action_annuler(self):
        self.write({'state': 'annule'})

    def action_reset_new(self):
        self.write({'state': 'new'})