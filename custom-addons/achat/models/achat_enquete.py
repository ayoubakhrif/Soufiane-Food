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
        default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
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
         'Ce produit existe déjà pour ce fournisseur à la même date !'),
        ('price_gt_zero', 'CHECK(price > 0)', 'Le prix doit être strictement supérieur à 0 !')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super(AchatArticlePrice, self).create(vals_list)
        
        for record, vals in zip(records, vals_list):
            # Look for the previous price for this article
            previous_price_rec = self.search([
                ('article_id', '=', record.article_id.id),
                ('id', 'not in', records.ids) # Exclude all records being created in this batch
            ], order='date desc, id desc', limit=1)

            old_price = previous_price_rec.price if previous_price_rec else 0.0
            # Use value from vals if available to avoid cache issues, fallback to record.price
            new_price = vals.get('price', record.price)

            # If price changed, send notification
            _logger.info("Price Bot: Article %s - Old: %s, New: %s", record.article_id.name, old_price, new_price)
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

                    # Display Translation and Name if both exist
                    name = record.article_id.name or ""
                    trad = record.article_id.traduction or ""
                    article_display = f"{trad} ({name})" if trad and trad != name else (trad or name)

                    msg = f"📢 *CHANGEMENT DE PRIX (ENQUÊTE)* 📢\n"
                    msg += f"------------------------------------\n"
                    msg += f"📦 *Article:* {article_display}\n"
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

        return records
