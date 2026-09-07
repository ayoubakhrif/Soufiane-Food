import os

csv_path = 'custom-addons/tanger_med/security/ir.model.access.csv'
with open(csv_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_rules = """access_sutra_dossier_finance_user,access.sutra.dossier.finance.user,model_sutra_dossier,finance_2.group_finance2_user,1,1,1,0
access_sutra_dossier_finance_manager,access.sutra.dossier.finance.manager,model_sutra_dossier,finance_2.group_finance2_manager,1,1,1,1
access_sutra_facture_finance_user,access.sutra.facture.finance.user,model_sutra_facture,finance_2.group_finance2_user,1,1,1,0
access_sutra_facture_finance_manager,access.sutra.facture.finance.manager,model_sutra_facture,finance_2.group_finance2_manager,1,1,1,1
"""
with open(csv_path, 'a', encoding='utf-8') as f:
    f.write(new_rules)
print("Updated ir.model.access.csv")
