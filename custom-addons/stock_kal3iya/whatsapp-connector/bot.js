/**
 * Stock Kal3iya — WhatsApp Web Connector
 * 
 * Bridges WhatsApp Web messages to the Odoo chatbot API.
 * 
 * Setup:
 *   1. Copy .env.example to .env and fill in values
 *   2. Run: npm install whatsapp-web.js qrcode-terminal axios dotenv
 *   3. Run: node bot.js
 *   4. Scan the QR code with your WhatsApp phone
 */

const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
require('dotenv').config();

// ─── Configuration ───────────────────────────────────────────────────────────

const ODOO_URL = process.env.ODOO_URL || 'https://gestia-soufianefoods.cloud';
const ODOO_API_TOKEN = process.env.ODOO_API_TOKEN || '';
const ALLOWED_NUMBERS = (process.env.ALLOWED_NUMBERS || '')
    .split(',')
    .map(n => n.trim())
    .filter(Boolean);

// ─── WhatsApp Client ─────────────────────────────────────────────────────────

const client = new Client({
    authStrategy: new LocalAuth({ dataPath: './.wwebjs_auth' }),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
    }
});

// Show QR code in terminal
client.on('qr', (qr) => {
    console.log('\n📱 Scannez ce QR code avec WhatsApp :\n');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('\n✅ WhatsApp connecté ! Le bot est prêt.\n');
});

client.on('auth_failure', (msg) => {
    console.error('❌ Échec d\'authentification :', msg);
});

client.on('disconnected', (reason) => {
    console.log('⚠️  Déconnecté :', reason);
});

// ─── Message Handler ─────────────────────────────────────────────────────────

client.on('message', async (msg) => {
    // Ignore group messages, status updates, and media
    if (msg.from.includes('@g.us') || msg.from === 'status@broadcast') return;
    if (!msg.body || msg.body.trim() === '') return;

    // Extract phone number (format: 212XXXXXXXXX@c.us)
    const sender = msg.from.replace('@c.us', '');

    // Check whitelist (if configured)
    if (ALLOWED_NUMBERS.length > 0 && !ALLOWED_NUMBERS.includes(sender)) {
        console.log(`🚫 Message ignoré de ${sender} (non autorisé)`);
        return;
    }

    console.log(`📩 Message de ${sender}: ${msg.body}`);

    try {
        // Call Odoo chat API
        const response = await axios.post(
            `${ODOO_URL}/api/stock_kal3iya/chat`,
            {
                message: msg.body,
                sender: sender,
            },
            {
                headers: {
                    'Authorization': `Bearer ${ODOO_API_TOKEN}`,
                    'Content-Type': 'application/json',
                },
                timeout: 30000, // 30s timeout (OpenAI can be slow)
            }
        );

        const reply = response.data.response || 'Erreur: pas de réponse.';
        console.log(`📤 Réponse: ${reply}`);
        await msg.reply(reply);

    } catch (error) {
        let errorMsg = 'Erreur interne. Veuillez réessayer.';

        if (error.response) {
            console.error(`❌ Odoo API error ${error.response.status}:`, error.response.data);
            if (error.response.status === 401) {
                errorMsg = 'Erreur d\'authentification avec le serveur.';
            }
        } else if (error.code === 'ECONNREFUSED') {
            console.error('❌ Impossible de se connecter à Odoo');
            errorMsg = 'Le serveur est indisponible.';
        } else {
            console.error('❌ Error:', error.message);
        }

        await msg.reply(errorMsg);
    }
});

// ─── Start ───────────────────────────────────────────────────────────────────

console.log('🚀 Démarrage du bot WhatsApp Stock Kal3iya...');
client.initialize();
