import os
import re

api_path = r'c:\odoo-repos\Soufiane-Food\custom-addons\generate_bons\controllers\whatsapp_bon_api.py'
with open(api_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace parsing logic block
old_parsing_block = """            company_code = None
            date_str = None
            poids_fictif = None
            article_lines = []
            
            parsing_articles = False
            
            for line in lines:
                line_upper = line.upper()
                if line_upper.startswith('SOCIETE:') or line_upper.startswith('SOCIÉTÉ:'):
                    company_code = line.split(':', 1)[1].strip()
                elif line_upper.startswith('DATE:'):
                    date_str = line.split(':', 1)[1].strip()
                elif line_upper.startswith('POIDS FICTIF:'):
                    try:
                        poids_fictif_str = line.split(':', 1)[1].strip().lower().replace('kg', '').replace('t', '').replace('tonnes', '').replace(',', '.').strip()
                        poids_fictif = float(poids_fictif_str)
                    except ValueError:
                        pass
                elif line_upper.startswith('ARTICLES:'):
                    parsing_articles = True
                elif parsing_articles and line.startswith(('-', '*', '•', '·')):
                    line_content = line[1:].strip()
                    art_name = ""
                    qte = 0.0
                    
                    if '|' in line_content:
                        parts = [p.strip() for p in line_content.split('|')]
                        if len(parts) >= 2:
                            art_name = parts[0]
                            qte = float(parts[1].replace(',', '.'))
                    else:
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
                            'qte': qte
                        })"""

# Handle encoding issues by doing a regex replace for the parsing loop
import re

# I will use a regex to replace everything from "company_code = None" to "if not company_code:"
pattern = re.compile(r"company_code = None.*?if not company_code:", re.DOTALL)

new_parsing_block = """company_code = None
            date_str = None
            poids_fictif = None
            article_lines = []
            
            parsing_articles = False
            
            for line in lines:
                line_upper = line.upper().strip()
                
                if line_upper.startswith('SOCIETE') or line_upper.startswith('SOCIÉTÉ') or line_upper.startswith('SOCIETE') or line_upper.startswith('SOCIÉTÉ'):
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
                    # Clean line from prefixes like -, *, etc.
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
                            'qte': qte
                        })
            
            if not company_code:"""

content = pattern.sub(new_parsing_block, content)

with open(api_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated parsing logic")
