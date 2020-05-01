odoo.define('report_excel.field', function(require){
"use strict";

var AbstractField = require('web.AbstractField');
var Registry = require('web.field_registry');
var ModelFieldSelector = require("report_excel.ModelFieldSelectorExt");
var field_utils = require ("web.field_utils");
var session = require('web.session');
var ReportField = AbstractField.extend({
    custom_events: {
    	"field_chain_changed": "_onFieldChainChange",
    },
    init: function () {
    	this._super.apply(this, arguments);
    	this.readonly = this.mode === 'readonly' ? true : false;
    	this.valid = true;
        this.options = _.defaults(this.options || {}, {
            in_dialog: false,
            model: undefined, 
            fs_filters: {}, 
        });
    },
    start: function() {
        this.model = _get_model.call(this); 
        if (!this.readonly){
	        this.fieldSelector = new ModelFieldSelector(
	        		this, 
	        		this.model, 
	        		this.value ? this.value.split(".") : [], 
	        		{
					readonly: this.get("readonly"),
					fs_filters: this.options.fs_filters,
					debugMode: session.debug,
					}
	        		);
	        this.fieldSelector.prependTo(this.$el);        
        }else{
        	this.displayValue = this.value;
        	var fields = this.value.split(".");        	
        	this.el.textContent = fields; 
        };
        function _get_model() {
            if (this.options.model) {
                return this.options.model;
            }
            if (this.recordData.root_model_name) {
            	return this.recordData.root_model_name;
            }
        }
    },
    initialize_content: function () {
        this._super.apply(this, arguments);
        this.$modelMissing = this.$(".o_domain_model_missing");
    },
    /**
     * Handles a field chain change in the domain. In that case, the operator
     * should be adapted to a valid one for the new field and the value should
     * also be adapted to the new field and/or operator.
     *
     * -> trigger_up domain_changed event to ask for a re-rendering (if not
     * silent)
     *
     * @param {string[]} chain - the new field chain
     * @param {boolean} silent - true if the method call should not trigger_up a
     *                         domain_changed event
     */
    _changeFieldChain: function (chain, silent) {
        this.chain = chain.join(".");
        this.fieldSelector.setChain(chain).then((function () {
            if (!this.fieldSelector.isValid() || !(this.fieldSelector.chain.length)) return;
            var selectedField = this.fieldSelector.getSelectedField() || {};
            this._changeValue(this.chain, true);
            this._setValue(this.chain, {forceChange: true});
        }).bind(this));
    },
    _onFieldChainChange: function (e) {
        this._changeFieldChain(e.data.chain);
    },
    _changeValue: function (value, silent) {
        var couldNotParse = false;
        var selectedField = this.fieldSelector.getSelectedField() || {};
        try {
            this.value = field_utils.parse[selectedField.type](value, selectedField);
        } catch (err) {
            this.value = value;
            couldNotParse = true;
        }
        if (selectedField.type === "boolean") {
            if (!_.isBoolean(this.value)) { 
                this.value = !!parseFloat(this.value);
            }
        } else if (selectedField.type === "selection") {
            if (!_.some(selectedField.selection, (function (option) { return option[0] === this.value; }).bind(this))) {
                this.value = selectedField.selection[0][0];
            }
        } else if (_.contains(["date", "datetime"], selectedField.type)) {
            if (couldNotParse || _.isBoolean(this.value)) {
                this.value = field_utils.parse[selectedField.type](field_utils.format[selectedField.type](moment())).toJSON(); 
            } else {
                this.value = this.value.toJSON(); 
            }
        } else {
            if (_.isBoolean(this.value)) {
                this.value = "";
            } else if (_.isObject(this.value) && !_.isArray(this.value)) { 
                this.value = this.value.id || value || "";
            }
        }
    },
    /**
     * @override isValid from AbstractField.isValid
     * Parsing the char value is not enough for this field. It is considered
     * valid if the internal domain selector was built correctly and that the
     * query to the model to test the domain did not fail.
     *
     * @returns {boolean}
     */
    isValid: function () {
    	return (!this.fieldSelector.isValid() || !(this.fieldSelector.chain.length)) ? false : true ;
    },    
});
Registry.add('report_field', ReportField);
});
