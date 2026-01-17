/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

class DrivePicker extends Component {
    static template = "finance.DrivePicker";
    static props = { ...standardActionServiceProps };

    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.notification = useService("notification");

        // Data from the wizard action
        this.wizardDetails = this.props.action.context || {};

        onWillStart(async () => {
            // Load Google APIs
            await loadJS("https://apis.google.com/js/api.js");
            await loadJS("https://accounts.google.com/gsi/client");
        });

        onMounted(async () => {
            try {
                // Fetch config
                const result = await this.rpc("/finance/drive/config");
                if (result.error) {
                    this.showError(result.message);
                    return;
                }
                this.config = result.config;

                // Initialize Google API
                await this.loadGoogleApi();

            } catch (e) {
                this.showError("Failed to initialize Google Drive: " + e.message);
            }
        });
    }

    async loadGoogleApi() {
        // Initialize gapi client
        await new Promise((resolve) => gapi.load('client:picker', resolve));

        // Initialize Identity Services
        this.tokenClient = google.accounts.oauth2.initTokenClient({
            client_id: this.config.client_id,
            scope: 'https://www.googleapis.com/auth/drive.readonly',
            callback: (response) => {
                if (response.error !== undefined) {
                    this.showError("Auth Error: " + response.error);
                    return;
                }
                this.createPicker(response.access_token);
            },
        });

        // Trigger auth flow (popup)
        if (gapi.client.getToken() === null) {
            this.tokenClient.requestAccessToken({ prompt: 'consent' });
        } else {
            this.tokenClient.requestAccessToken({ prompt: '' });
        }
    }

    createPicker(accessToken) {
        if (!accessToken) {
            this.showError("No access token available");
            return;
        }

        const view = new google.picker.View(google.picker.ViewId.DOCS);
        view.setMimeTypes("application/pdf,image/png,image/jpeg,image/jpg");

        const picker = new google.picker.PickerBuilder()
            .enableFeature(google.picker.Feature.NAV_HIDDEN)
            .enableFeature(google.picker.Feature.MULTISELECT_ENABLED)
            .setAppId(this.config.app_id)
            .setOAuthToken(accessToken)
            .addView(view)
            .addView(new google.picker.DocsUploadView())
            .setDeveloperKey(this.config.api_key)
            .setCallback(this.pickerCallback.bind(this))
            .build();

        picker.setVisible(true);
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
