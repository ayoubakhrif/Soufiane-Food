import os
import re

api_path = r'c:\odoo-repos\Soufiane-Food\custom-addons\finance_2\controllers\whatsapp_finance_api.py'
with open(api_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the PDF part of _format_finance2_cheque_details
old_pdf_code = """        # Direct PDF attachments if available
        cheque_full = cheque.sudo().with_context(bin_size=False).browse(cheque.id)
        files = []
        if cheque_full.chq_vide_pdf:
            files.append({
                'pdf_base64': cheque_full.chq_vide_pdf.decode('utf-8') if isinstance(cheque_full.chq_vide_pdf, bytes) else cheque_full.chq_vide_pdf,
                'file_name': cheque_full.chq_vide_filename or f"Cheque_Vide_{cheque_full.name}.pdf",
                'caption': f"Chèque vide #{cheque_full.name}"
            })
        if cheque_full.doc_pdf:
            files.append({
                'pdf_base64': cheque_full.doc_pdf.decode('utf-8') if isinstance(cheque_full.doc_pdf, bytes) else cheque_full.doc_pdf,
                'file_name': cheque_full.doc_filename or f"Documentation_{cheque_full.name}.pdf",
                'caption': f"Documentation #{cheque_full.name}"
            })"""

new_pdf_code = """        # Direct PDF attachments if available
        cheque_full = cheque.sudo().with_context(bin_size=False).browse(cheque.id)
        files = []
        
        # 1. Variables to track if we found them in V2
        has_vide = False
        has_doc = False

        if cheque_full.chq_vide_pdf:
            has_vide = True
            files.append({
                'pdf_base64': cheque_full.chq_vide_pdf.decode('utf-8') if isinstance(cheque_full.chq_vide_pdf, bytes) else cheque_full.chq_vide_pdf,
                'file_name': cheque_full.chq_vide_filename or f"Cheque_Vide_{cheque_full.name}.pdf",
                'caption': f"Chèque vide #{cheque_full.name} (V2)"
            })
        if cheque_full.doc_pdf:
            has_doc = True
            files.append({
                'pdf_base64': cheque_full.doc_pdf.decode('utf-8') if isinstance(cheque_full.doc_pdf, bytes) else cheque_full.doc_pdf,
                'file_name': cheque_full.doc_filename or f"Documentation_{cheque_full.name}.pdf",
                'caption': f"Documentation #{cheque_full.name} (V2)"
            })

        # 2. Fallback to Old Finance for PDFs if missing
        if not has_vide or not has_doc:
            from odoo.http import request
            old_phys = request.env['finance.cheque.physical'].sudo().with_context(bin_size=False).search([('name', '=', cheque.name)], limit=1)
            if old_phys:
                if not has_vide and old_phys.chq_vide_pdf:
                    files.append({
                        'pdf_base64': old_phys.chq_vide_pdf.decode('utf-8') if isinstance(old_phys.chq_vide_pdf, bytes) else old_phys.chq_vide_pdf,
                        'file_name': old_phys.chq_vide_filename or f"Cheque_Vide_{old_phys.name}.pdf",
                        'caption': f"Chèque vide #{old_phys.name} (Ancien)"
                    })
                if not has_doc and old_phys.doc_pdf:
                    files.append({
                        'pdf_base64': old_phys.doc_pdf.decode('utf-8') if isinstance(old_phys.doc_pdf, bytes) else old_phys.doc_pdf,
                        'file_name': old_phys.doc_filename or f"Documentation_{old_phys.name}.pdf",
                        'caption': f"Documentation #{old_phys.name} (Ancien)"
                    })
                if hasattr(old_phys, 'cheque_copy_pdf') and old_phys.cheque_copy_pdf:
                    files.append({
                        'pdf_base64': old_phys.cheque_copy_pdf.decode('utf-8') if isinstance(old_phys.cheque_copy_pdf, bytes) else old_phys.cheque_copy_pdf,
                        'file_name': getattr(old_phys, 'cheque_copy_filename', False) or f"Cheque_{old_phys.name}.pdf",
                        'caption': f"Chèque #{old_phys.name} (Ancien)"
                    })"""

if old_pdf_code.replace("è", "") in content.replace("è", ""):
    # Encoding matches can be tricky, let's just do a rough replace using re if needed.
    pass

# Actually, the file has some encoding artifacts like "Chque". Let's handle it safely.
# I will just write a regex to replace everything between "# Direct PDF attachments if available" and "return {"

import re
pattern = re.compile(r'# Direct PDF attachments if available.*?return \{', re.DOTALL)
content = pattern.sub(new_pdf_code + "\n\n        return {", content)

with open(api_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('PDF fallback added')
