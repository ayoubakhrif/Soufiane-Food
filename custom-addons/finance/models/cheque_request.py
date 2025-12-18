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
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    ], string='État', default='pending', tracking=True, readonly=True)

    preview_html = fields.Html(string='Aperçu', sanitize=False, readonly=True)

    @api.model
    def create_request(self, ste_id):
        """Creates a new request ONLY if the last one was rejected or none exists."""
        
        # Check LAST request state
        last_request = self.search([
            ('ste_id', '=', ste_id.id)
        ], order='request_date desc, id desc', limit=1)

        if last_request:
            if last_request.state in ['pending', 'approved']:
                # Do NOT create a new request
                return last_request
            # If rejected, we proceed to create a new one

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
                    note=f'Le stock de chèques pour {ste_id.name} est presque épuisé. Veuillez valider la demande.'
                )
        return request

    # ... _generate_html_content ...

    def action_approve(self):
        """Approve request, clear activity, and print PDF."""
        self.ensure_one()
        self.state = 'approved'
        self.activity_feedback(['mail.mail_activity_data_todo'])
        
        # Trigger PDF Download
        return self.env.ref('finance.action_report_cheque_request').report_action(self)

    def action_reject(self):
        """Reject request and clear activity."""
        self.ensure_one()
        self.state = 'rejected'
        self.activity_feedback(['mail.mail_activity_data_todo'])

    def _generate_html_content(self, ste_id):
        logo_url = f"/web/image/finance.ste/{ste_id.id}/logo"
        today = fields.Date.today().strftime('%d/%m/%Y')

        return f"""
        <div style="
            font-family: 'Times New Roman', Times, serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px;
            background: white;
            color: #000;
            line-height: 1.6;
        ">
            <!-- Header -->
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <img src="{logo_url}" style="max-height: 80px;"/>
                </div>
                <div style="text-align: right;">
                    <p>Tanger, le {today}</p>
                </div>
            </div>

            <br/><br/>

            <!-- Recipient -->
            <div>
                <p>
                    <strong>À</strong><br/>
                    Mme la Directrice du Centre d’Affaires PDN<br/>
                    Banque Populaire Tanger – Tétouan
                </p>
            </div>

            <br/>

            <!-- Subject -->
            <div style="text-align: center; margin: 30px 0;">
                <p style="font-weight: bold; text-decoration: underline;">
                    Objet : Demande de talons de chèques
                </p>
            </div>

            <!-- Body -->
            <div>
                <p>Madame,</p>

                <p>
                    Nous vous prions de bien vouloir procéder à la mise à disposition de nouveaux
                    carnets de chèques relatifs au compte professionnel de notre société,
                    dont les coordonnées sont les suivantes :
                </p>

                <br/>

                <p>
                    <strong>Raison sociale :</strong> {ste_id.raison_social or ste_id.name}<br/>
                    <strong>Numéro de compte :</strong> {ste_id.num_compte or "—"}
                </p>

                <br/>

                <p>
                    Nous vous remercions de bien vouloir nous aviser dès la mise à disposition
                    des carnets de chèques.
                </p>

                <p>
                    Dans l’attente de votre confirmation, nous vous prions d’agréer,
                    Madame, l’assurance de nos salutations distinguées.
                </p>
            </div>

            <br/><br/><br/>

            <!-- Signature -->
            <div>
                <p><strong>Signature</strong></p>
                <br/><br/>
            </div>

            <!-- Footer -->
            <div style="
                margin-top: 60px;
                font-size: 11px;
                color: #000;
                border-top: 1px solid #000;
                padding-top: 10px;
            ">
                <p>
                    {ste_id.raison_social or ste_id.name}<br/>
                    {ste_id.adress or ""}<br/>
                </p>
            </div>
        </div>
        """



