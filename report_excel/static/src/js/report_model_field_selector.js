odoo.define("report_excel.ModelFieldSelectorExt", function (require) {
"use strict";

var ModelFieldSelector = require("web.ModelFieldSelector");	
var ModelFieldSelectorExt = ModelFieldSelector.extend({
	init: function (parent, model, chain, options) {
        this._super.apply(this, arguments);
		delete this.options.filters["searchable"];
    },
});
return ModelFieldSelectorExt;
});
