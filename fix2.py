with open('custom-addons/finance_2/controllers/whatsapp_finance_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_response = """                return {
                    'status': 'success',
                    'product_name': f"Chèques Semaine {week_str}",
                    'response': f"Voici le rapport des chèques pour la semaine *{week_str}*." + 
                                (f"\n\n🚨 *Journaux manquants ({len(missing_journals)} chqs) :* {', '.join(map(str, missing_journals))}" if missing_journals else "") +
                                (f"\n\n🛑 *Chq vide absent ({len(chq_vide_missing_journals)} chqs) :* Les journaux des chqs sans pdf de chq vide: {', '.join(sorted(chq_vide_missing_journals))}" if chq_vide_missing_journals else "") +
                                (f"\n\n🛑 *Documentation absente ({len(doc_missing_journals)} chqs) :* Journaux des chqs sans pdf de documentation: {', '.join(sorted(doc_missing_journals))}" if doc_missing_journals else ""),
                    'files': [
                        {
                            'pdf_base64': pdf_base64,
                            'file_name': f"Cheques_{week_str}.pdf",
                            'caption': f"Chèques de la semaine {week_str} 📅"
                        }
                    ]
                }"""

new_response = """                encaisse_label = " ENCAISSÉS" if only_encaisse else ""
                return {
                    'status': 'success',
                    'product_name': f"Chèques{encaisse_label.title()} Semaine {week_str}",
                    'response': f"Voici le rapport des chèques{encaisse_label.lower()} pour la semaine *{week_str}*." + 
                                (f"\n\n🚨 *Journaux manquants ({len(missing_journals)} chqs) :* {', '.join(map(str, missing_journals))}" if missing_journals and not only_encaisse else "") +
                                (f"\n\n🛑 *Chq vide absent ({len(chq_vide_missing_journals)} chqs) :* Les journaux des chqs sans pdf de chq vide: {', '.join(sorted(chq_vide_missing_journals))}" if chq_vide_missing_journals else "") +
                                (f"\n\n🛑 *Documentation absente ({len(doc_missing_journals)} chqs) :* Journaux des chqs sans pdf de documentation: {', '.join(sorted(doc_missing_journals))}" if doc_missing_journals else ""),
                    'files': [
                        {
                            'pdf_base64': pdf_base64,
                            'file_name': f"Cheques_{week_str}{'_encaisses' if only_encaisse else ''}.pdf",
                            'caption': f"Chèques{encaisse_label.lower()} de la semaine {week_str} 📅"
                        }
                    ]
                }"""

content = content.replace(old_response, new_response)

old_h2 = '<h2>Documents de la Semaine {week_str}</h2>'
new_h2 = '<h2>Documents{encaisse_label.lower()} de la Semaine {week_str}</h2>'
content = content.replace(old_h2, new_h2)

with open('custom-addons/finance_2/controllers/whatsapp_finance_api.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Response fixed")
