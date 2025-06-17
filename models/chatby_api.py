import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ChatByAPI(models.AbstractModel):
    _name = 'chatby.api'
    _description = 'ChatBy API Integration'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _get_auth_headers(self):
        """Retorna los headers de autenticación para la API"""
        token = self.env['ir.config_parameter'].sudo().get_param('chatby_integration.token')
        if not token:
            raise UserError(_('Por favor configure el token de ChatBy primero'))
        
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    @api.model
    def test_connection(self):
        """Prueba la conexión con la API de ChatBy"""
        api_url = self.env['ir.config_parameter'].sudo().get_param(
            'chatby_integration.api_url', 
            'https://app.chatby.io/api'
        )
        
        headers = self._get_auth_headers()
        
        try:
            # Endpoint para verificar autenticación
            response = requests.get(
                f'{api_url}/me',
                headers=headers,
                timeout=10
            )
            
            # Verificar si la respuesta fue exitosa
            response.raise_for_status()
            
            # Intentar parsear la respuesta JSON
            data = response.json()
            
            # Retornar información útil del usuario/conexión
            return {
                'status': 'success',
                'message': _('Conexión exitosa con ChatBy'),
                'data': data
            }
            
        except requests.exceptions.HTTPError as http_err:
            if http_err.response.status_code == 401:
                raise UserError(_('Error de autenticación: Token inválido o expirado'))
            else:
                raise UserError(_('Error HTTP: %s') % str(http_err))
        except requests.exceptions.ConnectionError:
            raise UserError(_('Error de conexión: No se pudo contactar el servidor de ChatBy'))
        except requests.exceptions.Timeout:
            raise UserError(_('Timeout: El servidor de ChatBy no respondió a tiempo'))
        except requests.exceptions.RequestException as e:
            raise UserError(_('Error al conectar con ChatBy: %s') % str(e))
        except ValueError:
            raise UserError(_('Respuesta inválida del servidor: No se pudo interpretar la respuesta JSON'))

    @api.model
    def get_subscribers(self, page=1, per_page=50):
        """Obtiene los subscribers de ChatBy"""
        api_url = self.env['ir.config_parameter'].sudo().get_param(
            'chatby_integration.api_url', 
            'https://app.chatby.io/api'
        )
        
        headers = self._get_auth_headers()
        params = {
            'page': page,
            'per_page': per_page
        }
        
        try:
            response = requests.get(
                f'{api_url}/subscribers',
                headers=headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _logger.error("Error fetching ChatBy subscribers: %s", str(e))
            raise UserError(_('Error al obtener subscribers de ChatBy: %s') % str(e))