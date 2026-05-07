import os
import sys

# Set up Odoo environment
sys.path.append(r"c:\odoo-repos\Soufiane-Food")

import odoo
from odoo import api, SUPERUSER_ID

# Configure Odoo
odoo.tools.config.parse_config([])
# Let's find the database name
db_name = "soufianefoods"

registry = odoo.registry(db_name)
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Find some physical cheque with PDF
    cheques = env['finance.cheque.physical'].search([('cheque_copy_pdf', '!=', False)], limit=1)
    if cheques:
        chq = cheques[0]
        pdf_val = chq.cheque_copy_pdf
        print(f"Cheque ID: {chq.id}")
        print(f"Type of cheque_copy_pdf: {type(pdf_val)}")
        if pdf_val:
            print(f"Length of cheque_copy_pdf: {len(pdf_val)}")
            preview = pdf_val[:100]
            print(f"Preview of cheque_copy_pdf: {preview}")
            if isinstance(pdf_val, bytes):
                print("It is bytes!")
            else:
                print("It is string!")
    else:
        print("No cheques with PDF found.")
