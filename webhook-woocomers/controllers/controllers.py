# -*- coding: utf-8 -*-
from flectra import http
from flectra.http import request
import requests
import json

class WebhookWoocomers(http.Controller):
    #url
    url     =   ""

    def getToken(self, username, password, db, host):
        db_config = {
            "username": username,
            "password": password,
            "db": db
        }

        self.url    =   host

        server_url = self.url
        get_token_url = "/api/auth/get_tokens"
        url  = server_url + get_token_url
        res  = requests.post(url=url, data=db_config)
        data = res.json()
        
        return data

    def post_log(self, user, product = None, customer = None, order = None, type = 'create'):
        vals = {
            'user_id': user,
            'create_uid': user,
            'write_uid': user,
        }

        if product != None:
            vals['product_id']         =   product
            vals['description']     =   "{} {}".format(type, 'product')
        elif customer != None:
            vals['partner_id']        =   customer
            vals['description']     =   "{} {}".format(type, 'customer')
        elif order != None:
            vals['order_id']            =   order
            vals['description']         =   "{} {}".format(type, 'order')

        return request.env["webhook.log"].sudo().create(vals)

    def country(self, country_id):
        if country_id != "":
            country_id  =   request.env["res.country"].sudo().search([('code', '=', country_id)])

            if len(country_id) > 0:
                country_id  =   country_id[0].id
            else:
                country_id  =   ""

            return country_id
        
        else:
            return ''

    def state(self, state, country_id):
        if state != "" and country_id != "":
            state_id    =   request.env["res.country.state"].sudo().search([('code', '!=', state)])

            if len(state_id) > 0:
                state_id       =   state_id[0].id
            else:
                state_id       =   ""
        
            return state_id

        else:
            return ''

    @http.route('/webhook/api/customer/<company>', methods=['GET', 'POST'], type='json', auth='none', csrf=False)
    def webhook(self, company):
        company     =   request.env["res.company"].sudo().search([('name', '=', company)])[0]
        token       =   self.getToken(company.email_login, company.password_login, company.database, company.host)
        res         =   request.jsonrequest

        state       =   res["billing"]["state"]
        state_id    =   ""
        country_id  =   res["billing"]["country"]
        user        =   request.env["res.partner"].sudo().search([("ref", "=", res["username"])])

        if country_id != "":
            country_id  =   request.env["res.country"].sudo().search([('code', '=', country_id)])

            if len(country_id) > 0:
                country_id  =   country_id[0].id
            else:
                country_id  =   ""

        if state != "" and country_id != "":
            state_id    =   request.env["res.country.state"].sudo().search([('code', '!=', state)])

            if len(state_id) > 0:
                state_id       =   state_id[0].id
            else:
                state_id       =   ""

        data    =   {
            'name':     "{} {}".format(res["first_name"], res["last_name"]),
            'company_id':    token["company_id"],
            "ref": res["username"],
            'street':    res["billing"]["address_1"],
            'street2':    res["billing"]["address_2"],
            'zip':    res["billing"]["postcode"],
            'city':    res["billing"]["city"],
            'state_id':    state_id,
            'country_id':    country_id,
            'email':    res["email"],
            'phone':    res["billing"]["phone"],
            'commercial_company_name':    res["billing"]["company"],
            'create_uid':    token["uid"],
            'write_uid':    token["uid"],
        }

        header = {
            "access_token": token['access_token']
        }

        server_url = self.url
        post_url = '/api/res.partner'
        url = server_url + post_url

        if len(user) > 0:
            data['id']  =   user[0].id

            customer    =   requests.put(url=url, data=data, headers=header)
            self.post_log(token['uid'], None, user[0].id, None, "update")

            return 'success'
        else: 
            customer    =   request.env['res.partner'].sudo().create(data)
            customer    =   customer[0]

            self.post_log(token['uid'], None, customer["id"], None, "create")

            return 'success'

    @http.route('/webhook/api/order/<company>', methods=['GET', 'POST'], type='json', auth='none', csrf=False)
    def order(self, company):
        company     =   request.env["res.company"].sudo().search([('name', '=', company)])[0]
        token       =   self.getToken(company.email_login, company.password_login, company.database, company.host)

        res         =   request.jsonrequest

        partner        =   request.env['res.partner'].sudo().search([('email', '=', res["billing"]["email"])])

        country_id  =   self.country(res["billing"]["country"])
        state_id    =   self.state(res["billing"]["state"], country_id)

        header = {
            "access_token": token['access_token']
        }

        data    =   {
            'name':     "{} {}".format(res["billing"]["first_name"], res["billing"]["last_name"]),
            'company_id':    token["company_id"],
            'street':    res["billing"]["address_1"],
            'street2':    res["billing"]["address_2"],
            'zip':    res["billing"]["postcode"],
            'city':    res["billing"]["city"],
            'email':    res["billing"]["email"],
            'state_id':    state_id,
            'country_id':    country_id,
            'phone':    res["billing"]["phone"],
            'commercial_company_name':    res["billing"]["company"],
            'create_uid':    token["uid"],
            'write_uid':    token["uid"],
        }

        server_url  = self.url
        post_url    = '/api/res.partner'
        url         = server_url + post_url

        if len(partner) > 0:
            data['id']  =   partner[0].id
            partner        =   partner[0]

            customer    =   requests.put(url=url, data=data, headers=header)

            self.post_log(token['uid'], None, partner[0].id, None, "update")
        else: 
            customer        =   request.env['res.partner'].sudo().create(data)
            customer        =   customer[0]
            partner         =   customer

            self.post_log(token['uid'], None, customer["id"], None, "create")
        
        user_id     =   request.env["res.users"].sudo().search([('id', '=', company.user_id[0].id)])[0]

        branch      =   request.env["res.branch"].sudo().search([('id', '=', company.branch_id[0].id)])[0]

        company     =   request.env["res.company"].sudo().search([('name', '=', company.name)])[0]

        team        =   request.env["crm.team"].sudo().search([('id', '=', company.team_id[0].id)])[0]

        data_order  =   {
            'name': res["id"],
            'origin': res["order_key"],
            'state': 'draft',
            'date_order': res["date_created"],
            'partner_id': partner.id,
            'user_id': user_id.id,
            'analytic_account_id': branch.id,
            'company_id': company.id,
            'branch_id': branch.id,
            'create_uid': user_id.id,
            'team_id': team.id
        }

        order = request.env["sale.order"].sudo().create(data_order)
        self.post_log(token['uid'], None, None, order[0].id, "create")

        for product in res["line_items"]:
            pro     =   request.env["product.template"].sudo().search([('name', '=', product["name"])])[0]

            pro_id  =   request.env["product.product"].sudo().search([('product_tmpl_id', '=', pro.id)])[0]

            route   =   request.env["stock.location.route"].sudo().search([('name', '=', 'Drop Shipping')])[0]

            data_product    =   {
                'name': product["name"],
                'order_id': order[0].id, 
                'invoice_status': 'no',
                'price_unit': product["price"],
                'price_subtotal': product["subtotal"],
                'price_tax': product["subtotal_tax"],
                'price_total': product["total"],
                'product_uom_qty':product["quantity"],
                'product_id': pro_id.id,
                'product_uom': pro.uom_id[0].id,
                'company_id': company.id,
                'branch_id': branch.id,
                'state': 'draft',
                'route_id': route.id
            }

            request.env["sale.order.line"].sudo().create(data_product)