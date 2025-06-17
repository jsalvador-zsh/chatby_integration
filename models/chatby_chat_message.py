from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import requests
import logging

_logger = logging.getLogger(__name__)

class ChatByChatMessage(models.Model):
    _name = 'chatby.chat.message'
    _description = 'ChatBy Chat Message'
    _order = 'ts desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Campos principales
    mid = fields.Char(string='Message ID', readonly=True, index=True)
    subscriber_id = fields.Many2one(
        'chatby.subscriber', 
        string='Subscriber',
        required=True,
        readonly=True,
        ondelete='cascade'
    )
    user_id = fields.Char(
        string='User ID', 
        related='subscriber_id.user_id',
        readonly=True,
        store=True
    )
    type = fields.Selection([
        ('in', 'Incoming'),
        ('out', 'Outgoing'),
        ('agent', 'Agent')
    ], string='Direction', readonly=True)
    msg_type = fields.Selection([
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('file', 'File'),
        ('audio', 'Audio'),
        ('other', 'Other')
    ], string='Message Type', readonly=True)
    sender_id = fields.Char(string='Sender ID', readonly=True)
    agent_id = fields.Integer(string='Agent ID', readonly=True)
    content = fields.Text(string='Content', readonly=True)
    username = fields.Char(string='Username', readonly=True)
    ts = fields.Datetime(string='Timestamp', readonly=True)
    paused_diff_seconds = fields.Integer(string='Paused Seconds', readonly=True)
    message_id = fields.Integer(string='ChatBy Message ID', readonly=True)
    
    # Campos para payload estructurado
    payload_text = fields.Text(string='Text Payload', readonly=True)
    payload_url = fields.Char(string='Media URL', readonly=True)
    
    @api.model
    def fetch_messages_for_subscriber(self, subscriber):
        """Obtiene mensajes para un subscriber específico"""
        if not subscriber.user_id:
            _logger.warning("Subscriber sin user_id, no se pueden obtener mensajes")
            return False
            
        api_url = self.env['ir.config_parameter'].sudo().get_param(
            'chatby_integration.api_url', 
            'https://app.chatby.io/api'
        )
        
        headers = self.env['chatby.api']._get_auth_headers()
        params = {
            'user_id': subscriber.user_id
        }
        
        try:
            response = requests.get(
                f'{api_url}/subscriber/chat-messages',
                headers=headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _logger.error("Error fetching messages for subscriber %s: %s", subscriber.user_id, str(e))
            raise UserError(_('Error al obtener mensajes: %s') % str(e))
    
    @api.model
    def process_message_data(self, message_data, subscriber):
        """Procesa los datos de un mensaje y retorna valores para crear/actualizar"""
        # Convertir timestamp de Unix a datetime
        message_date = False
        if message_data.get('ts'):
            try:
                message_date = datetime.fromtimestamp(int(message_data['ts']))
            except (ValueError, TypeError) as e:
                _logger.warning("Error convirtiendo timestamp %s: %s", message_data.get('ts'), str(e))
        
        # Extraer información del payload
        payload_text = message_data.get('payload', {}).get('text', '')
        payload_url = message_data.get('payload', {}).get('url', '')
        
        return {
            'mid': message_data.get('mid'),
            'subscriber_id': subscriber.id,
            'type': message_data.get('type'),
            'msg_type': message_data.get('msg_type'),
            'sender_id': message_data.get('sender_id'),
            'agent_id': message_data.get('agent_id', 0),
            'content': message_data.get('content', payload_text),
            'username': message_data.get('username'),
            'ts': message_date,
            'paused_diff_seconds': message_data.get('paused_diff_seconds', 0),
            'message_id': message_data.get('id'),
            'payload_text': payload_text,
            'payload_url': payload_url if payload_url else None,
        }
    
    @api.model
    def sync_messages_for_subscriber(self, subscriber):
        """Sincroniza mensajes para un subscriber específico"""
        try:
            messages_data = self.fetch_messages_for_subscriber(subscriber)
            messages = messages_data.get('data', [])
            
            if not messages:
                _logger.info("No hay mensajes nuevos para el subscriber %s", subscriber.user_id)
                return True
                
            existing_mids = set(self.search([
                ('subscriber_id', '=', subscriber.id)
            ]).mapped('mid'))
            
            created_count = 0
            for msg_data in messages:
                if msg_data.get('mid') in existing_mids:
                    continue
                    
                message_vals = self.process_message_data(msg_data, subscriber)
                self.create(message_vals)
                created_count += 1
                
            _logger.info("Sincronizados %d nuevos mensajes para subscriber %s", created_count, subscriber.user_id)
            return created_count
            
        except Exception as e:
            _logger.error("Error sincronizando mensajes para subscriber %s: %s", subscriber.user_id, str(e))
            raise UserError(_('Error al sincronizar mensajes: %s') % str(e))
    
    @api.model
    def _cron_sync_all_messages(self):
        """Job programado para sincronizar mensajes de todos los subscribers"""
        subscribers = self.env['chatby.subscriber'].search([])
        total_created = 0
        
        for subscriber in subscribers:
            try:
                created = self.sync_messages_for_subscriber(subscriber)
                if created:
                    total_created += created
            except Exception as e:
                _logger.error("Error procesando subscriber %d: %s", subscriber.id, str(e))
                continue
                
        _logger.info("Sincronización completa. Total de mensajes nuevos: %d", total_created)
        return True