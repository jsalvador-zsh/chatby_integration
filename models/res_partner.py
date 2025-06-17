from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    user_ns = fields.Char(string='Chatby User NS', readonly=True, index=True)
    user_id = fields.Char(string='Chatby User ID', readonly=True)
    agent_id = fields.Integer(string='Chatby Agent ID', readonly=True)
    channel = fields.Selection([
        ('instagram', 'Instagram'),
        ('facebook', 'Facebook'),
        ('whatsapp', 'WhatsApp'),
        ('web', 'Web'),
        ('telegram', 'Telegram'),
        ('other', 'Other')
    ], string='Channel', readonly=True)
    chatby_subscriber_id = fields.Many2one(
        'chatby.subscriber',
        string='ChatBy Subscriber',
        readonly=True
    )