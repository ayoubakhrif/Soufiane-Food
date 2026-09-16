import os

filepath = 'custom-addons/finance_2/views/cheque_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_code = """for record in records:
    if record.name and record.ste_id:
        talon = record.find_matching_talon(record.name, record.ste_id.id)
        if talon:
            record.write({'talon_id': talon.id})"""

new_code = """for record in records:
    if record.name and record.ste_id and record.name.isdigit():
        num = int(record.name)
        talons = env['finance2.talon'].search([('ste_id', '=', record.ste_id.id)])
        for t in talons:
            if t.first_cheque_number and t.last_cheque_number and t.first_cheque_number.isdigit() and t.last_cheque_number.isdigit():
                if int(t.first_cheque_number) &lt;= num &lt;= int(t.last_cheque_number):
                    record.write({'talon_id': t.id})
                    break"""

content = content.replace(old_code, new_code)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated Server Action")
