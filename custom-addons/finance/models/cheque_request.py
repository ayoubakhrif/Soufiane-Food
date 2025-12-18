from odoo import models, fields, api

class FinanceChequeRequest(models.Model):
    _name = 'finance.cheque.request'
    _description = 'Demande de Chéquier'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'ste_id'
    _order = 'request_date desc, id desc'

    ste_id = fields.Many2one('finance.ste', string='Société', required=True, readonly=True)
    request_date = fields.Datetime(string='Date de demande', default=fields.Datetime.now, readonly=True)
    
    state = fields.Selection([
        ('pending', 'En attente'),
        ('done', 'Traité'),
    ], string='État', default='pending', tracking=True, readonly=True)

    preview_html = fields.Html(string='Aperçu', sanitize=False, readonly=True)

    @api.model
    def create_request(self, ste_id):
        """Creates a new request if one doesn't already exist in pending state."""
        existing = self.search([
            ('ste_id', '=', ste_id.id),
            ('state', '=', 'pending')
        ])
        if existing:
            return existing

        # Generate HTML Preview
        html_content = self._generate_html_content(ste_id)

        request = self.create({
            'ste_id': ste_id.id,
            'preview_html': html_content,
        })
        
        # Notify Managers
        group_finance_user = self.env.ref('finance.group_finance_user')
        if group_finance_user:
            managers = group_finance_user.users
            for manager in managers:
                request.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=manager.id,
                    summary=f'Stock chéquier bas pour {ste_id.name}',
                    note=f'Le stock de chèques pour {ste_id.name} est presque épuisé (<= 20). Veuillez commander un nouveau carnet.'
                )
        return request

    def _generate_html_content(self, ste_id):
        logo_url = f"/web/image/finance.ste/{ste_id.id}/logo"
        
        return f"""
        <div style="
            font-family: 'Times New Roman', Times, serif; 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 40px; 
            background: white; 
            border: 1px solid #ddd; 
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
            color: #333;
        ">
            <!-- Header -->
            <div style="text-align: center; margin-bottom: 40px; border-bottom: 2px solid #333; padding-bottom: 20px;">
                <img src="{logo_url}" style="max-height: 100px; margin-bottom: 20px;"/><br/>
                <h1 style="margin: 0; font-size: 24px; text-transform: uppercase; letter-spacing: 2px;">Demande de Chéquier</h1>
                <p style="margin: 10px 0 0 0; color: #666; font-style: italic;">Document Interne - Département Finance</p>
            </div>

            <!-- Company Info -->
            <div style="margin-bottom: 40px;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="width: 150px; font-weight: bold; padding: 5px;">Société :</td>
                        <td style="padding: 5px; font-size: 18px;">{ste_id.raison_social or ste_id.name}</td>
                    </tr>
                    <tr>
                        <td style="width: 150px; font-weight: bold; padding: 5px;">Compte Bancaire :</td>
                        <td style="padding: 5px; font-family: monospace; font-size: 16px;">{ste_id.num_compte or 'N/A'}</td>
                    </tr>
                    <tr>
                        <td style="width: 150px; font-weight: bold; padding: 5px;">Date :</td>
                        <td style="padding: 5px;">{fields.Date.today().strftime('%d/%m/%Y')}</td>
                    </tr>
                </table>
            </div>

            <!-- Body -->
            <div style="margin-bottom: 50px; line-height: 1.6; font-size: 16px;">
                <p>Madame, Monsieur,</p>
                <p>
                    Par la présente, nous sollicitons le renouvellement de notre carnet de chèques pour le compte susmentionné.
                    Le stock actuel arrivant à épuisement, nous vous prions de bien vouloir procéder à la commande d'un nouveau chéquier
                    dans les meilleurs délais.
                </p>
                <p>
                    Veuillez mettre le chéquier à disposition de notre mandataire habituel dès sa disponibilité.
                </p>
            </div>

            <!-- Signature Area -->
            <div style="display: flex; justify-content: space-between; margin-top: 60px;">
                <div style="text-align: center; width: 40%;">
                    <p style="font-weight: bold; margin-bottom: 50px;">Le Demandeur</p>
                    <div style="border-top: 1px solid #ccc; width: 80%; margin: 0 auto;"></div>
                </div>
                <div style="text-align: center; width: 40%;">
                    <p style="font-weight: bold; margin-bottom: 50px;">Direction / Validation</p>
                    <div style="border-top: 1px solid #ccc; width: 80%; margin: 0 auto;"></div>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="margin-top: 60px; text-align: center; font-size: 10px; color: #999;">
                <p>Ceci est un document généré automatiquement par le système de gestion financière.</p>
            </div>
        </div>
        """

    def action_done(self):
        """Mark request as done and close activities."""
        self.ensure_one()
        self.state = 'done'
        self.activity_feedback(['mail.mail_activity_data_todo'])
        return {'type': 'ir.actions.act_window_close'}
