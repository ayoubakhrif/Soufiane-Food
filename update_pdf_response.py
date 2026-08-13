import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/controllers/whatsapp_finance_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_return = """        choices = [f"DOC_LINK_VIDE_{cheque.id}", f"DOC_LINK_DOC_{cheque.id}"]
        return {
            'status': 'success',
            'response': msg,
            'choices': choices
        }"""

new_return = """        # Direct PDF attachments if available
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
            })

        return {
            'status': 'success',
            'response': msg,
            'files': files,
            'product_name': f"Chèque #{cheque.name}"
        }"""

content = content.replace(old_return, new_return)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated whatsapp_finance_api.py to send PDFs directly")
