const {
    makeWASocket,
    useMultiFileAuthState,
    DisconnectReason,
    getContentType,
    fetchLatestBaileysVersion
} = require('@whiskeysockets/baileys');
const { Boom } = require('@hapi/boom');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
const fs = require('fs');
const pino = require('pino');

// CONFIGURATION
const ARTICLE_GROUP_ID = "120363405648854156@g.us";
const CLIENT_GROUP_ID = "120363426234155722@g.us";
const STOCK_VALIDATION_GROUP_ID = "120363403203705514@g.us";
const FINANCE_GROUP_ID = "120363428965532100@g.us";
const LOGISTICS_GROUP_ID = "120363427755410654@g.us";
const DOUANE_GROUP_ID = "120363406635335778@g.us";
const SORTIE_GROUP_ID = "120363424919316319@g.us";

const ARTICLE_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/stock?db=soufianefoods";
const CLIENT_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/client?db=soufianefoods";
const STOCK_VALIDATION_ODOO_URL = "https://gestia-soufianefoods.cloud/api/stock_kal3iya/chat";
const FINANCE_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/finance?db=soufianefoods";
const LOGISTICS_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/logistics?db=soufianefoods";
const DOUANE_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/douane?db=soufianefoods";
const SORTIE_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/sortie?db=soufianefoods";

const API_KEY = "whatsapp_direct_quantity"; // À définir dans Odoo (Paramètres système)

let odooSessionCookie = '';
const pendingChoices = new Map(); // Garde en mémoire les menus interactifs par groupe

