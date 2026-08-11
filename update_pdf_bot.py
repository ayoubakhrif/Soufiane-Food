import re

with open('c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/controllers/whatsapp_pdf_bot_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the route
content = content.replace("'/api/whatsapp/finance/pdf'", "'/api/whatsapp/finance2/pdf'")

# Find the block starting at "5. Find the DataCheque" and ending at "except Exception as e:" inside whatsapp_finance_pdf_processor
start_marker = "# 5. Find the DataCheque in reserve or bureau"
end_marker = "        except Exception as e:\n            _logger.error(f\"Error updating/creating datacheques from PDF: {str(e)}\")"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    new_logic = """# 5. Find or Create the Cheque in finance_2
        domain = [('name', '=', chq_number)]
        base_cheque = request.env['finance2.cheque'].sudo().search(domain, limit=1)

        if not base_cheque:
            base_cheque = request.env['finance2.cheque'].sudo().create({
                'name': chq_number,
                'state': 'brouillon'
            })

        # Save the document PDF on the cheque
        if pdf_base64:
            base_cheque.sudo().write({
                'doc_pdf': pdf_base64,
                'doc_filename': file_name
            })

        messages = []
        try:
            for idx, inv_data in enumerate(factures):
                inv_amount = float(inv_data.get('montant', 0))
                inv_facture_num = str(inv_data.get('numero_facture', '')).strip()
                inv_bl = str(inv_data.get('bl', '')).strip()

                if inv_facture_num.lower() == 'none':
                    inv_facture_num = ''
                if inv_bl.lower() == 'none':
                    inv_bl = ''

                # Create Repartition
                request.env['finance2.repartition'].sudo().create({
                    'cheque_id': base_cheque.id,
                    'amount': inv_amount,
                    'serie_facture': inv_facture_num,
                    'bl': inv_bl,
                })

                bl_str = f", BL: {inv_bl}" if inv_bl else ""
                fact_str = f", Fact: {inv_facture_num}" if inv_facture_num else ""
                messages.append(f"• {inv_amount} DH {bl_str}{fact_str}")

            return {
                'status': 'success',
                'response': f"✅ *PDF traité avec succès (Finance V2) !*\\n\\n*Chèque N°:* {chq_number}\\n\\n*Répartitions ajoutées :*\\n" + "\\n".join(messages)
            }
"""
    content = content[:start_idx] + new_logic + content[end_idx:]

with open('c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/controllers/whatsapp_pdf_bot_api.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated pdf bot api")
