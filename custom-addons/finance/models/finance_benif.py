from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64
import io
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

class Cal3iyaClient(models.Model):
    _name = 'finance.benif'
    _description = 'Bénificiaires'

    name = fields.Char(string='Bénificiaire', required=True)
    days = fields.Integer(string='Jours de plus')
    type = fields.Selection([
        ('import', 'Importation'),
        ('divers', 'Divers'),
        ('bureau', 'Bureau'),
        ('annule', 'Annulé'),
        ], string='Imp/Div', required=True, store=True)

    benif_deduction = fields.Boolean(string="Autorise Paiement par Déduction", default=False)

    physical_chq_ids = fields.One2many(
        'finance.cheque.physical',
        'benif_id',
        string="Chèques Physiques"
    )

    total_credit = fields.Float(string="Total Crédit", compute="_compute_chq_totals")
    total_debit = fields.Float(string="Total Encaissé", compute="_compute_chq_totals")
    solde = fields.Float(string="Solde à ce jour", compute="_compute_chq_totals")

    @api.depends('physical_chq_ids.credit', 'physical_chq_ids.debit')
    def _compute_chq_totals(self):
        for rec in self:
            rec.total_credit = sum(rec.physical_chq_ids.mapped('credit'))
            rec.total_debit = sum(rec.physical_chq_ids.mapped('debit'))
            rec.solde = rec.total_credit - rec.total_debit

    def action_export_excel(self):
        self.ensure_one()
        if not xlsxwriter:
            raise ValidationError("The library xlsxwriter is not installed.")

        from datetime import datetime, time

        def to_xlsx_date(d):
            if not d:
                return None
            return datetime.combine(d, time.min)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Styles
        title_style = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
        section_style = workbook.add_format({'bold': True, 'font_size': 12, 'bg_color': '#f2f2f2', 'border': 1})
        header_style = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': '#f2f2f2'})
        cell_style = workbook.add_format({'border': 1})
        money_style = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        date_style = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy'})

        sheet = workbook.add_worksheet("Détails Bénéficiaire")
        
        # Colonnes
        sheet.set_column(0, 0, 18)  # N° Chèque
        sheet.set_column(1, 1, 25)  # Société
        sheet.set_column(2, 2, 18)  # Date d'émission
        sheet.set_column(3, 3, 18)  # Date d'échéance
        sheet.set_column(4, 4, 18)  # Date d'encaissement
        sheet.set_column(5, 5, 18)  # Crédit
        sheet.set_column(6, 6, 18)  # Débit

        # Titre Principal
        sheet.merge_range('A1:G1', f"Détails du Bénéficiaire: {self.name}", title_style)

        # Date de relevé à droite
        from odoo import fields as odoo_fields
        sheet.set_column(7, 7, 18)
        sheet.set_column(8, 8, 15)
        sheet.write('H1', 'Date de relevé', header_style)
        sheet.write('I1', odoo_fields.Date.today().strftime('%d/%m/%Y'), cell_style)

        row = 2

        # -------------------------
        # Bloc Résumé
        # -------------------------
        sheet.merge_range(row, 0, row, 6, "Informations Générales", section_style)
        row += 1

        summary = [
            ("Nom", self.name or ""),
            ("Autorise Déduction", "Oui" if self.benif_deduction else "Non"),
            ("Total Crédit", self.total_credit or 0.0),
            ("Total Encaissé", self.total_debit or 0.0),
            ("Solde", self.solde or 0.0),
        ]

        for label, value in summary:
            sheet.write(row, 0, label, header_style)
            if isinstance(value, (int, float)):
                sheet.write_number(row, 1, float(value), money_style)
            else:
                sheet.write(row, 1, value or "", cell_style)
            row += 1

        row += 2  # Espace

        # -------------------------
        # Bloc Liste des Chèques
        # -------------------------
        sheet.merge_range(row, 0, row, 6, "Chèques Physiques", section_style)
        row += 1

        headers = [
            "N° Chèque", "Société", "Date d'émission", "Date d'échéance",
            "Date d'encaissement", "Crédit", "Débit"
        ]
        sheet.write_row(row, 0, headers, header_style)
        row += 1

        for chq in self.physical_chq_ids:
            # Numéro
            sheet.write(row, 0, chq.name or "", cell_style)
            # Société
            sheet.write(row, 1, chq.ste_id.name if chq.ste_id else "", cell_style)
            
            # Dates
            dt_em = to_xlsx_date(chq.date_emission)
            if dt_em: sheet.write_datetime(row, 2, dt_em, date_style)
            else: sheet.write(row, 2, "", cell_style)

            dt_ech = to_xlsx_date(chq.date_echeance)
            if dt_ech: sheet.write_datetime(row, 3, dt_ech, date_style)
            else: sheet.write(row, 3, "", cell_style)

            dt_enc = to_xlsx_date(chq.date_encaissement)
            if dt_enc: sheet.write_datetime(row, 4, dt_enc, date_style)
            else: sheet.write(row, 4, "", cell_style)

            # Montants
            sheet.write_number(row, 5, float(chq.credit or 0.0), money_style)
            sheet.write_number(row, 6, float(chq.debit or 0.0), money_style)

            row += 1

        workbook.close()
        output.seek(0)

        file_data = base64.b64encode(output.read())
        output.close()

        sanitized_name = "".join(c for c in (self.name or "") if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"Detail_Beneficiaire_{sanitized_name}.xlsx"

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': file_data,
            'type': 'binary',
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }