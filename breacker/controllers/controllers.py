# -*- coding: utf-8 -*-
from odoo import http

# class BreakMenu(http.Controller):
#     @http.route('/break_menu/break_menu/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/break_menu/break_menu/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('break_menu.listing', {
#             'root': '/break_menu/break_menu',
#             'objects': http.request.env['break_menu.break_menu'].search([]),
#         })

#     @http.route('/break_menu/break_menu/objects/<model("break_menu.break_menu"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('break_menu.object', {
#             'object': obj
#         })