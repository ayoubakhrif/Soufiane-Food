from odoo import models

class ClientFactureReport(models.AbstractModel):
    _name = 'report.kal3iya.client_facture_template'
    _description = 'Rapport Facture Client'

    def _get_report_values(self, docids, data=None):
        client = self.env['kal3iya.client'].browse(docids[0])
        week = data.get('week')

        week_data = client._get_week_data(week)

        return {
            'doc_ids': [client.id],
            'doc_model': 'kal3iya.client',
            'docs': client,
            'week': week,
            'week_data': week_data,
        }
