csv_content = """access_sutra_config_ste_user,access.sutra.config.ste.user,model_sutra_config_ste,finance_2.group_finance2_user,1,0,0,0
access_sutra_config_ste_manager,access.sutra.config.ste.manager,model_sutra_config_ste,finance_2.group_finance2_manager,1,1,1,1
"""
with open('custom-addons/tanger_med/security/ir.model.access.csv', 'a', encoding='utf-8') as f:
    f.write(csv_content)
print("Updated ir.model.access.csv")
