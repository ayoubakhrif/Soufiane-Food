import os
import re

api_path = r'c:\odoo-repos\Soufiane-Food\custom-addons\finance_2\controllers\whatsapp_finance_api.py'
with open(api_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add a continue at the end of the CHQ_V2 block
old_block = """                            if idx == 0:
                                html_content += f"<td rowspan='{row_span}'>{phys_amount}</td>"
                                html_content += f"<td rowspan='{row_span}'>{global_state}</td>"
                                
                            html_content += "</tr>"

                elif doc['type_doc'] == 'CHQ':"""

new_block = """                            if idx == 0:
                                html_content += f"<td rowspan='{row_span}'>{phys_amount}</td>"
                                html_content += f"<td rowspan='{row_span}'>{global_state}</td>"
                                
                            html_content += "</tr>"
                            
                    continue

                elif doc['type_doc'] == 'CHQ':"""

content = content.replace(old_block, new_block)

with open(api_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Added continue to skip grouped_rows")
