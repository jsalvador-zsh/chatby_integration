from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = 'crm.lead'
    
    subscriber_id = fields.Many2one(
        'chatby.subscriber',
        string='ChatBy Subscriber',
        ondelete='set null'
    )