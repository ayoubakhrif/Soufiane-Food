from odoo import models, fields, api

class ClaimsSummaryReport(models.AbstractModel):
    _name = 'report.claims.report_claims_summary_template'
    _description = 'Claims Summary Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        claims_models = [
            ('claims.quantity', 'Quantity Claim'),
            ('claims.quality', 'Quality Claim'),
            ('claims.dhl.delay', 'DHL Delay Claim'),
            ('claims.franchise.difference', 'Franchise Difference Claim'),
            ('claims.divers', 'Divers Claim')
        ]

        claims_list = []
        for model_name, type_label in claims_models:
            if model_name in self.env:
                records = self.env[model_name].sudo().search([('state', 'not in', ('closed', 'refused'))])
                for rec in records:
                    bl_num = rec.bl_id.bl_number if rec.bl_id else 'Inconnu'
                    supplier_name = rec.supplier_id.name if rec.supplier_id else 'Inconnu'
                    article_name = rec.article_id.name if rec.article_id else 'Inconnu'
                    ste_name = rec.company_id.name if rec.company_id else 'Inconnu'
                    
                    state_val = rec.state
                    state_selection = dict(rec._fields['state'].selection)
                    state_label = state_selection.get(state_val, state_val)

                    claims_list.append({
                        'id': rec.id,
                        'type': type_label,
                        'model': model_name,
                        'bl': bl_num or 'Inconnu',
                        'bl_id': rec.bl_id.id if rec.bl_id else False,
                        'supplier': supplier_name or 'Inconnu',
                        'article': article_name or 'Inconnu',
                        'ste': ste_name or 'Inconnu',
                        'claim_date': rec.claim_date.strftime('%d/%m/%Y') if rec.claim_date else '',
                        'amount_due': rec.amount_due or 0.0,
                        'state': state_label,
                        'state_raw': state_val,
                        'responsible': rec.responsible_id.name if rec.responsible_id else 'Non assigné'
                    })

        # Sort claims: empty/null bl numbers first or last (handles strings safely)
        claims_list.sort(key=lambda x: (x['bl'] or '', x['type'] or ''))

        total_amount = sum(c['amount_due'] for c in claims_list)
        total_claims = len(claims_list)

        return {
            'doc_ids': docids,
            'doc_model': 'logistique.entry',
            'claims': claims_list,
            'total_amount': total_amount,
            'total_claims': total_claims,
            'report_date': fields.Date.today().strftime('%d/%m/%Y'),
            'res_company': self.env.company,
        }
