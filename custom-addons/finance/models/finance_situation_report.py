from odoo import models, fields, api

class ReportFinanceSituation(models.AbstractModel):
    _name = 'report.finance.report_finance_situation_template'
    _description = 'Rapport de Situation des Chèques Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        # Fetch physical cheques instead of datacheques (répartitions)
        physical_recs = self.env['finance.cheque.physical'].sudo().search([])
        
        active_list_phys = []
        reserve_list_phys = []
        bureau_list_phys = []
        annule_list_phys = []
        
        for physical in physical_recs:
            if not physical.datacheque_ids:
                continue
            # Use the first linked datacheque as the source of state and person
            first_datacheque = physical.datacheque_ids[0]
            state = first_datacheque.state or 'reserve'
            
            item = {
                'chq': physical.name,
                'ste': physical.ste_id.name or 'Inconnu',
                'perso': first_datacheque.perso_id.name or 'Inconnu',
                'benif': physical.benif_id.name or 'Inconnu',
                'amount': physical.amount_total or 0.0,
                'date_emission': physical.date_emission,
                'date_echeance': physical.date_echeance,
            }
            
            if state == 'actif':
                active_list_phys.append(item)
            elif state == 'reserve':
                reserve_list_phys.append(item)
            elif state == 'bureau':
                bureau_list_phys.append(item)
            elif state == 'annule':
                annule_list_phys.append(item)

        # 1. Active checks general recap (grouped by company)
        ste_summary = {}
        for item in active_list_phys:
            ste_name = item['ste']
            if ste_name not in ste_summary:
                ste_summary[ste_name] = {
                    'ste_name': ste_name,
                    'count': 0,
                    'total_amount': 0.0
                }
            ste_summary[ste_name]['count'] += 1
            ste_summary[ste_name]['total_amount'] += item['amount']

        ste_summary_list = list(ste_summary.values())
        ste_summary_list.sort(key=lambda x: -x['total_amount'])

        total_active_count = len(active_list_phys)
        total_active_amount = sum(item['amount'] for item in active_list_phys)

        # 2. Detailed Reserve Checks (sorted by company, then amount descending, then check number ascending)
        reserve_list_phys.sort(key=lambda x: (x['ste'].lower(), -x['amount'], x['chq'] or ''))
        total_reserve_count = len(reserve_list_phys)
        total_reserve_amount = sum(item['amount'] for item in reserve_list_phys)

        # 3. Detailed Bureau Checks (sorted by company, then amount descending, then check number ascending)
        bureau_list_phys.sort(key=lambda x: (x['ste'].lower(), -x['amount'], x['chq'] or ''))
        total_bureau_count = len(bureau_list_phys)
        total_bureau_amount = sum(item['amount'] for item in bureau_list_phys)

        # 4. Detailed Annulé Checks (sorted by company, then amount descending, then check number ascending)
        annule_list_phys.sort(key=lambda x: (x['ste'].lower(), -x['amount'], x['chq'] or ''))
        total_annule_count = len(annule_list_phys)
        total_annule_amount = sum(item['amount'] for item in annule_list_phys)

        # Overall summary stats
        global_count = total_active_count + total_reserve_count + total_bureau_count + total_annule_count
        global_amount = total_active_amount + total_reserve_amount + total_bureau_amount + total_annule_amount

        return {
            'doc_ids': docids,
            'doc_model': 'finance.cheque.physical',
            'active_summary': ste_summary_list,
            'total_active_count': total_active_count,
            'total_active_amount': total_active_amount,
            
            'reserve_list': reserve_list_phys,
            'total_reserve_count': total_reserve_count,
            'total_reserve_amount': total_reserve_amount,
            
            'bureau_list': bureau_list_phys,
            'total_bureau_count': total_bureau_count,
            'total_bureau_amount': total_bureau_amount,
            
            'annule_list': annule_list_phys,
            'total_annule_count': total_annule_count,
            'total_annule_amount': total_annule_amount,
            
            'global_count': global_count,
            'global_amount': global_amount,
            
            'report_date': fields.Date.today().strftime('%d/%m/%Y'),
        }
