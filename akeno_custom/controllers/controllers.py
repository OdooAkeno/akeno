# -*- coding: utf-8 -*-
from odoo import http

# class AkenoCustom(http.Controller):
#     @http.route('/akeno_custom/akeno_custom/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/akeno_custom/akeno_custom/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('akeno_custom.listing', {
#             'root': '/akeno_custom/akeno_custom',
#             'objects': http.request.env['akeno_custom.akeno_custom'].search([]),
#         })

#     @http.route('/akeno_custom/akeno_custom/objects/<model("akeno_custom.akeno_custom"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('akeno_custom.object', {
#             'object': obj
#         })