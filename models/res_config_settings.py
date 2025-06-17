from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    chatby_token = fields.Char(string='ChatBy API Token', config_parameter='chatby_integration.token')
    chatby_api_url = fields.Char(string='ChatBy API URL', default='https://app.chatby.io/api', config_parameter='chatby_integration.api_url')

    def test_chatby_connection(self):
        self.ensure_one()
        try:
            result = self.env['chatby.api'].test_connection()
            message = result.get('message', 'Conexión exitosa')
            
            # Mostrar información
            details = ""
            if result.get('data'):
                user_info = result['data']
                details = f"Usuario: {user_info.get('name', 'N/A')}<br/>Email: {user_info.get('email', 'N/A')}"
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Conexión exitosa',
                    'message': f'{message}<br/>{details}',
                    'sticky': False,
                    'type': 'success',
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error de conexión',
                    'message': str(e),
                    'sticky': False,
                    'type': 'danger',
                }
            }

    def sync_chatby_subscribers(self):
        self.ensure_one()
        try:
            result = self.env['chatby.subscriber'].sync_subscribers()
            return result
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': str(e),
                    'sticky': True,
                    'type': 'danger',
                }
            }