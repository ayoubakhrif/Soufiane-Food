from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PortnetEntry(models.Model):
    _name = 'portnet.entry'
    _description = 'Entrée Portnet'
    _order = 'id desc'

    name = fields.Char(
        string='Référence',
        required=True,
        copy=False,
        default='/',
    )

    article_id = fields.Many2one(
        'achat.article',
        string='Article',
        required=True,
    )

    origin_id = fields.Many2one(
        'achat.origin',
        string='Origine',
        required=True,
    )

    supplier_id = fields.Many2one(
        'logistique.supplier',
        string='Fournisseur',
        required=True,
    )

    incoterm = fields.Selection(
        selection=[
            ('cfr', 'CFR'),
            ('fob', 'FOB'),
            ('exw', 'EXW'),
        ],
        string='Incoterm',
        required=True,
    )

    invoice = fields.Char(
        string='Facture',
        required=True,
    )

    ste_id = fields.Many2one(
        'logistique.ste',
        string='Société',
        required=True,
    )

    note = fields.Text(
        string='Notes',
    )

    provenance = fields.Many2one(
        'achat.origin',
        string='Provenance',
        required=True,
    )

    device = fields.Selection(
        selection=[
            ('usd', 'USD'),
            ('eur', 'EUR'),
        ],
        string='Devise',
        required=True,
    )

    gross = fields.Float(string='Poids brut (kg)', required=True)
    net = fields.Float(string='Poids net (kg)', required=True)
    valeur = fields.Float(string='Valeur', required=True)
    nomenclature = fields.Char(string='Nomenclature')
    avance = fields.Float(string='Avance')

    total_fob = fields.Float(string='Total FOB', required=True)
    total_freight = fields.Float(string='Total Freight')  # required only when incoterm=cfr (enforced in view)

    total_cfr = fields.Float(
        string='Total CFR',
        compute='_compute_total_cfr',
        store=True,
    )

    payment_terms = fields.Boolean(string='Payment terms')
    date_invoice = fields.Date(string='Date facture', required=True)

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
        article's reference value stored in company.article.value."""
        for rec in self:
            if not rec.article_id:
                continue
            company_article = rec.article_id.company_article_id
            if not company_article:
                continue
            ref_value = company_article.value
            # Only enforce when a reference value has been set (> 0)
            if ref_value and rec.valeur != ref_value:
                raise ValidationError(
                    "La valeur saisie (%.2f) est strictement supérieure à la valeur "
                    "de référence de l'article \"%s\" (%.2f).\n"
                    "Veuillez corriger la valeur avant de domicilier."
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