import io
from odoo import http
from odoo.http import request

class Finance2ExportController(http.Controller):

    @http.route('/finance_2/export_benif_excel/<int:benif_id>', type='http', auth='user')
    def export_benif_excel(self, benif_id, **kwargs):
        benif = request.env['finance2.benif'].browse(benif_id)
        if not benif.exists():
            return request.not_found()

        try:
            import xlsxwriter
        except ImportError:
            return request.make_response("Bibliothèque xlsxwriter manquante.", headers=[('Content-Type', 'text/plain')])

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(f"Recapitulatif {benif.name[:20]}")

        # Formats
        bold = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1, 'align': 'center'})
        cell_format = workbook.add_format({'border': 1, 'align': 'center'})
        money_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00', 'align': 'right'})
        date_format = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy', 'align': 'center'})

        # Write Title
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
        sheet.merge_range('A1:H1', f"Récapitulatif des Chèques - {benif.name}", title_format)

        # Headers
        headers = ['Chèque', 'Société', 'Date Émission', 'Date Échéance', 'Date Encaissement', 'Crédit', 'Encaissement', 'État']
        for col, h in enumerate(headers):
            sheet.write(2, col, h, bold)
            sheet.set_column(col, col, 15)

        sheet.set_column(0, 0, 20) # Chèque
        sheet.set_column(1, 1, 20) # Société

        row = 3
        total_credit = 0.0
        total_encaisse = 0.0

        for chq in benif.cheque_ids:
            sheet.write(row, 0, chq.name or '', cell_format)
            sheet.write(row, 1, chq.ste_id.name if chq.ste_id else '', cell_format)
            sheet.write(row, 2, chq.date_emission.strftime('%d/%m/%Y') if chq.date_emission else '', date_format)
            sheet.write(row, 3, chq.date_echeance.strftime('%d/%m/%Y') if chq.date_echeance else '', date_format)
            sheet.write(row, 4, chq.date_encaissement.strftime('%d/%m/%Y') if chq.date_encaissement else '', date_format)
            
            credit = chq.amount_total or 0.0
            encaisse = chq.montant_encaisse or 0.0
            total_credit += credit
            total_encaisse += encaisse

            sheet.write(row, 5, credit, money_format)
            sheet.write(row, 6, encaisse, money_format)
            
            # Translate state
            state_dict = dict(chq._fields['state'].selection)
            state_label = state_dict.get(chq.state) or chq.state
            sheet.write(row, 7, state_label, cell_format)
            
            row += 1

        # Totals row
        total_bold = workbook.add_format({'bold': True, 'border': 1, 'align': 'right', 'bg_color': '#F0F0F0'})
        total_money = workbook.add_format({'bold': True, 'border': 1, 'num_format': '#,##0.00', 'align': 'right', 'bg_color': '#F0F0F0'})
        
        sheet.merge_range(row, 0, row, 4, 'Total:', total_bold)
        sheet.write(row, 5, total_credit, total_money)
        sheet.write(row, 6, total_encaisse, total_money)
        sheet.write(row, 7, '', total_bold)
        
        row += 1
        # Solde
        sheet.merge_range(row, 0, row, 4, 'Solde:', total_bold)
        sheet.write(row, 5, total_credit - total_encaisse, total_money)
        sheet.write(row, 6, '', total_bold)
        sheet.write(row, 7, '', total_bold)

        workbook.close()
        output.seek(0)

        filename = f"Recapitulatif_{benif.name.replace(' ', '_')}.xlsx"

        return request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename="{filename}"')
            ]
        )
