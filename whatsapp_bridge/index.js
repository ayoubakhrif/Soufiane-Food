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
const ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/stock?db=soufianefoods";
const API_KEY = "whatsapp_direct_quantity"; // À définir dans Odoo (Paramètres système)
const TARGET_GROUP_ID = "120363405648854156@g.us"; 

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

            // FILTRE : On ne répond qu'au groupe spécifique
            if (from !== TARGET_GROUP_ID) {
                console.log(`Ignoré (destinataire différent de ${TARGET_GROUP_ID})`);
                continue;
            }

            try {
                // APPEL À ODOO
                console.log(`Appel à Odoo pour : "${text}"`);
                const response = await axios.post(ODOO_URL, {
                    jsonrpc: "2.0",
                    params: {
                        message: text,
                        group_id: from
                    }
                }, {
                    headers: {
                        'X-Api-Key': API_KEY,
                        'Content-Type': 'application/json'
                    }
                });

                if (response.data.error) {
                    console.error("Erreur Odoo (JSON-RPC) :", JSON.stringify(response.data.error, null, 2));
                    return;
                }

                const result = response.data.result;
                console.log("Résultat Odoo :", result ? result.status : "AUCUN RESULTAT", result ? (result.message || "") : "");

                if (result && result.status === 'success') {
                    console.log(`Produit identifié : ${result.product_name}. Envoi du PDF...`);
                    
                    // Envoi du PDF
                    await sock.sendMessage(from, {
                        document: Buffer.from(result.pdf_base64, 'base64'),
                        mimetype: 'application/pdf',
                        fileName: result.file_name,
                        caption: `Voici le rapport de stock pour *${result.product_name}*.`
                    });
                } else if (result && result.status === 'not_found') {
                    console.log(`Non trouvé : ${result.message}`);
                    await sock.sendMessage(from, { text: result.message });
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
