odoo.define('report_excel.DomainSelectorParam', function(require){
	"use strict";

var core = require("web.core");
var datepicker = require("web.datepicker");
var Domain = require("report_excel.DomainParam");
var field_utils = require ("web.field_utils");
var ModelFieldSelector = require("web.ModelFieldSelector");
var Widget = require("web.Widget");
var _t = core._t;
var _lt = core._lt;
var operator_mapping = {
    "=": "=",
    "!=": _lt("is not ="),
    ">": ">",
    "<": "<",
    ">=": ">=",
    "<=": "<=",
    "ilike": _lt("contains"),
    "not ilike": _lt("does not contain"),
    "in": _lt("in"),
    "not in": _lt("not in"),
    "child_of": _lt("child of"),
    "parent_of": _lt("parent of"),
    "like": "like",
    "not like": "not like",
    "=like": "=like",
    "=ilike": "=ilike",
    "set": _lt("is set"),
    "not set": _lt("is not set"),
};
/**
 * Abstraction for widgets which can represent and allow edition of a domain.
 */
var DomainNode = Widget.extend({
    events: {
        "click .o_domain_add_node_button": "_onAddButtonClick",
        "click .o_domain_delete_node_button": "_onDeleteButtonClick",
        "mouseenter button": "_onButtonEntered",
        "mouseleave button": "_onButtonLeft",
    },
    /**
     * A DomainNode needs a model and domain to work. It can also receive a set
     * of options.
     *
     * @param {Object} parent
     * @param {string} model - the model name
     * @param {Array|string} domain - the prefix representation of the domain
     * @param {Object} [options] - an object with possible values:
     * @param {boolean} [options.readonly=true] - true if is readonly
     * @param {Array} [options.default] - default domain used when creating a
     *   new node
     * @param {string[]} [options.operators=null]
     *        a list of available operators (null = all of supported ones)
     * @param {boolean} [options.debugMode=false] - true if should be in debug
     *
     * @see ModelFieldSelector for other options
     */
    init: function (parent, model, domain, options, params) {
        this._super.apply(this, arguments);
        this.model = model;
        this.params = params;        
        this.options = _.extend({
            readonly: true,
            operators: null,
            debugMode: false,
        }, options || {});
        this.readonly = this.options.readonly;
        this.debug = this.options.debugMode;
    },
    /**
     * Should return if the node is representing a well-formed domain, whose
     * field chains properly belong to the associated model.
     *
     * @abstract
     * @returns {boolean}
     */
    isValid: function () {},
    /**
     * Should return the prefix domain the widget is currently representing
     * (an array).
     *
     * @abstract
     * @returns {Array}
     */
    getDomain: function () {},
    /**
     * Called when the add button is clicked -> trigger_up an event to ask
     * creation of a new child in its parent.
     *
     * @param {Event} e
     */
    _onAddButtonClick: function (e) {
        e.preventDefault();
        e.stopPropagation();
        this.trigger_up("add_node_clicked", {newBranch: !!$(e.currentTarget).data("branch"), child: this});
    },
    /**
     * Called when the delete button is clicked -> trigger_up an event to ask
     * deletion of this node from its parent.
     *
     * @param {Event} e
     */
    _onDeleteButtonClick: function (e) {
        e.preventDefault();
        e.stopPropagation();
        this.trigger_up("delete_node_clicked", {child: this});
    },
    /**
     * Called when a "controlpanel" button is hovered -> add classes to the
     * domain node to add animation effects.
     *
     * @param {Event} e
     */
    _onButtonEntered: function (e) {
        e.preventDefault();
        e.stopPropagation();
        var $target = $(e.currentTarget);
        this.$el.toggleClass("o_hover_btns", $target.hasClass("o_domain_delete_node_button"));
        this.$el.toggleClass("o_hover_add_node", $target.hasClass("o_domain_add_node_button"));
        this.$el.toggleClass("o_hover_add_inset_node", !!$target.data("branch"));
    },
    /**
     * Called when a "controlpanel" button is not hovered anymore -> remove
     * classes from the domain node to stop animation effects.
     *
     * @param {Event} e
     */
    _onButtonLeft: function (e) {
        e.preventDefault();
        e.stopPropagation();
        this.$el.removeClass("o_hover_btns o_hover_add_node o_hover_add_inset_node");
    },
});
/**
 * DomainNode which can handle subdomains (a domain which is composed of
 * multiple parts). It thus will be composed of other DomainTree instances
 * and/or leaf parts of a domain (@see DomainLeaf).
 */
var DomainTree = DomainNode.extend({
    template: "DomainTree",
    events: _.extend({}, DomainNode.prototype.events, {
        "click .o_domain_tree_operator_selector .dropdown-item": "_onOperatorChange",
    }),
    custom_events: {
        "add_node_clicked": "_onNodeAdditionAsk",
        "delete_node_clicked": "_onNodeDeletionAsk",
    },
    /**
     * @constructor
     * @see DomainNode.init
     * The initialization of a DomainTree creates a "children" array attribute
     * which will contain the the DomainNode children. It also deduces the
     * operator from the domain.
     * @see DomainTree._addFlattenedChildren
     */
    init: function (parent, model, domain, options, params) {
        this._super.apply(this, arguments);
        var parsedDomain = this._parseDomain(domain);
        if (parsedDomain) {
            this._initialize(parsedDomain);
        }
    },
    /**
     * @see DomainNode.start
     * @returns {Deferred}
     */
    start: function () {
        this._postRender();
        return $.when(this._super.apply(this, arguments), this._renderChildrenTo(this.$childrenContainer));
    },
    /**
     * @see DomainNode.isValid
     * @returns {boolean}
     */
    isValid: function () {
        for (var i = 0 ; i < this.children.length ; i++) {
            var cValid = this.children[i].isValid();
            if (!cValid) {
                return cValid;
            }
        }
        return this._isValid;
    },
    /**
     * @see DomainNode.getDomain
     * @returns {Array}
     */
    getDomain: function () {
        var childDomains = [];
        var nbChildren = 0;
        _.each(this.children, function (child) {
            var childDomain = child.getDomain();
            if (childDomain.length) {
                nbChildren++;
                childDomains = childDomains.concat(child.getDomain());
            }
        });
        var nbChildRequired = this.operator === "!" ? 1 : 2;
        var operators = _.times(nbChildren - nbChildRequired + 1, _.constant(this.operator));
        return operators.concat(childDomains);
    },
    /**
     * Adds a domain part to the widget.
     * -> trigger_up "domain_changed" if the child is added
     *
     * @private
     * @param {Array} domain - the prefix-like domain to build and add to the
     *                       widget
     * @param {DomainNode} afterNode - the node after which the new domain part
     *                               must be added (at the end if not given)
     * @returns {boolean} true if the part was added
     *                   false otherwise (the afterNode was not found)
     */
    _addChild: function (domain, afterNode) {
        var i = afterNode ? _.indexOf(this.children, afterNode) : this.children.length;
        if (i < 0) return false;
        this.children.splice(i+1, 0, instantiateNode(this, this.model, domain, this.options));
        this.trigger_up("domain_changed", {child: this});
        return true;
    },
    /**
     * Adds a child which represents the given domain. If the child has children
     * and that the child main domain operator is the same as the current widget
     * one, the 2-children prefix hierarchy is then simplified by making the
     * child's children the widget's own children.
     *
     * @private
     * @param {Array|string} domain - the domain of the child to add
     */
    _addFlattenedChildren: function (domain) {
        var node = instantiateNode(this, this.model, domain, this.options, this.params);
        if (node === null) {
            return;
        }
        if (!node.children || node.operator !== this.operator) {
            this.children.push(node);
            return;
        }
        _.each(node.children, (function (child) {
            child.setParent(this);
            this.children.push(child);
        }).bind(this));
        node.destroy();
    },
    /**
     * Changes the operator of the domain tree and notifies the parent if
     * necessary (not silent).
     *
     * @private
     * @param {string} operator - the new operator
     * @param {boolean} silent - true if the parents should not be notified of
     *                         the change
     */
    _changeOperator: function (operator, silent) {
        this.operator = operator;
        if (!silent) this.trigger_up("domain_changed", {child: this});
    },
    /**
     * @see DomainTree.init
     * @private
     */
    _initialize: function (domain) {
        this._isValid = true;
        this.operator = domain[0];
        this.children = [];
        if (domain.length <= 1) {
            return;
        }
        var nbLeafsToFind = 1;
        for (var i = 1 ; i < domain.length ; i++) {
            if (domain[i] === "&" || domain[i] === "|") {
                nbLeafsToFind++;
            } else if (domain[i] !== "!") {
                nbLeafsToFind--;
            }
            if (!nbLeafsToFind) {
                var partLeft = domain.slice(1, i+1);
                var partRight = domain.slice(i+1);
                if (partLeft.length) {
                    this._addFlattenedChildren(partLeft);
                }
                if (partRight.length) {
                    this._addFlattenedChildren(partRight);
                }
                break;
            }
        }
        this._isValid = (nbLeafsToFind === 0);
        if (this.operator === "!") {
            this.children[0].noControlPanel = true;
        }
    },
    /**
     * @see DomainTree.start
     * Initializes variables which depend on the rendered widget.
     * @private
     */
    _postRender: function () {
        this.$childrenContainer = this.$("> .o_domain_node_children_container");
    },
    /**
     * Removes a given child from the widget.
     * -> trigger_up domain_changed if the child is removed
     *
     * @private
     * @param {DomainNode} oldChild - the child instance to remove
     * @returns {boolean} true if the child was removed, false otherwise (the
     *                   widget does not own the child)
     */
    _removeChild: function (oldChild) {
        var i = _.indexOf(this.children, oldChild);
        if (i < 0) return false;
        this.children[i].destroy();
        this.children.splice(i, 1);
        this.trigger_up("domain_changed", {child: this});
        return true;
    },
    /**
     * @see DomainTree.start
     * Appends the children domain node to the given node. This is used to
     * render the children widget in a dummy element before adding them in the
     * DOM, otherwhise they could be misordered as they rendering is not
     * synchronous.
     *
     * @private
     * @param {jQuery} $to - the jQuery node to which the children must be added
     * @returns {Deferred}
     */
    _renderChildrenTo: function ($to) {
        var $div = $("<div/>");
        return $.when.apply($, _.map(this.children, (function (child) {
            return child.appendTo($div);
        }).bind(this))).then((function () {
            _.each(this.children, function (child) {
                child.$el.appendTo($to); 
            });
        }).bind(this));
    },
    /**
     * @param {string} domain
     * @returns {Array[]}
     */
    _parseDomain: function (domain) {
        var parsedDomain = false;
        try {
            parsedDomain = Domain.prototype.stringToArray(domain);
            this.invalidDomain = false;
        } catch (err) {
            this.invalidDomain = true;
            this.children = [];
        }
        return parsedDomain;
    },
    /**
     * Called when the operator select value is changed -> change the internal
     * operator state
     *
     * @param {Event} e
     */
    _onOperatorChange: function (e) {
        e.preventDefault();
        e.stopPropagation();
        this._changeOperator($(e.target).data("operator"));
    },
    /**
     * Called when a node addition was asked -> add the new domain part if on
     * the right node or let the propagation continue.
     *
     * @param {OdooEvent} e
     */
    _onNodeAdditionAsk: function (e) {
        var domain = this.options.default || [["id", "=", 1]];
        if (e.data.newBranch) {
            domain = [this.operator === "&" ? "|" : "&"].concat(domain).concat(domain);
        }
        if (this._addChild(domain, e.data.child)) {
            e.stopPropagation();
        }
    },
    /**
     * Called when a node deletion was asked -> remove the domain part if on
     * the right node or let the propagation continue.
     *
     * @param {OdooEvent} e
     */
    _onNodeDeletionAsk: function (e) {
        if (this._removeChild(e.data.child)) {
            e.stopPropagation();
        }
    },
});
/**
 * The DomainSelector widget can be used to build prefix char domain. It is the
 * DomainTree specialization to use to have a fully working widget.
 *
 * Known limitations:
 *
 * - Some operators like "child_of", "parent_of", "like", "not like",
 *   "=like", "=ilike" will come only if you use them from demo data or
 *   debug input.
 * - Some kind of domain can not be build right now
 *   e.g ("country_id", "in", [1,2,3]) but you can insert from debug input.
 */
var DomainSelector = DomainTree.extend({
    template: "DomainSelector",
    events: _.extend({}, DomainTree.prototype.events, {
        "click .o_domain_add_first_node_button": "_onAddFirstButtonClick",
        "change .o_domain_debug_input": "_onDebugInputChange",
    }),
    custom_events: _.extend({}, DomainTree.prototype.custom_events, {
        domain_changed: "_onDomainChange",
    }),
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            if (self.invalidDomain) {
                var msg = _t("This domain is not supported.");
                self.$el.html(msg);
            }
        });
    },
    /**
     * Changes the internal domain value and forces a reparsing and rerendering.
     * If the internal domain value was already equal to the given one, this
     * does nothing.
     *
     * @param {string} domain
     * @returns {Deferred} resolved when the rerendering is finished
     */
    setDomain: function (domain) {
        if (domain === Domain.prototype.arrayToString(this.getDomain())) {
            return $.when();
        }
        var parsedDomain = this._parseDomain(domain);
        if (parsedDomain) {
            return this._redraw(parsedDomain);
        }
    },
    /**
     * @see DomainTree._initialize
     */
    _initialize: function (domain) {
        if (domain.length > 1) {
            Domain.prototype.normalizeArray(domain);
        } else {
            domain = ["&"].concat(domain);
        }
        return this._super(domain);
    },
    /**
     * @see DomainTree._postRender
     * Warns the user if the domain is not valid after rendering.
     */
    _postRender: function () {
        this._super.apply(this, arguments);
        this.$debugInput = this.$(".o_domain_debug_input");
        if (this.$debugInput.length) {
            this.$debugInput.val(Domain.prototype.arrayToString(this.getDomain()));
        }
        if (!this._isValid) {
            this.do_warn(
                _t("Domain error"),
                _t("The domain you entered is not properly formed")
            );
        }
    },
    /**
     * This method is ugly but achieves the right behavior without flickering.
     *
     * @param {Array|string} domain
     * @returns {Deferred}
     */
    _redraw: function (domain) {
        var oldChildren = this.children.slice();
        this._initialize(domain || this.getDomain());
        return this._renderChildrenTo($("<div/>")).then((function () {
            _.each(oldChildren, function (child) { child.destroy(); });
            this.renderElement();
            this._postRender();
            _.each(this.children, (function (child) { child.$el.appendTo(this.$childrenContainer); }).bind(this));
        }).bind(this));
    },
    /**
     * Called when the "add a filter" button is clicked -> adds a first domain
     * node
     */
    _onAddFirstButtonClick: function () {
        this._addChild(this.options.default || [["id", "=", 1]]);
    },
    /**
     * Called when the debug input value is changed -> constructs the tree
     * representation if valid or warn the user if invalid.
     *
     * @param {Event} e
     */
    _onDebugInputChange: function (e) {
        var domain;
        try {
            domain = Domain.prototype.stringToArray($(e.currentTarget).val());
        } catch (err) { 
            this.do_warn(_t("Syntax error"), _t("The domain you entered is not properly formed"));
            return;
        }
        this._redraw(domain).then((function () {
            this.trigger_up("domain_changed", {child: this, alreadyRedrawn: true});
        }).bind(this));
    },
    /**
     * Called when a (child's) domain has changed -> redraw the entire tree
     * representation if necessary
     *
     * @param {OdooEvent} e
     */
    _onDomainChange: function (e) {
        if (!e.data.alreadyRedrawn) {
            this._redraw();
        }
    },
});
/**
 * DomainNode which handles a domain which cannot be split in another
 * subdomains, i.e. composed of a field chain, an operator and a value.
 */
