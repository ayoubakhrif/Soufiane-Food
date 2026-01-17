/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

const SCOPES = 'https://www.googleapis.com/auth/drive.readonly';
let cachedToken = null;
let tokenExpiry = 0;

class DrivePicker extends Component {
    static template = "finance.DrivePicker";
    static props = { ...standardActionServiceProps };

    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.notification = useService("notification");
        this.wizardDetails = this.props.action.context || {};

        onWillStart(async () => {
            await loadJS("https://apis.google.com/js/api.js");
            await loadJS("https://accounts.google.com/gsi/client");
        });

        onMounted(async () => {
            try {
                const result = await this.rpc("/finance/drive/config");
                if (result.error) return this.showError(result.message);
                this.config = result.config;
                await this.loadGoogleApi();
            } catch (e) {
                this.showError("Init Error: " + e.message);
            }
        });
    }

    async loadGoogleApi() {
        await new Promise((resolve) => gapi.load('client:picker', resolve));

        // Check cache first
        if (cachedToken && Date.now() < tokenExpiry) {
            this.createPicker(cachedToken);
            return;
        }

        this.tokenClient = google.accounts.oauth2.initTokenClient({
            client_id: this.config.client_id,
            scope: SCOPES,
            callback: (response) => {
                if (response.error) return this.showError("Auth Error: " + response.error);

                // Cache token (expires_in is in seconds, usually 3600)
                cachedToken = response.access_token;
                // Set safe expiry (e.g. 50 mins instead of 60)
                tokenExpiry = Date.now() + (parseInt(response.expires_in) * 1000) - 300000;

                this.createPicker(response.access_token);
            },
        });

        // Skip prompt if we have a hint? We don't.
        // But prompt:'' usually attempts silent.
        this.tokenClient.requestAccessToken({ prompt: '' });
    }

    createPicker(accessToken) {
        if (!accessToken) return this.showError("No access token");

        const view = new google.picker.DocsView(google.picker.ViewId.DOCS);
        // Include folders in mime types so they are visible!
        view.setMimeTypes("application/pdf,image/png,image/jpeg,image/jpg,application/vnd.google-apps.folder");
        view.setIncludeFolders(true);
        // Allow navigating properly
        view.setSelectFolderEnabled(false); // Can't select folders, only open them

        // Restrict to specific folder if configured
        if (this.config.folder_id) {
            view.setParent(this.config.folder_id);
        }

        const pickerBuilder = new google.picker.PickerBuilder()
            .enableFeature(google.picker.Feature.NAV_HIDDEN)
            .setAppId(this.config.app_id)
            .setOAuthToken(accessToken)
            .addView(view)
            .setDeveloperKey(this.config.api_key)
            .setCallback(this.pickerCallback.bind(this));

        // Disable multi-select explicitly (it is disabled by default usually but good to be sure)
        // To disable it, we just DON'T enable it. 
        // But the user requested "Disable Multi-Select".
        // .enableFeature(google.picker.Feature.MULTISELECT_ENABLED) <-- WAS HERE, REMOVING IT.

        pickerBuilder.build().setVisible(true);
    }

    async pickerCallback(data) {
        if (data[google.picker.Response.ACTION] == google.picker.Action.PICKED) {
            const doc = data[google.picker.Response.DOCUMENTS][0];

            const fileData = {
                drive_file_id: doc[google.picker.Document.ID],
                file_name: doc[google.picker.Document.NAME],
                drive_url: doc[google.picker.Document.URL],
                // Add explicit view mode to URL if missing? Usually URL is fine.
            };

            await this.processSelection(fileData);

        } else if (data[google.picker.Response.ACTION] == google.picker.Action.CANCEL) {
            // User cancelled, close the wizard action
            this.action.doAction({ type: "ir.actions.act_window_close" });
        }
    }

    async processSelection(fileData) {
        try {
            const result = await this.rpc("/finance/drive/document/create", {
                wizard_id: this.wizardDetails.wizard_id,
                drive_file_id: fileData.drive_file_id,
                file_name: fileData.file_name,
                drive_url: fileData.drive_url,
            });

            if (result.error) {
                this.showError(result.message);
            } else {
                this.notification.add(result.message, { type: "success" });
                // Close wizard and reloading is handled by returning action close from server usually,
                // but here we are in a client action.
                // We should close this client action and refresh the underlying view.

                await this.action.doAction({ type: "ir.actions.act_window_close" });
                // Trigger reload of the underlying form (passed in context or just reload active)
                // Since this opened in 'new' (dialog) ideally, or fullscreen?
                // The wizard action usually opens in dialog. Client action replaces it.
                // We might need to reload the cheque page.
                window.location.reload(); // Brute force or cleaner action service reload
            }
        } catch (e) {
            this.showError("Error saving document: " + e.message);
        }
    }

    showError(msg) {
        this.notification.add(msg, { type: "danger", sticky: true });
        // Close on error after delay? Or let user close.
        this.action.doAction({ type: "ir.actions.act_window_close" });
    }
}

registry.category("actions").add("finance_drive_picker", DrivePicker);
