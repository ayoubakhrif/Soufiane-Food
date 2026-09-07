with open('custom-addons/finance_2/controllers/whatsapp_finance_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_listcomp = "journals = [int(dq.journal) for dq in datacheques if dq.journal and int(dq.journal) > 0]"
new_listcomp = "journals = [int(dq.journal) for dq in datacheques if dq.journal and str(dq.journal).isdigit() and int(dq.journal) > 0]"

content = content.replace(old_listcomp, new_listcomp)

with open('custom-addons/finance_2/controllers/whatsapp_finance_api.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed list comprehension")
