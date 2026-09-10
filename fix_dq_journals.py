import os

filepath = 'custom-addons/finance_2/controllers/whatsapp_finance_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    "journals = [int(dq.journal) for dq in datacheques if dq.journal and str(dq.journal).isdigit() and int(dq.journal) > 0]",
    "journals = [int(dq.journal) for dq in datacheques if getattr(dq, 'journal', False) and str(dq.journal).isdigit() and int(dq.journal) > 0]"
)
content = content.replace(
    "journals = [int(dq.journal) for dq in dqs_list if dq.journal and str(dq.journal).isdigit()]",
    "journals = [int(dq.journal) for dq in dqs_list if getattr(dq, 'journal', False) and str(dq.journal).isdigit()]"
)
content = content.replace("total_amount += dq.amount", "total_amount += getattr(dq, 'amount', 0.0)")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Re-applied getattr fixes")
