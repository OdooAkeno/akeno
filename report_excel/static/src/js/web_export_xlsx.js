odoo.define('report_excel.web_export_xlsx', function(require) {
	"use strict";

var FormController = require('web.FormController');
FormController.include({
	_onButtonClicked : function(event) {
			var self = this;
			this._super.apply(this, arguments);
			if (event.data.attrs.name == "export_excel") {
				setTimeout(this._enableButtons.bind(this), 4000);
			}
		},
	});
});
