from odoo import models, fields, api
from odoo.exceptions import ValidationError
import requests
import logging

_logger = logging.getLogger(__name__)


class AchatArticlePrice(models.Model):
    _name = 'achat.article.price'
    _description = 'Purchase Article Price History'
    _order = 'date desc'

    # Core fields
    article_id = fields.Many2one(
        'logistique.article',
        string='Article',
        required=True,
        index=True
    )

    supplier_id = fields.Many2one(
        'logistique.supplier',
        string='Supplier',
        required=True,
        index=True
    )

    origin_id = fields.Many2one(
        'achat.origin',
        string='Origin',
        index=True
    )

    price = fields.Float(
        string='Price',
        required=True,
        digits=(16, 4)
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
    )

    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        index=True
    )

    remarks = fields.Char(
        string='Remarks',
        help='Conditions, MOQ, delivery delay, or any additional information'
    )

    incoterm = fields.Selection([
        ('cfr', 'CFR'),
        ('fob', 'FOB'),
        ('emirate', 'Emirate')
    ], string='Incoterm')

    crop = fields.Selection([
        ('new_crop', 'New crop'),
        ('old_crop', 'Old crop')
    ], string='Crop')

    user_id = fields.Many2one(
        'res.users',
        string='Entered By',
        default=lambda self: self.env.user,
        readonly=True
    )

    details = fields.Char(
        string='Details',
        help='Additional information or remarks'
    )

    _sql_constraints = [
        ('article_supplier_date_crop_origin_uniq', 'unique(article_id, supplier_id, date, crop, origin_id)', 
         'Ce produit existe déjà pour ce fournisseur à la même date avec ce crop et cette origine !'),
        ('price_gt_zero', 'CHECK(price > 0)', 'Le prix doit être strictement supérieur à 0 !')
    ]

    def init(self):
        # Drop the old unique constraints to allow the new unique constraint with crop and origin to take effect
        self.env.cr.execute("""
            ALTER TABLE achat_article_price 
            DROP CONSTRAINT IF EXISTS achat_article_price_article_supplier_date_uniq,
            DROP CONSTRAINT IF EXISTS achat_article_price_article_supplier_date_crop_uniq
        """)
        super(AchatArticlePrice, self).init()

    @api.constrains('article_id')
    def _check_article_translation(self):
        for record in self:
            if record.article_id and (not record.article_id.traduction or not record.article_id.traduction.strip()):
                raise ValidationError(
                    f"Enregistrement impossible : L'article '{record.article_id.name}' n'a pas de traduction renseignée.\n"
                    "Veuillez d'abord remplir le champ 'Traduction' sur la fiche article."
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super(AchatArticlePrice, self).create(vals_list)
        
        for record, vals in zip(records, vals_list):
            # Look for the previous price for this article
            previous_price_rec = self.search([
                ('article_id', '=', record.article_id.id),
                ('incoterm', '=', record.incoterm),
                ('crop', '=', record.crop),
                ('origin_id', '=', record.origin_id.id),
                ('id', 'not in', records.ids) # Exclude all records being created in this batch
            ], order='date desc, id desc', limit=1)

            old_price = previous_price_rec.price if previous_price_rec else 0.0
            # Use value from vals if available to avoid cache issues, fallback to record.price
            new_price = vals.get('price', record.price)

            # If price changed, send notification
            _logger.info("Price Bot: Article %s - Old: %s, New: %s", record.article_id.name, old_price, new_price)
            if old_price != 0 and old_price != new_price:
                try:
                    # Determine trend
                    if new_price > old_price:
                        trend_msg = "🔺 *AUGMENTATION*"
                        icon = "📈"
                    else:
                        trend_msg = "🔻 *DIMINUTION*"
                        icon = "📉"

                    # Affichage de la traduction (champ traduction de logistique.article)
                    article_sudo = record.article_id.sudo()
                    article_display = article_sudo.traduction

                    # Dates pour l'affichage
                    old_date_str = previous_price_rec.date.strftime('%d/%m') if previous_price_rec and previous_price_rec.date else "??"
                    new_date_str = record.date.strftime('%d/%m') if record.date else "??"
                    
                    # Libellé Incoterm
                    incoterm_val = dict(self._fields['incoterm'].selection).get(record.incoterm, record.incoterm or 'N/A')

                    msg = f"📢 *CHANGEMENT DE PRIX ({incoterm_val.upper()})* 📢\n"
                    msg += f"------------------------------------\n"
                    msg += f"📦 *Article:* {article_display}\n"
                    if record.crop:
                        crop_display = "Nouvelle récolte (New crop)" if record.crop == 'new_crop' else "Ancienne récolte (Old crop)"
                        msg += f"🌱 *Crop:* {crop_display}\n"
                    msg += f"🏢 *Fournisseur:* {record.supplier_id.name}\n"
                    msg += f"🌍 *Origine:* {record.origin_id.name or 'Inconnu'}\n\n"
                    msg += f"{icon} {trend_msg}\n"
                    msg += f"📉 Ancien: {old_price:.2f} {record.currency_id.symbol or 'Dh'} ({old_date_str})\n"
                    msg += f"📈 Nouveau: {new_price:.2f} {record.currency_id.symbol or 'Dh'} ({new_date_str})\n"
                    msg += f"👤 Saisi par: {self.env.user.name}"


                    payload = {
                        "group_id": "120363428923348892@g.us",
                        "text": msg
                    }
                    
                    # Send to bridge API (same server, host from docker)
                    requests.post("http://172.17.0.1:3000/api/send", json=payload, timeout=5)
                    _logger.info(f"Price Bot notification sent for article {record.article_id.name}")
                except Exception as e:
                    _logger.error(f"Failed to send Price Bot notification: {str(e)}")

        return records
