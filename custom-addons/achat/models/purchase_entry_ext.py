from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date, timedelta
import base64
import io
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

class LogisticsEntry(models.Model):
    _inherit = 'logistique.entry'

    contract_id = fields.Many2one('achat.contract', string='Contract', domain="[('state', '=', 'open')]")
    free_time_negotiated = fields.Integer(string='Negotiated Free Time')

    is_non_change = fields.Boolean(string='Non Changé', default=False,
                                   help='Cocher si le dossier n\'a pas encore été changé')

    date_booking = fields.Date(string='Date of Booking')
    date_docs_received = fields.Date(string='Date Documents Received')
    date_docs_confirmed = fields.Date(string='Date Documents Confirmed')

    origin_id = fields.Many2one(
        'achat.origin',
        string='Origin'
    )

    
    # Document Link
    document_ids = fields.One2many('logistique.entry.document', 'entry_id', string='Documents')

    display_name = fields.Char(compute='_compute_display_name') # Just to ensure we have it if needed

    eta_this_week = fields.Boolean(
        string='ETA cette semaine',
        compute='_compute_eta_this_week',
        store=True,
        help='True if ETA <= next Thursday (inclusive) and port_status is on_port',
    )

    @api.depends('eta', 'port_status')
    def _compute_eta_this_week(self):
        today = date.today()
        days_to_thursday = (3 - today.weekday()) % 7
        next_thursday = today + timedelta(days=days_to_thursday)
        for rec in self:
            rec.eta_this_week = (
                rec.port_status == 'on_port'
                and bool(rec.eta)
                and rec.eta <= next_thursday
            )

    calendar_label = fields.Char(string='Label Calendrier', compute='_compute_calendar_label')

    @api.depends('supplier_id.name', 'achat_article_id.name', 'ste_id.name', 'amount_total')
    def _compute_calendar_label(self):
        for rec in self:
            supplier = rec.supplier_id.name or ''
            article = rec.achat_article_id.name or ''
            ste = rec.ste_id.name or ''
            total = rec.amount_total or 0.0
            # Format total with space as thousands separator
            total_str = "{:,.2f}".format(total).replace(",", " ")
            rec.calendar_label = f"{supplier} - {article} - {ste} - {total_str} USD"

    @api.depends('calendar_label', 'bl_number')
    def _compute_display_name(self):
        for rec in self:
            if self.env.context.get('show_bl_number'):
                rec.display_name = rec.bl_number or "Nouveau"
            elif rec.calendar_label:
                rec.display_name = rec.calendar_label
            else:
                rec.display_name = rec.bl_number or "Nouveau"

    @api.constrains('bl_number', 'contract_id')
    def _check_bl_contract_unique(self):
        """Prevent duplicate BL numbers for the same contract"""
        for rec in self:
            if rec.bl_number and rec.contract_id:
                duplicate = self.search([
                    ('id', '!=', rec.id),
                    ('bl_number', '=', rec.bl_number),
                    ('contract_id', '=', rec.contract_id.id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        f"The BL '{rec.bl_number}' exists already for this contract '{rec.contract_id.name}'.\n"
                        f"The same BL number cannot be used twice for the same contract."
                    )

    @api.constrains('price_unit')
    def _check_price_unit(self):
        for rec in self:
            if rec.price_unit <= 0:
                raise ValidationError("Le prix unitaire (P.U) doit être strictement supérieur à 0.")

    def action_confirm_purchase(self):
        # FIX: Allow regular purchase users to confirm too
        if not self.env.user.has_group('achat.group_purchase_user'):
            raise ValidationError("Only Purchase Users/Managers can confirm a dossier.")
        self.write({'purchase_state': 'confirmed'})

    def action_reset_to_initial(self):
        """Admin-only: Reset purchase state back to Initial."""
        self.write({'purchase_state': 'initial'})

    def action_reset_to_draft(self):
        """Admin-only: Reset purchase state back to Draft."""
        self.write({'purchase_state': 'draft'})

    legacy_article_id = fields.Many2one('logistique.article', string='Article (Ancien)', readonly=True)
    achat_article_id = fields.Many2one('achat.article', string='Article')
    details = fields.Char(string='Details')

    @api.onchange('contract_id')
    def _onchange_contract_id(self):
        if self.contract_id:
            self.contract_num = self.contract_id.name
            self.supplier_id = self.contract_id.supplier_id
            self.ste_id = self.contract_id.ste_id
            self.achat_article_id = self.contract_id.article_id
            self.incoterm = self.contract_id.incoterm
            self.details = self.contract_id.details

            self.origin_id = self.contract_id.origin_id
            self.free_time_negotiated = self.contract_id.free_time_negotiated
            # Pre-fill actual free time with negotiated value
            self.free_time = self.contract_id.free_time_negotiated
            if self.contract_id.weight_total:
                self.weight = self.contract_id.weight_total # Optional sync, user might update per shipment

    def action_generate_excel_dossiers_to_exit(self):
        if not xlsxwriter:
            raise ValidationError("La bibliothèque xlsxwriter n'est pas installée.")

        from datetime import datetime, time

        def to_xlsx_date(d):
            if not d:
                return None
            return datetime.combine(d, time.min)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Styles
        title_style = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
        header_style = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': '#f2f2f2'})
        cell_style = workbook.add_format({'border': 1})
        money_style = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        weight_style = workbook.add_format({'border': 1, 'num_format': '#,##0.000'})
        date_style = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy'})
        total_style = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#e6e6e6', 'num_format': '#,##0.00'})

        sheet = workbook.add_worksheet("Dossiers à Sortir")

        # Colonnes
        sheet.set_column(0, 0, 20)  # Société
        sheet.set_column(1, 1, 20)  # Supplier
        sheet.set_column(2, 2, 15)  # Invoice
        sheet.set_column(3, 3, 20)  # Article
        sheet.set_column(4, 4, 30)  # Details
        sheet.set_column(5, 5, 12)  # Poids
        sheet.set_column(6, 6, 12)  # UP
        sheet.set_column(7, 7, 15)  # Total
        sheet.set_column(8, 8, 12)  # Incoterm
        sheet.set_column(9, 9, 12)  # Franchise
        sheet.set_column(10, 10, 25) # Conteneurs
        sheet.set_column(11, 11, 15) # ETA
        sheet.set_column(12, 12, 35) # Commentaire

        sheet.merge_range('A1:M1', "Liste des Dossiers à Sortir", title_style)

        row = 2

        headers = [
            "Société", "Supplier", "Invoice Number", "Article", "Details",
            "Poids", "UP", "Total Montant", "Incoterm", "Franchise",
            "Conteneurs", "ETA", "Commentaire Sortie"
        ]
        sheet.write_row(row, 0, headers, header_style)
        row += 1

        total_montant = 0.0

        for rec in self:
            sheet.write(row, 0, rec.ste_id.name if rec.ste_id else "", cell_style)
            sheet.write(row, 1, rec.supplier_id.name if rec.supplier_id else "", cell_style)
            sheet.write(row, 2, rec.invoice_number or "", cell_style)
            sheet.write(row, 3, rec.achat_article_id.name if rec.achat_article_id else "", cell_style)
            sheet.write(row, 4, rec.details or "", cell_style)
            
            sheet.write_number(row, 5, float(rec.weight or 0.0), weight_style)
            sheet.write_number(row, 6, float(rec.price_unit or 0.0), money_style)
            sheet.write_number(row, 7, float(rec.amount_total or 0.0), money_style)
            
            total_montant += float(rec.amount_total or 0.0)

            sheet.write(row, 8, rec.incoterm.upper() if rec.incoterm else "", cell_style)
            sheet.write(row, 9, rec.free_time or "", cell_style)
            sheet.write(row, 10, rec.container_names or "", cell_style)
            
            dt_eta = to_xlsx_date(rec.eta)
            if dt_eta:
                sheet.write_datetime(row, 11, dt_eta, date_style)
            else:
                sheet.write(row, 11, "", cell_style)
                
            sheet.write(row, 12, rec.exit_comment or "", cell_style)
            
            row += 1

        # Ligne de Total (seulement Total Montant selon demande)
        sheet.merge_range(row, 0, row, 6, "Total", total_style)
        sheet.write_number(row, 7, total_montant, total_style)
        
        # Style vide pour le reste
        for col in range(8, 13):
            sheet.write(row, col, "", total_style)

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        output.close()

        filename = "Dossiers_A_Sortir.xlsx"

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': file_data,
            'type': 'binary',
            'res_model': self._name,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