async function connectToWhatsApp() {
    const { version, isLatest } = await fetchLatestBaileysVersion();
    console.log(`Utilisation de la version WA v${version.join('.')} (Est la plus récente : ${isLatest})`);

    const { state, saveCreds } = await useMultiFileAuthState('auth_info_baileys');

    const sock = makeWASocket({
        version,
        auth: state,
        logger: pino({ level: 'debug' }),
        browser: ['Gestia Bot', 'Chrome', '114.0.5735.199'], // Version de Chrome fixe
        syncFullHistory: false, // Évite la synchronisation lourde au début
        generateHighQualityLinkPreview: true
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            console.log('--- SCANNEZ LE QR CODE CI-DESSOUS ---');
            qrcode.generate(qr, { small: true });
        }

        if (connection === 'close') {
            const statusCode = (lastDisconnect.error instanceof Boom) ?
                lastDisconnect.error.output.statusCode : 0;

            console.log(`Connexion fermée (Code: ${statusCode})...`);

            if (statusCode !== DisconnectReason.loggedOut) {
                console.log('Reconnexion en cours...');
                setTimeout(() => connectToWhatsApp(), 5000); // Attendre 5s avant de retenter
            } else {
                console.log('Déconnexion effectuée. Supprimez le dossier "auth_info_baileys" pour recommencer.');
            }
        } else if (connection === 'open') {
            console.log('--- CONNEXION WHATSAPP ÉTABLIE ---');
        }
    });

    sock.ev.on('messages.upsert', async (m) => {
        if (m.type !== 'notify') return;

        for (const msg of m.messages) {
            if (!msg.message || msg.key.fromMe) continue;

            const from = msg.key.remoteJid;
            const text = (getContentType(msg.message) === 'conversation') ? msg.message.conversation :
                (getContentType(msg.message) === 'extendedTextMessage') ? msg.message.extendedTextMessage.text : '';

            if (!text) continue;

            console.log(`Message de ${from} : "${text}"`);
            let realMessage = text;

            // DETERMINATION DU TYPE DE REQUÊTE SELON LE GROUPE
            let targetOdooUrl = "";
            let isClientRequest = false;

            if (from === ARTICLE_GROUP_ID) {
                targetOdooUrl = ARTICLE_ODOO_URL;
                isClientRequest = false;
            } else if (from === CLIENT_GROUP_ID) {
                targetOdooUrl = CLIENT_ODOO_URL;
                isClientRequest = true;
            } else if (from === STOCK_VALIDATION_GROUP_ID) {
                targetOdooUrl = STOCK_VALIDATION_ODOO_URL;
                isClientRequest = false;
            } else if (from === FINANCE_GROUP_ID) {
                targetOdooUrl = FINANCE_ODOO_URL;
                isClientRequest = true; // Use true to reuse the identifier/caption logic in bridge
            } else if (from === LOGISTICS_GROUP_ID) {
                targetOdooUrl = LOGISTICS_ODOO_URL;
                isClientRequest = false;
            } else if (from === DOUANE_GROUP_ID) {
                targetOdooUrl = DOUANE_ODOO_URL;
                isClientRequest = false;
            } else if (from === SORTIE_GROUP_ID) {
                targetOdooUrl = SORTIE_ODOO_URL;
                isClientRequest = false;
            } else {
                console.log(`Ignoré (destinataire ${from} non autorisé)`);
                continue;
            }

            // GESTION DU MENU INTERACTIF
            if (pendingChoices.has(from)) {
                const choices = pendingChoices.get(from);
                const choiceNum = parseInt(text.trim());
                if (!isNaN(choiceNum) && choiceNum > 0 && choiceNum <= choices.length) {
                    realMessage = choices[choiceNum - 1];
                    console.log(`Sélection utilisateur : Option ${choiceNum} -> "${realMessage}"`);
                    pendingChoices.delete(from); // Clear menu once selected
                } else if (!isNaN(choiceNum)) {
                    await sock.sendMessage(from, { text: "⚠️ Choix invalide. Veuillez répondre par le bon numéro." }, { quoted: msg });
                    continue; // Skip Odoo call
                } else {
                    // L'utilisateur a tapé une phrase, le menu est abandonné
                    pendingChoices.delete(from);
                }
            }

            try {
                // AUTHENTIFICATION ODOO (pour contourner le DB Proxy 404)
                if (!odooSessionCookie) {
                    console.log("Demande de session (Cookie) à Odoo...");
                    const authRes = await axios.post("https://gestia-soufianefoods.cloud/web/session/authenticate", {
                        jsonrpc: "2.0",
                        params: {
                            db: "soufianefoods",
                            login: "ai_whatsapp_bot@soufianefoods.com",
                            password: "0000"
                        }
                    });
                    if (authRes.headers['set-cookie']) {
                        odooSessionCookie = authRes.headers['set-cookie'].find(c => c.startsWith('session_id='));
                        console.log("Session Odoo activée.");
                    } else {
                        console.log("Impossible d'obtenir la session Odoo.");
                    }
                }

                // APPEL À ODOO
                let typeStr = "ARTICLE";
                if (from === STOCK_VALIDATION_GROUP_ID) typeStr = "STOCK_VAL";
                else if (from === CLIENT_GROUP_ID) typeStr = "CLIENT";
                else if (from === FINANCE_GROUP_ID) typeStr = "FINANCE";
                else if (from === LOGISTICS_GROUP_ID) typeStr = "LOGISTICS";
                else if (from === DOUANE_GROUP_ID) typeStr = "DOUANE";
                else if (from === SORTIE_GROUP_ID) typeStr = "SORTIE";

                console.log(`Appel à Odoo (${typeStr}) pour : "${realMessage}"`);
                const response = await axios.post(targetOdooUrl, {
                    jsonrpc: "2.0",
                    params: {
                        message: realMessage,
                        sender: from, // Used by stock_kal3iya
                        group_id: from // Used by others
                    }
                }, {
                    headers: {
                        'X-Api-Key': API_KEY,
                        'Content-Type': 'application/json',
                        'Cookie': odooSessionCookie || ''
                    }
                });

                if (response.data.error) {
                    console.error("Erreur Odoo (JSON-RPC) :", JSON.stringify(response.data.error, null, 2));
                    return;
                }

                const result = response.data.result;
                console.log("Résultat Odoo :", result ? result.status : "AUCUN RESULTAT", result ? (result.message || "") : "");

                if (result && result.status === 'multiple_choices') {
                    // C'est un menu de sélection
                    pendingChoices.set(from, result.choices);
                    await sock.sendMessage(from, { text: result.message }, { quoted: msg });
                }
                else if (result && result.response) {
                    // C'est une réponse textuelle simple (ex: chatbot stock)
                    console.log(`Réponse textuelle : ${result.response}`);
                    await sock.sendMessage(from, { text: result.response }, { quoted: msg });
                }
                else if (result && result.status === 'success') {
                    // Extract identifier (it might be in client_name or product_name depending on the controller result)
                    const identifier = result.client_name || result.product_name || "Bénéficiaire";
                    
                    let reportType = "de stock";
                    if (from === CLIENT_GROUP_ID) reportType = "de compte";
                    if (from === FINANCE_GROUP_ID) reportType = "financier";
                    if (from === DOUANE_GROUP_ID) reportType = "douane (DUM)";
                    if (from === SORTIE_GROUP_ID) reportType = "de sorties";

                    console.log(`Entité identifiée : ${identifier}. Envoi du/des PDF(s)...`);

                    // Support for multiple files
                    if (result.files && Array.isArray(result.files)) {
                        for (const file of result.files) {
                            await sock.sendMessage(from, {
                                document: Buffer.from(file.pdf_base64, 'base64'),
                                mimetype: 'application/pdf',
                                fileName: file.file_name,
                                caption: `Document DUM pour *${identifier}*.`
                            }, { quoted: msg });
                        }
                    } else if (result.pdf_base64) {
                        // Original single file support
                        await sock.sendMessage(from, {
                            document: Buffer.from(result.pdf_base64, 'base64'),
                            mimetype: 'application/pdf',
                            fileName: result.file_name,
                            caption: `Voici le rapport ${reportType} pour *${identifier}*.`
                        }, { quoted: msg });
                    }
                } else if (result && result.status === 'not_found') {
                    console.log(`Non trouvé : ${result.message}`);
                    await sock.sendMessage(from, { text: result.message }, { quoted: msg });
                } else {
                    console.log("Structure de réponse inattendue :", JSON.stringify(response.data, null, 2));
                }

            } catch (error) {
                console.error("Erreur d'appel Odoo :", error.message);
                if (error.response) {
                    console.error("Status Erreur :", error.response.status);
                    console.error("Data Erreur :", error.response.data);
                }
            }
        }
    });
}

connectToWhatsApp();
