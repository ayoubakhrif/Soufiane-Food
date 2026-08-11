import re

with open('c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/controllers/whatsapp_finance_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the route
content = content.replace("'/api/whatsapp/finance'", "'/api/whatsapp/finance2'")

# 1. Add formatting method for finance2
new_format_method = """
    def _format_finance2_cheque_details(self, cheque):
        import pytz
        from datetime import datetime

        doc_name = cheque.name or "Inconnu"
        ste_name = cheque.ste_id.name if cheque.ste_id else "Non spécifié"
        benif_name = cheque.benif_id.name if cheque.benif_id else "Non spécifié"
        amount = '{:,.2f}'.format(cheque.amount_total).replace(',', ' ')
        
        date_em = cheque.date_emission.strftime('%d/%m/%Y') if cheque.date_emission else "Non spécifiée"
        date_ech = cheque.date_echeance.strftime('%d/%m/%Y') if cheque.date_echeance else "Non spécifiée"
        
        etat = dict(cheque._fields['state'].selection).get(cheque.state) or cheque.state
        
        msg = (
            f"📄 *Détails du Chèque (Finance V2)*\\n\\n"
            f"• *Numéro* : {doc_name}\\n"
            f"• *Société* : {ste_name}\\n"
            f"• *Bénéficiaire* : {benif_name}\\n"
            f"• *Montant* : {amount} DH\\n"
            f"• *Date d'émission* : {date_em}\\n"
            f"• *Date d'échéance* : {date_ech}\\n"
            f"• *État actuel* : {etat}\\n"
        )
        
        if cheque.remis_a_id:
            msg += f"• *Logistique* : Remis à {cheque.remis_a_id.name}\\n"

        if cheque.repartition_ids:
            msg += "\\n📋 *Répartitions* :\\n"
            for rep in cheque.repartition_ids:
                rep_amt = '{:,.2f}'.format(rep.amount).replace(',', ' ')
                msg += f"  - {rep_amt} DH (Fact: {rep.serie_facture or 'N/A'})\\n"

        choices = [f"DOC_LINK_VIDE_{cheque.id}", f"DOC_LINK_DOC_{cheque.id}"]
        return {
            'status': 'success',
            'response': msg,
            'choices': choices
        }
"""
# Insert before _format_physical_cheque_details
idx = content.find("def _format_physical_cheque_details")
if idx != -1:
    content = content[:idx] + new_format_method + "\n    " + content[idx:]

# 2. Update Direct Search to look in finance2 first
search_block = """cheques = request.env['finance.cheque.physical'].sudo().search([('name', '=', search_number)])"""
new_search_block = """
            # Search in finance2 first
            cheques_v2 = request.env['finance2.cheque'].sudo().search([('name', '=', search_number)])
            if cheques_v2:
                return self._format_finance2_cheque_details(cheques_v2[0])
            
            cheques = request.env['finance.cheque.physical'].sudo().search([('name', '=', search_number)])"""
content = content.replace(search_block, new_search_block)

# 3. Update Amount Search to look in finance2 first
amount_block = """phys_amount = request.env['finance.cheque.physical'].sudo().search([('amount_total', '=', amount_val)], order='date_emission desc', limit=30)"""
new_amount_block = """
            cheques_v2_amount = request.env['finance2.cheque'].sudo().search([('amount_total', '=', amount_val)], order='date_emission desc', limit=30)
            if cheques_v2_amount:
                if len(cheques_v2_amount) == 1:
                    return self._format_finance2_cheque_details(cheques_v2_amount[0])
                else:
                    unique_choices = []
                    choices_text = f"Plusieurs chèques (V2) trouvés avec le montant *{amount_val} DH*. Veuillez préciser le numéro.\\n"
                    for c in cheques_v2_amount:
                        choices_text += f"CHQ {c.name} ({c.ste_id.name})\\n"
                    return {'status': 'success', 'response': choices_text}

            phys_amount = request.env['finance.cheque.physical'].sudo().search([('amount_total', '=', amount_val)], order='date_emission desc', limit=30)"""
content = content.replace(amount_block, new_amount_block)

with open('c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/controllers/whatsapp_finance_api.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated finance bot api")
