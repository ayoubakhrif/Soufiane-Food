import os

filepath = 'whatsapp_bridge/index.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add group ID
if 'DOSSIER_SEARCH_GROUP_ID' not in content:
    content = content.replace(
        'const DOSSIER_VERIF_GROUP_ID = "120363408433779149@g.us";',
        'const DOSSIER_VERIF_GROUP_ID = "120363408433779149@g.us";\nconst DOSSIER_SEARCH_GROUP_ID = "120363425063313711@g.us";'
    )

# 2. Add Odoo URL
if 'DOSSIER_SEARCH_ODOO_URL' not in content:
    content = content.replace(
        'const DOSSIER_VERIF_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/dossier_verification?db=soufianefoods";',
        'const DOSSIER_VERIF_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/dossier_verification?db=soufianefoods";\nconst DOSSIER_SEARCH_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/dossier_search?db=soufianefoods";'
    )

# 3. Add routing
if 'from === DOSSIER_SEARCH_GROUP_ID' not in content:
    target_route = '            } else if (from === DOSSIER_VERIF_GROUP_ID) {'
    new_route = '''            } else if (from === DOSSIER_SEARCH_GROUP_ID) {
                targetOdooUrl = DOSSIER_SEARCH_ODOO_URL;
                isClientRequest = false;
            } else if (from === DOSSIER_VERIF_GROUP_ID) {'''
    content = content.replace(target_route, new_route)

# 4. Add typeStr
if 'DOSSIER_SEARCH' not in content:
    target_typestr = '                else if (from === DOSSIER_VERIF_GROUP_ID) typeStr = "DOSSIER_VERIF";'
    new_typestr = '''                else if (from === DOSSIER_VERIF_GROUP_ID) typeStr = "DOSSIER_VERIF";
                else if (from === DOSSIER_SEARCH_GROUP_ID) typeStr = "DOSSIER_SEARCH";'''
    content = content.replace(target_typestr, new_typestr)

# 5. Add documents_to_send logic
if 'documents_to_send' not in content:
    target_docs = '''                    if (result && result.message && !hasAction) {
                        await sock.sendMessage(from, { text: result.message });
                        hasAction = true;
                    }'''
    new_docs = '''                    if (result && result.message && !hasAction) {
                        await sock.sendMessage(from, { text: result.message });
                        hasAction = true;
                    }
                    if (result && result.documents_to_send) {
                        for (const doc of result.documents_to_send) {
                            try {
                                const buffer = Buffer.from(doc.base64, 'base64');
                                await sock.sendMessage(from, { 
                                    document: buffer, 
                                    mimetype: doc.mimetype || 'application/pdf', 
                                    fileName: doc.name 
                                });
                            } catch (e) {
                                console.error("Error sending document:", e);
                            }
                        }
                        hasAction = true;
                    }'''
    content = content.replace(target_docs, new_docs)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Patch complete.')
