import os

api_path = r'c:\odoo-repos\Soufiane-Food\custom-addons\generate_bons\controllers\whatsapp_bon_api.py'
with open(api_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if "for line in lines:" in line:
        start_idx = i
        # Find the end of the loop
        for j in range(i, len(lines)):
            if "if not company_code:" in lines[j]:
                end_idx = j
                break
        break

if start_idx != -1 and end_idx != -1:
    new_loop = """            for line in lines:
                line_upper = line.upper().strip()
                
                if line_upper.startswith('SOCIETE') or line_upper.startswith('SOCIÉTÉ') or line_upper.startswith('SOCI'):
                    if ':' in line_upper:
                        company_code = line.split(':', 1)[1].strip()
                    elif ' ' in line_upper:
                        company_code = line.split(' ', 1)[1].strip()
                elif line_upper.startswith('DATE'):
                    if ':' in line_upper:
                        date_str = line.split(':', 1)[1].strip()
                elif line_upper.startswith('POIDS FICTIF'):
                    if ':' in line_upper:
                        try:
                            poids_fictif_str = line.split(':', 1)[1].strip().lower().replace('kg', '').replace('t', '').replace('tonnes', '').replace(',', '.').strip()
                            poids_fictif = float(poids_fictif_str)
                        except ValueError:
                            pass
                elif line_upper.startswith('ARTICLE') or line_upper == 'ARTICLES':
                    parsing_articles = True
                elif parsing_articles:
                    line_content = line.strip()
                    if line_content.startswith(('-', '*', '•', '·')):
                        line_content = line_content[1:].strip()
                        
                    if not line_content:
                        continue
                        
                    art_name = ""
                    qte = 0.0
                    
                    if '|' in line_content:
                        parts = [p.strip() for p in line_content.split('|')]
                        if len(parts) >= 2:
                            art_name = parts[0]
                            qte = float(parts[1].replace(',', '.'))
                    else:
                        import re
                        match = re.match(r"^([\d.,]+)\s+(.+)$", line_content)
                        if match:
                            qte_str = match.group(1).replace(',', '.')
                            qte = float(qte_str)
                            art_name = match.group(2).strip()
                        else:
                            art_name = line_content
                            qte = 1.0
                    
                    if art_name:
                        article_lines.append({
                            'name': art_name,
                            'qte': qte,
                            'pu': None
                        })
            
"""
    new_lines = lines[:start_idx] + [new_loop] + lines[end_idx:]
    with open(api_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("Fixed parsing logic")
else:
    print("Could not find parsing block")
