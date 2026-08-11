import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/controllers/whatsapp_pdf_bot_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_logic = """                inv_amount = float(inv_data.get('montant', 0))
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
                messages.append(f"• {inv_amount} DH {bl_str}{fact_str}")"""

new_logic = """                inv_amount = float(inv_data.get('montant', 0))
                inv_facture_num = str(inv_data.get('numero_facture', '')).strip()
                inv_bl = str(inv_data.get('bl', '')).strip()
                inv_type = inv_data.get('type', '').lower()

                if inv_facture_num.lower() == 'none':
                    inv_facture_num = ''
                if inv_bl.lower() == 'none':
                    inv_bl = ''

                # Map AI type to Odoo selection
                type_val = False
                if inv_type in ['surestarie', 'magasinage', 'change']:
                    type_val = inv_type
                elif inv_type == 'thc':
                    type_val = 'change' # THC is basically change/port fees for them? Or maybe they didn't specify. I will let 'change' be used for THC if needed, but actually the user said: "change (THC)". So THC -> change.
                    
                # Create Repartition
                request.env['finance2.repartition'].sudo().create({
                    'cheque_id': base_cheque.id,
                    'amount': inv_amount,
                    'serie_facture': inv_facture_num,
                    'bl': inv_bl,
                    'type': type_val,
                })

                bl_str = f", BL: {inv_bl}" if inv_bl else ""
                fact_str = f", Fact: {inv_facture_num}" if inv_facture_num else ""
                type_str = f" ({type_val})" if type_val else ""
                messages.append(f"• {inv_amount} DH{type_str} {bl_str}{fact_str}")"""

content = content.replace(old_logic, new_logic)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Added type extraction mapping")
