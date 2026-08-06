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

    # @api.constrains('article_id')
    # def _check_article_translation(self):
    #     for record in self:
    #         if record.article_id and (not record.article_id.traduction or not record.article_id.traduction.strip()):
    #             raise ValidationError(
    #                 f"Enregistrement impossible : L'article '{record.article_id.name}' n'a pas de traduction renseignée.\n"
    #                 "Veuillez d'abord remplir le champ 'Traduction' sur la fiche article."
    #             )

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
        return records

    @api.model
    def _cron_send_daily_price_report(self):
        import logging
        import base64
        import requests
        from datetime import datetime, time
        import pytz
        from dateutil.relativedelta import relativedelta
        import io
        
        import matplotlib
        try:
            matplotlib.use('Agg')
        except Exception:
            pass
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        _logger = logging.getLogger(__name__)

        user_tz = pytz.timezone(self.env.user.tz or 'Africa/Casablanca')
        today_local = datetime.now(user_tz).date()
        
        start_of_day_local = user_tz.localize(datetime.combine(today_local, time.min))
        end_of_day_local = user_tz.localize(datetime.combine(today_local, time.max))
        
        start_of_day_utc = start_of_day_local.astimezone(pytz.utc).replace(tzinfo=None)
        end_of_day_utc = end_of_day_local.astimezone(pytz.utc).replace(tzinfo=None)

        followed_articles = self.env['logistique.article'].search([('to_follow', '=', True)])

        if not followed_articles:
            _logger.info("Daily Price Report: No followed articles found.")
            return

        final_changes = []

        for article in followed_articles:
            latest_price_rec = self.search([
                ('article_id', '=', article.id)
            ], order='date desc, id desc', limit=1)

            if not latest_price_rec:
                continue

            previous_price_rec = self.search([
                ('article_id', '=', article.id),
                ('incoterm', '=', latest_price_rec.incoterm),
                ('crop', '=', latest_price_rec.crop),
                ('origin_id', '=', latest_price_rec.origin_id.id),
                ('supplier_id', '=', latest_price_rec.supplier_id.id),
                ('id', '!=', latest_price_rec.id),
                ('date', '<=', latest_price_rec.date)
            ], order='date desc, id desc', limit=1)

            old_price = previous_price_rec.price if previous_price_rec else latest_price_rec.price
            new_price = latest_price_rec.price

            if new_price > old_price:
                trend = 'up'
            elif new_price < old_price:
                trend = 'down'
            else:
                trend = 'flat'

            final_changes.append({
                'record': latest_price_rec,
                'old_price': old_price,
                'new_price': new_price,
                'trend': trend,
                'old_date': previous_price_rec.date.strftime('%d/%m/%Y') if previous_price_rec and previous_price_rec.date else "N/A",
            })

        if not final_changes:
            _logger.info("Daily Price Report: No ACTUAL price changes for followed articles today.")
            return

        # Calculate date limit (6 months ago)
        six_months_ago = (today_local - relativedelta(months=6))

        # Prepare dummy dicts for the report since QWeb records can be heavy
        changes_data = []
        for c in final_changes:
            rec = c['record']
            crop_display = "New crop" if rec.crop == 'new_crop' else "Old crop" if rec.crop == 'old_crop' else "N/A"
            
            # Fetch historical data for graph
            history = self.search([
                ('article_id', '=', rec.article_id.id),
                ('incoterm', '=', rec.incoterm),
                ('crop', '=', rec.crop),
                ('origin_id', '=', rec.origin_id.id),
                ('supplier_id', '=', rec.supplier_id.id),
                ('date', '>=', six_months_ago)
            ], order='date asc')

            dates = []
            prices = []
            for h in history:
                if h.date:
                    dates.append(h.date)
                    prices.append(h.price)

            graph_b64 = ""
            if len(dates) > 0:
                try:
                    plt.figure(figsize=(8, 4))
                    plt.plot(dates, prices, marker='o', linestyle='-', color='#1f77b4', linewidth=2, markersize=6)
                    plt.title(f"Évolution du prix (6 derniers mois)", fontsize=12, pad=10)
                    plt.xlabel("Date", fontsize=10)
                    plt.ylabel(f"Prix ({rec.currency_id.symbol or 'Dh'})", fontsize=10)
                    plt.grid(True, linestyle='--', alpha=0.7)
                    
                    # Format X axis dates
                    ax = plt.gca()
                    ax.set_xticks(dates)
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'))
                    plt.xticks(rotation=45)
                    plt.tight_layout()

                    buf = io.BytesIO()
                    plt.savefig(buf, format='png', dpi=100)
                    buf.seek(0)
                    graph_b64 = base64.b64encode(buf.read()).decode('utf-8')
                    buf.close()
                    plt.close()
                except Exception as e:
                    _logger.error(f"Erreur génération graphe pour {rec.id}: {e}")

            changes_data.append({
                'article': rec.article_id.traduction or rec.article_id.name,
                'fournisseur': rec.supplier_id.name,
                'origine': rec.origin_id.name or 'N/A',
                'crop': crop_display,
                'incoterm': dict(self._fields['incoterm'].selection).get(rec.incoterm, rec.incoterm or 'N/A'),
                'old_price': c['old_price'],
                'new_price': c['new_price'],
                'trend': c['trend'],
                'currency': rec.currency_id.symbol or 'Dh',
                'old_date': c['old_date'],
                'graph_b64': graph_b64
            })

        data = {
            'changes': changes_data,
            'report_date': today_local.strftime('%d/%m/%Y')
        }
        
        pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
            'achat.action_report_daily_price_changes', 
            res_ids=[], 
            data=data
        )

        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

        try:
            payload = {
                "group_id": "120363428923348892@g.us",
                "text": f"📢 *Rapport Journalier des Prix* ({today_local.strftime('%d/%m/%Y')})\n\nVoici le récapitulatif des changements de prix pour les articles suivis.",
                "document": pdf_base64,
                "fileName": f"Rapport_Prix_{today_local.strftime('%Y%m%d')}.pdf"
            }
            response = requests.post("http://172.17.0.1:3000/api/send", json=payload, timeout=15)
            response.raise_for_status()
            _logger.info("Daily Price Report PDF sent successfully.")
        except Exception as e:
            _logger.error(f"Failed to send Daily Price Report PDF: {str(e)}")
