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
    )

    supplier_id = fields.Many2one(
        'logistique.supplier',
        string='Fournisseur',
    )

    incoterm = fields.Selection(
        selection=[
            ('cfr', 'CFR'),
            ('fob', 'FOB'),
            ('exw', 'EXW'),
        ],
        string='Incoterm',
    )

    invoice = fields.Char(
        string='Facture',
    )

    ste_id = fields.Many2one(
        'logistique.ste',
        string='Société',
    )

    note = fields.Text(
        string='Notes',
    )

    provenance = fields.Many2one(
        'achat.origin',
        string='Provenance',
    )

    device = fields.Selection(
        selection=[
            ('usd', 'USD'),
            ('eur', 'EUR'),
        ],
        string='Devise',
    )

    gross = fields.Float(string='Poids brut (kg)')
    net = fields.Float(string='Poids net (kg)')
    valeur = fields.Float(string='Valeur')
    nomenclature = fields.Char(string='Nomenclature')

    total_fob = fields.Float(string='Total FOB')
    total_freight = fields.Float(string='Total Freight')

    total_cfr = fields.Float(
        string='Total CFR',
        compute='_compute_total_cfr',
        store=True,
    )

    payment_terms = fields.Boolean(string='Payment terms')
    date_invoice = fields.Date(string='Date facture')

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

    # ── Valeur validation helper ──────────────────────────────────────────────

    def _check_valeur(self):
        """Raise if the entered valeur differs from the article's reference value."""
        for rec in self:
            if not rec.article_id:
                continue
            company_article = rec.article_id.company_article_id
            if not company_article:
                continue
            ref_value = company_article.value
            if ref_value and rec.valeur != ref_value:
                raise ValidationError(
                    "La valeur saisie (%.2f) est différente de la valeur "
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