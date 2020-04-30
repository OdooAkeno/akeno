odoo.define('report_excel.FormViewDialogModal', function(require) {
	"use strict";

var FormViewDialog = require('web.view_dialogs').FormViewDialog;
FormViewDialog.include({
	init: function(parent, options) {
		if (options.res_model == "report.excel.section") {
			options.disable_multiple_selection =  true;			
		};
		this._super(parent, options);
		if (options.res_model == "report.excel.fields") {
			this.dialogClass += ' modal-body_report_excel';
		};
	},
});
});
