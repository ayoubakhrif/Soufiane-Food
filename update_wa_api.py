import os

filepath = 'custom-addons/finance_2/controllers/whatsapp_finance_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_logic = """            if journals:
                max_j = max(journals)
                expected_set = set(range(1, max_j + 1))
                actual_set = set(journals)
                missing_journals = sorted(list(expected_set - actual_set))"""

new_logic = """            if journals:
                max_j = max(journals)
                expected_set = set(range(1, max_j + 1))
                actual_set = set(journals)
                missing_journals = sorted(list(expected_set - actual_set))
                
                # Check for justified missing journals in V2 cheques history
                if missing_journals:
                    import re
                    actual_missing = []
                    for j in missing_journals:
                        is_justified = False
                        domain = [('history_journals', '!=', False)]
                        cheques_with_history = request.env['finance2.cheque'].sudo().search(domain)
                        for chq in cheques_with_history:
                            # Look for pattern: WXX - JX
                            pattern = rf"{week_str}.*?\bJ?{j}\b"
                            if re.search(pattern, chq.history_journals, re.IGNORECASE):
                                is_justified = True
                                break
                        if not is_justified:
                            actual_missing.append(j)
                    missing_journals = actual_missing"""

content = content.replace(old_logic, new_logic)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated whatsapp_finance_api.py")
