from odoo import models, fields, api

class ReportFinanceSituation(models.AbstractModel):
    _name = 'report.finance.report_finance_situation_template'
    _description = 'Rapport de Situation des Chèques Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        # 1. Active checks general recap (grouped by company)
        active_recs = self.env['datacheque'].sudo().search([('state', '=', 'actif')])
        
        ste_summary = {}
        for chq in active_recs:
            ste_name = chq.ste_id.name or 'Inconnu'
            if ste_name not in ste_summary:
                ste_summary[ste_name] = {
                    'ste_name': ste_name,
                    'count': 0,
                    'total_amount': 0.0
                }
            ste_summary[ste_name]['count'] += 1
            ste_summary[ste_name]['total_amount'] += chq.amount

        ste_summary_list = list(ste_summary.values())
        ste_summary_list.sort(key=lambda x: x['ste_name'])

        total_active_count = len(active_recs)
        total_active_amount = sum(active_recs.mapped('amount')) or 0.0

        # 2. Detailed Reserve Checks
        reserve_recs = self.env['datacheque'].sudo().search([('state', '=', 'reserve')], order='chq asc')
        reserve_list = []
        for chq in reserve_recs:
            reserve_list.append({
                'chq': chq.chq,
                'ste': chq.ste_id.name or 'Inconnu',
                'perso': chq.perso_id.name or 'Inconnu',
                'benif': chq.benif_id.name or 'Inconnu',
                'amount': chq.amount,
                'date_emission': chq.date_emission,
                'date_echeance': chq.date_echeance,
            })
        reserve_list.sort(key=lambda x: (x['ste'].lower(), x['chq'] or ''))
        total_reserve_count = len(reserve_recs)
        total_reserve_amount = sum(reserve_recs.mapped('amount')) or 0.0

        # 3. Detailed Bureau Checks
        bureau_recs = self.env['datacheque'].sudo().search([('state', '=', 'bureau')], order='chq asc')
        bureau_list = []
        for chq in bureau_recs:
            bureau_list.append({
                'chq': chq.chq,
                'ste': chq.ste_id.name or 'Inconnu',
                'perso': chq.perso_id.name or 'Inconnu',
                'benif': chq.benif_id.name or 'Inconnu',
                'amount': chq.amount,
                'date_emission': chq.date_emission,
                'date_echeance': chq.date_echeance,
            })
        bureau_list.sort(key=lambda x: (x['ste'].lower(), x['chq'] or ''))
        total_bureau_count = len(bureau_recs)
        total_bureau_amount = sum(bureau_recs.mapped('amount')) or 0.0

        # 4. Detailed Annulé Checks
        annule_recs = self.env['datacheque'].sudo().search([('state', '=', 'annule')], order='chq asc')
        annule_list = []
        for chq in annule_recs:
            annule_list.append({
                'chq': chq.chq,
                'ste': chq.ste_id.name or 'Inconnu',
                'perso': chq.perso_id.name or 'Inconnu',
                'benif': chq.benif_id.name or 'Inconnu',
                'amount': chq.amount,
                'date_emission': chq.date_emission,
                'date_echeance': chq.date_echeance,
            })
        annule_list.sort(key=lambda x: (x['ste'].lower(), x['chq'] or ''))
        total_annule_count = len(annule_recs)
        total_annule_amount = sum(annule_recs.mapped('amount')) or 0.0

        # Overall summary stats
        global_count = total_active_count + total_reserve_count + total_bureau_count + total_annule_count
        global_amount = total_active_amount + total_reserve_amount + total_bureau_amount + total_annule_amount

        return {
            'doc_ids': docids,
            'doc_model': 'finance.cheque.physical',
            'active_summary': ste_summary_list,
            'total_active_count': total_active_count,
            'total_active_amount': total_active_amount,
            
            'reserve_list': reserve_list,
            'total_reserve_count': total_reserve_count,
            'total_reserve_amount': total_reserve_amount,
            
            'bureau_list': bureau_list,
            'total_bureau_count': total_bureau_count,
            'total_bureau_amount': total_bureau_amount,
            
            'annule_list': annule_list,
            'total_annule_count': total_annule_count,
            'total_annule_amount': total_annule_amount,
            
            'global_count': global_count,
            'global_amount': global_amount,
            
            'report_date': fields.Date.today().strftime('%d/%m/%Y'),
        }
