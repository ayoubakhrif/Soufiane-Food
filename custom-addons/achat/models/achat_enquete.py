from odoo import models, fields, api
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
        default=lambda self: self.env.company.currency_id
    )

    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        index=True
    )

    # Optional but recommended
    remarks = fields.Char(
        string='Remarks',
        help='Conditions, MOQ, delivery delay, or any additional information'
    )

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
        ('article_supplier_date_uniq', 'unique(article_id, supplier_id, date)', 
         'Ce produit existe déjà pour ce fournisseur à la même date !')
    ]

    @api.model
    def create(self, vals):
        record = super(AchatArticlePrice, self).create(vals)
        
        # Look for the previous price for this article
        previous_price_rec = self.search([
            ('article_id', '=', record.article_id.id),
            ('id', '!=', record.id)
        ], order='date desc, id desc', limit=1)

        old_price = previous_price_rec.price if previous_price_rec else 0.0
        new_price = record.price

        # If price changed, send notification
        _logger.info(f"Price Bot: Checking {record.article_id.name} - Old: {old_price}, New: {new_price}")
        if old_price != new_price:
            try:
                # Determine trend
                if old_price == 0:
                    trend_msg = "🆕 *NOUVEAU PRIX*"
                    icon = "⭐"
                elif new_price > old_price:
                    trend_msg = "🔺 *AUGMENTATION*"
                    icon = "📈"
                else:
                    trend_msg = "🔻 *DIMINUTION*"
                    icon = "📉"

                msg = f"📢 *CHANGEMENT DE PRIX (ENQUÊTE)* 📢\n"
                msg += f"------------------------------------\n"
                msg += f"📦 *Article:* {record.article_id.name}\n"
                msg += f"🏢 *Fournisseur:* {record.supplier_id.name}\n\n"
                msg += f"{icon} {trend_msg}\n"
                msg += f"📉 Ancien: {old_price:.2f} {record.currency_id.symbol or 'Dh'}\n"
                msg += f"📈 Nouveau: {new_price:.2f} {record.currency_id.symbol or 'Dh'}\n"
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

        return record