var DomainLeaf = DomainNode.extend({
    template: "DomainLeafParam",
    events: _.extend({}, DomainNode.prototype.events, {
        "change .o_domain_leaf_operator_select": "_onOperatorSelectChange",
        "change .o_domain_leaf_value_input": "_onValueInputChange",
        "click .o_domain_leaf_value_add_tag_button": "on_add_tag",
        "keyup .o_domain_leaf_value_tags input": "on_add_tag",
        "click .o_domain_leaf_value_remove_tag_button": "on_remove_tag",
        "change .o_domain_leaf_operator_select_param": function (e) {
        	this.onOperatorParamChange($(e.currentTarget).val());
        },
    }),
    custom_events: {
        "field_chain_changed": "_onFieldChainChange",
    },
    /**
     * @see DomainNode.init
     */
	init: function (parent, model, domain, options, params) {
        this._super.apply(this, arguments);
        var currentDomain = Domain.prototype.stringToArray(domain);
        this.chain = currentDomain[0][0];
        this.operator = currentDomain[0][1];
        this.value = currentDomain[0][2];
        this.params = params;        
        this.operator_mapping = operator_mapping;
    },
    /**
     * Prepares the information the rendering of the widget will need by
     * pre-instantiating its internal field selector widget.
     *
     * @returns {Deferred}
     */
    willStart: function () {
        var defs = [this._super.apply(this, arguments)];
        this.fieldSelector = new ModelFieldSelector(
            this,
            this.model,
            this.chain ? this.chain.split(".") : [],
            this.options
        );
        defs.push(this.fieldSelector.appendTo($("<div/>")).then((function () {
            var wDefs = [];
        if (!this.readonly) {
            var selectedField = this.fieldSelector.getSelectedField() || {};
	        var value_split = ("" + this.value).split(/\(([^)]+)\)/);
	        var param = value_split[0] === 'param' ? true : false;
	        var params_arr = new Array();
	        var params_arr_all = new Array();
	        var params_all =  ("" + this.params).split(';');
	        var i_split = ''
	    	var n = 0
	    	for (var i = 1 ; i < params_all.length ; i++) {
	    		i_split = ("" + params_all[i-1]).split(',');
	        	params_arr_all[i-1] = i_split
	        	var type_param_char = ['char', 'text', 'html', 'selection', 'reference']
	        	var type_param_integer = ['integer']
	        	var type_param_float = ['float', 'monetary']
	        	var type_param_m2x = ['many2one','one2many', 'many2many']
	        	var type_param_date = ['date']
	        	var type_param_datetime = ['datetime']
	        	var type_param_boolean = ['boolean']
	        	if ((_.contains(type_param_char, i_split[2])) && (_.contains(type_param_char, selectedField.type))) {
	        		params_arr[n] = [i_split[0],i_split[1]];
	        		n++;
	        	} else if ((_.contains(type_param_integer, i_split[2])) && (_.contains(type_param_integer, selectedField.type))) {
	        		params_arr[n] = [i_split[0],i_split[1]];
	        		n++;
	        	} else if ((_.contains(type_param_float, i_split[2])) && (_.contains(type_param_float, selectedField.type))) {
	        		params_arr[n] = [i_split[0],i_split[1]];
	        		n++;
	        	} else if ((_.contains(type_param_m2x, i_split[2])) && (_.contains(type_param_m2x, selectedField.type))) {
	        		if (_.contains([selectedField.relation], i_split[3])){
	            		params_arr[n] = [i_split[0],i_split[1]];
	            		n++;
	        		}
	        	} else if ((_.contains(type_param_date, i_split[2])) && (_.contains(type_param_date, selectedField.type))) {
	        		params_arr[n] = [i_split[0],i_split[1]];
	        		n++;
	        	} else if ((_.contains(type_param_datetime, i_split[2])) && (_.contains(type_param_datetime, selectedField.type))) {
	        		params_arr[n] = [i_split[0],i_split[1]];
	        		n++;
	        	} else if ((_.contains(type_param_boolean, i_split[2])) && (_.contains(type_param_boolean, selectedField.type))) {
	        		params_arr[n] = [i_split[0],i_split[1]];
	        		n++;
	        	}
	        }	                
                this.operators = this._getOperatorsFromType(selectedField.type);
                if (_.contains(["child_of", "parent_of", "like", "not like", "=like", "=ilike"], this.operator)) {
                    this.operators[this.operator] = operator_mapping[this.operator];
                } else if (!this.operators[this.operator]) {
                    this.operators[this.operator] = "?";
                }
                if (param === false){
	                this.selectionChoices = null;
	                if (selectedField.type === "boolean") {
	                    this.selectionChoices = [["1", _t("set (true)")], ["0", _t("not set (false)")]];
	                } else if (selectedField.type === "selection") {
	                    this.selectionChoices = selectedField.selection;
	                }
	                this.displayValue = this.value;
	                try {
	                    if (selectedField && !selectedField.relation && !_.isArray(this.value)) {
	                        this.displayValue = field_utils.format[selectedField.type](this.value, selectedField);
	                    }
	                } catch (err) {/**/}
	                this.displayOperator = this.operator;
	                if (selectedField.type === "boolean") {
	                    this.displayValue = this.value ? "1" : "0";
	                } else if ((this.operator === "!=" || this.operator === "=") && this.value === false) {
	                    this.displayOperator = this.operator === "!=" ? "set" : "not set";
	                }
	                if (_.contains(["date", "datetime"], selectedField.type)) {
	                    this.valueWidget = new (selectedField.type === "datetime" ? datepicker.DateTimeWidget : datepicker.DateWidget)(this);
	                    wDefs.push(this.valueWidget.appendTo("<div/>").then((function () {
	                        this.valueWidget.$el.addClass("o_domain_leaf_value_input");
	                        this.valueWidget.setValue(moment(this.value));
	                        this.valueWidget.on("datetime_changed", this, function () {
	                            this._changeValue(this.valueWidget.getValue());
	                        });
	                    }).bind(this)));
	                }
                } else{
                	this.displayOperator = this.operator;
                	this.operator_param = value_split[0];
                	var check_value = false
                	for (var i = 0 ; i < params_arr.length ; i++) {
                		if (_.contains(params_arr[i], this.value)) {
	                		check_value = true;
	        	    	}
                	}
                	this._isValidParam = true;
                	if (check_value === false){
                		params_arr[params_arr.length] = [this.value,'?']
                		this._validate_param(check_value)
                		this._isValidParam = false;                		
                	}
                	this.selectionChoices = params_arr;
                	this.displayValue = this.value;
                }
                return $.when.apply($, wDefs);
            }
        }).bind(this)));
        return $.when.apply($, defs);
    },
    /**
     * Toggles the valid status of the widget and display the error message if
     * it is not valid.
     *
     * @private
     * @param {boolean} valid - true if the widget is valid, false otherwise
     */
	_validate_param: function (valid) {
        this.valid = !!valid;
        if (!this.valid) {
            this.do_warn(
                _t("Invalid field Param"),
                _t("The field param is not valid. Did you maybe use a non-existing Param name?")
            );
        }
    },
    /**
     * @see DomainNode.start
     * Appends the prepared field selector and value widget.
     *
     * @returns {Deferred}
     */
    start: function () {
        this.fieldSelector.$el.prependTo(this.$("> .o_domain_leaf_info, > .o_domain_leaf_edition")); 
        if (!this.readonly && this.valueWidget) { 
            this.$(".o_domain_leaf_value_input").replaceWith(this.valueWidget.$el);
        }
        return this._super.apply(this, arguments);
    },
    /**
     * @see DomainNode.isValid
     * @returns {boolean}
     */
    isValid: function () {
        return this.fieldSelector && this.fieldSelector.isValid();
    },
    /**
     * @see DomainNode.getDomain
     * @returns {Array}
     */
    getDomain: function () {
        return [[this.chain, this.operator, this.value]];
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
		this.value = false
        this.chain = chain.join(".");
        this.fieldSelector.setChain(chain).then((function () {
            if (!this.fieldSelector.isValid()) return;
            var selectedField = this.fieldSelector.getSelectedField() || {};
            var operators = this._getOperatorsFromType(selectedField.type);
            if (operators[this.operator] === undefined) {
                this._changeOperator("=", true);
            }
            this._changeValue(this.value, true);
            if (!silent) this.trigger_up("domain_changed", {child: this});
        }).bind(this));
    },
    /**
     * Handles an operator change in the domain. In that case, the value should
     * be adapted to a valid one for the new operator.
     *
     * -> trigger_up domain_changed event to ask for a re-rendering
     * (if not silent)
     *
     * @param {string} operator - the new operator
     * @param {boolean} silent - true if the method call should not trigger_up a
     *                         domain_changed event
     */
    _changeOperator: function (operator, silent) {
        this.operator = operator;
        if (_.contains(["set", "not set"], this.operator)) {
            this.operator = this.operator === "not set" ? "=" : "!=";
            this.value = false;
        } else if (_.contains(["in", "not in"], this.operator)) {
            this.value = _.isArray(this.value) ? this.value : this.value ? ("" + this.value).split(",") : [];
        } else {
            if (_.isArray(this.value)) {
                this.value = this.value.join(",");
            }
            this._changeValue(this.value, true);
        }
        if (!silent) this.trigger_up("domain_changed", {child: this});
    },
 	    onOperatorParamChange: function (operator_param, silent) {
 	    	this.operator_param = operator_param;
 	    	if (_.contains(["param", "value"], this.operator_param)) {
 	    		this.operator_param = this.operator_param === "param" ? "param" : "value";
 	    		if (this.operator_param === 'param'){
 	               var selectedField = this.fieldSelector.getSelectedField() || {};
				   var value_split = ("" + this.value).split(/\(([^)]+)\)/);
				   var param = value_split[0] === 'param' ? true : false;
				   var params_arr = new Array();
				   var params_arr_all = new Array();
				   var params_all =  ("" + this.params).split(';');
				   var i_split = ''
					var n = 0
					for (var i = 1 ; i < params_all.length ; i++) {
						i_split = ("" + params_all[i-1]).split(',');
				   	params_arr_all[i-1] = i_split
				   	var type_param_char = ['char', 'text', 'html', 'selection', 'reference']
				   	var type_param_integer = ['integer']
				   	var type_param_float = ['float', 'monetary']
				   	var type_param_m2x = ['many2one','one2many', 'many2many']
				   	var type_param_date = ['date']
				   	var type_param_datetime = ['datetime']
				   	var type_param_boolean = ['boolean']
				   	if ((_.contains(type_param_char, i_split[2])) && (_.contains(type_param_char, selectedField.type))) {
				   		params_arr[n] = [i_split[0],i_split[1]];
				   		n++;
				   	} else if ((_.contains(type_param_integer, i_split[2])) && (_.contains(type_param_integer, selectedField.type))) {
				   		params_arr[n] = [i_split[0],i_split[1]];
				   		n++;
				   	} else if ((_.contains(type_param_float, i_split[2])) && (_.contains(type_param_float, selectedField.type))) {
				   		params_arr[n] = [i_split[0],i_split[1]];
				   		n++;
				   	} else if ((_.contains(type_param_m2x, i_split[2])) && (_.contains(type_param_m2x, selectedField.type))) {
				   		if (_.contains([selectedField.relation], i_split[3])){
				       		params_arr[n] = [i_split[0],i_split[1]];
				       		n++;
				   		}
				   	} else if ((_.contains(type_param_date, i_split[2])) && (_.contains(type_param_date, selectedField.type))) {
				   		params_arr[n] = [i_split[0],i_split[1]];
				   		n++;
				   	} else if ((_.contains(type_param_datetime, i_split[2])) && (_.contains(type_param_datetime, selectedField.type))) {
				   		params_arr[n] = [i_split[0],i_split[1]];
				   		n++;
				   	} else if ((_.contains(type_param_boolean, i_split[2])) && (_.contains(type_param_boolean, selectedField.type))) {
				   		params_arr[n] = [i_split[0],i_split[1]];
				   		n++;
				   	}
				   }	                
                 	this.selectionChoices = params_arr;	 
                 	if (params_arr.length > 0){
                 		this.value = params_arr[0][0];
                 	}
 	    		} else{
 	    			this.value = false;
 		    		this._onValueInputChange(this.value, true);
 	    		}
 	    	}
 	    	if (!silent) this.trigger_up("domain_changed", {child: this});
 	    },
    /**
     * Handles a formatted value change in the domain. In that case, the value
     * should be adapted to a valid technical one.
     *
     * -> trigger_up "domain_changed" event to ask for a re-rendering (if not
     * silent)
     *
     * @param {*} value - the new formatted value
     * @param {boolean} silent - true if the method call should not trigger_up a
     *                         domain_changed event
     */
    _changeValue: function (value, silent) {
        var couldNotParse = false;
      var re = /\(([^)]+)\)/;
      var param = (("" + value).split(re))[0] === 'param' ? true : false;
      if (param) {
      	this.value = value
      }
      else{
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
      }
        if (!silent) this.trigger_up("domain_changed", {child: this});
    },
    /**
     * Returns the mapping of "technical operator" to "display operator value"
     * of the operators which are available for the given field type.
     *
     * @private
     * @param {string} type - the field type
     * @returns {Object} a map of all associated operators and their label
     */
    _getOperatorsFromType: function (type) {
        var operators = {};
        switch (type) {
            case "boolean":
                operators = {
                    "=": _t("is"),
                    "!=": _t("is not"),
                };
                break;
            case "char":
            case "text":
            case "html":
                operators = _.pick(operator_mapping, "=", "!=", "ilike", "not ilike", "set", "not set", "in", "not in");
                break;
            case "many2many":
            case "one2many":
            case "many2one":
                operators = _.pick(operator_mapping, "=", "!=", "ilike", "not ilike", "set", "not set");
                break;
            case "integer":
            case "float":
            case "monetary":
                operators = _.pick(operator_mapping, "=", "!=", ">", "<", ">=", "<=", "ilike", "not ilike", "set", "not set");
                break;
            case "selection":
                operators = _.pick(operator_mapping, "=", "!=", "set", "not set");
                break;
            case "date":
            case "datetime":
                operators = _.pick(operator_mapping, "=", "!=", ">", "<", ">=", "<=", "set", "not set");
                break;
            default:
                operators = _.extend({}, operator_mapping);
                break;
        }
        if (this.options.operators) {
            operators = _.pick.apply(_, [operators].concat(this.options.operators));
        }
        return operators;
    },
    /**
     * Called when the operator select value is change -> change the operator
     * internal state and adapt
     *
     * @param {Event} e
     */
    _onOperatorSelectChange: function (e) {
        this._changeOperator($(e.currentTarget).val());
    },
    /**
     * Called when the value input value is changed -> change the internal value
     * state and adapt
     *
     * @param {Event} e
     */
    _onValueInputChange: function (e) {
        if (e.currentTarget !== e.target) return;
        this._changeValue($(e.currentTarget).val());
    },
    /**
     * Called when the field selector value is changed -> change the internal
     * chain state and adapt
     *
     * @param {OdooEvent} e
     */
    _onFieldChainChange: function (e) {
        this._changeFieldChain(e.data.chain);
    },
    on_add_tag: function (e) {
        if (e.type === "keyup" && e.which !== $.ui.keyCode.ENTER) return;
        if (!_.contains(["not in", "in"], this.operator)) return;
        var values = _.isArray(this.value) ? this.value.slice() : [];
        var $input = this.$(".o_domain_leaf_value_tags input");
        var val = $input.val().trim();
        if (val && values.indexOf(val) < 0) {
            values.push(val);
            _.defer(this._changeValue.bind(this, values));
            $input.focus();
        }
    },
    on_remove_tag: function (e) {
        var values = _.isArray(this.value) ? this.value.slice() : [];
        var val = this.$(e.currentTarget).data("value");
        var index = values.indexOf(val);
        if (index >= 0) {
            values.splice(index, 1);
            _.defer(this._changeValue.bind(this, values));
        }
    },
});
/**
 * Instantiates a DomainTree if the given domain contains several parts and a
 * DomainLeaf if it only contains one part. Returns null otherwise.
 *
 * @param {Object} parent
 * @param {string} model - the model name
 * @param {Array|string} domain - the prefix representation of the domain
 * @param {Object} options - @see DomainNode.init.options
 * @returns {DomainTree|DomainLeaf|null}
 */
function instantiateNode(parent, model, domain, options, params) {
    if (domain.length > 1) {
        return new DomainTree(parent, model, domain, options, params);
    } else if (domain.length === 1) {
        return new DomainLeaf(parent, model, domain, options, params);
    }
    return null;
}
return DomainSelector;
});
