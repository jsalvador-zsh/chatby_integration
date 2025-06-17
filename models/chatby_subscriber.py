from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import requests
import base64
import logging

_logger = logging.getLogger(__name__)

class ChatBySubscriber(models.Model):
    _name = 'chatby.subscriber'
    _description = 'ChatBy Subscriber'
    _order = 'last_interaction desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    user_ns = fields.Char(string='User NS', readonly=True, index=True)
    user_id = fields.Char(string='User ID', readonly=True)
    agent_id = fields.Integer(string='Agent ID', readonly=True)
    channel = fields.Selection([
        ('instagram', 'Instagram'),
        ('facebook', 'Facebook'),
        ('whatsapp', 'WhatsApp'),
        ('web', 'Web'),
        ('telegram', 'Telegram'),
        ('other', 'Other')
    ], string='Channel', readonly=True)
    status = fields.Char(string='Status', readonly=True)
    first_name = fields.Char(string='First Name', readonly=True)
    last_name = fields.Char(string='Last Name', readonly=True)
    name = fields.Char(string='Username', readonly=True)
    gender = fields.Char(string='Gender', readonly=True)
    email = fields.Char(string='Email', readonly=True)
    phone = fields.Char(string='Phone', readonly=True)
    language = fields.Char(string='Language', readonly=True)
    country = fields.Char(string='Country', readonly=True)
    city = fields.Char(string='City', readonly=True)
    profile_pic = fields.Char(string='Profile Picture URL', readonly=True)
    profile_pic_url = fields.Char(string='Profile Picture URL', readonly=True)
    avatar_image = fields.Binary(string='Avatar', attachment=True)
    subscribed = fields.Datetime(string='Subscribed Date', readonly=True)
    last_interaction = fields.Datetime(string='Last Interaction', readonly=True)
    last_message_at = fields.Datetime(string='Last Message At', readonly=True)
    last_message_type = fields.Selection([
        ('in', 'Incoming'),
        ('out', 'Outgoing'),
        ('agent', 'Agent')
    ], string='Last Message Type', readonly=True)
    tags = fields.Char(string='Tags', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Related Partner')
    
    message_ids = fields.One2many(
        'chatby.chat.message', 
        'subscriber_id', 
        string='Messages'
    )

    opportunity_id = fields.Many2one('crm.lead', string='Oportunidad Relacionada')

    @api.model
    def create(self, vals):
        """Override create method to generate opportunity automatically"""
        # Primero creamos el subscriber
        subscriber = super(ChatBySubscriber, self).create(vals)
        
        # Luego creamos la oportunidad
        subscriber._create_opportunity()
        
        return subscriber
    
    def _create_opportunity(self):
        """Crea una oportunidad en el CRM basada en el subscriber"""
        self.ensure_one()
        try:
            # Determinar el nombre de la oportunidad
            opportunity_name = f"Nuevo lead de {self.channel}"
            if self.first_name and self.last_name:
                opportunity_name = f"{self.first_name} {self.last_name} - {self.channel}"
            elif self.name:
                opportunity_name = f"{self.name} - {self.channel}"
            
            # Determinar la etapa inicial (usaremos la primera etapa de tipo 'New')
            stage = self.env['crm.stage'].search([('team_id', '=', False)], limit=1)
            
            # Crear la oportunidad
            opportunity = self.env['crm.lead'].create({
                'name': opportunity_name,
                'partner_id': self.partner_id.id if self.partner_id else False,
                'email_from': self.email,
                'phone': self.phone,
                'description': _("""Subscriber creado desde ChatBy\nCanal: %s\nUsuario: %s\nID: %s\nÚltima interacción: %s""") % (self.channel, self.name or '-', self.user_id or '-', self.last_interaction or '-'),
                'stage_id': stage.id if stage else False,
                'team_id': False,
                'user_id': False,
                'source_id': self.env.ref('odoo_chatby_plg.source_chatby').id if \
                    self.env.ref('odoo_chatby_plg.source_chatby', False) else False,
                'subscriber_id': self.id,
            })
            
            # Relacionar la oportunidad con el subscriber
            self.opportunity_id = opportunity.id
            
            _logger.info("Oportunidad creada automáticamente para subscriber %s", self.id)
            return opportunity
            
        except Exception as e:
            _logger.error("Error al crear oportunidad para subscriber %s: %s", self.id, str(e))
            return False

    def action_create_partner(self):
        """Crea un partner a partir del subscriber"""
        self.ensure_one()
        Partner = self.env['res.partner']
        
        # Buscar si ya existe un partner con este email, phone o user_ns
        domain = []
        if self.email:
            domain.append(('email', '=', self.email))
        if self.phone:
            domain.append(('mobile', '=', self.phone))
        if self.user_ns:
            domain.append(('user_ns', '=', self.user_ns))
        
        existing_partner = False
        if domain:
            existing_partner = Partner.search(domain, limit=1)
        
        if existing_partner:
            # Actualizar el partner existente con los nuevos datos
            update_vals = {
                'email': self.email or False,
                'mobile': self.phone or False,
                'user_ns': self.user_ns,
                'user_id': self.user_id,
                'agent_id': self.agent_id,
                'channel': self.channel,
                'chatby_subscriber_id': self.id,
            }
            existing_partner.write(update_vals)
            self.partner_id = existing_partner.id
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Información'),
                    'message': _('Partner actualizado: %s') % existing_partner.name,
                    'type': 'info',
                    'sticky': False,
                }
            }
        
        # Crear nuevo partner
        partner_vals = {
            'name': f"{self.first_name or ''} {self.last_name or ''}".strip() or self.name,
            'email': self.email or False,
            'mobile': self.phone or False,
            'country_id': self.env['res.country'].search([('name', '=', self.country)], limit=1).id if self.country else False,
            'city': self.city or False,
            'comment': _('ChatBy subscriber. Channel: %s. Subscribed: %s') % (self.channel, self.subscribed),
            'user_ns': self.user_ns,
            'user_id': self.user_id,
            'agent_id': self.agent_id,
            'channel': self.channel,
            'chatby_subscriber_id': self.id,
            'image_1920': self.avatar_image if self.avatar_image else False,
        }
        
        partner = Partner.create(partner_vals)
        self.partner_id = partner.id
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Éxito'),
                'message': _('Partner creado: %s') % partner.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def _download_profile_image(self, image_url):
        """Descarga la imagen de perfil desde la URL y la retorna como binario"""
        if not image_url:
            return False
            
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            return base64.b64encode(response.content)
        except Exception as e:
            _logger.warning("No se pudo descargar la imagen de perfil: %s", str(e))
            return False

    @api.model
    def sync_subscribers(self):
        """Sincroniza los subscribers desde ChatBy incluyendo sus imágenes"""
        try:
            subscribers_data = self.env['chatby.api'].get_subscribers()
            subscribers = subscribers_data.get('data', [])
            
            if not subscribers:
                raise UserError(_('No se encontraron subscribers en ChatBy'))
            
            created_count = 0
            for sub_data in subscribers:
                # Convertir fechas string a datetime
                subscribed_date = datetime.strptime(sub_data['subscribed'], '%Y-%m-%d %H:%M:%S') if sub_data.get('subscribed') else False
                last_interaction = datetime.strptime(sub_data['last_interaction'], '%Y-%m-%d %H:%M:%S') if sub_data.get('last_interaction') else False
                last_message_at = datetime.strptime(sub_data['last_message_at'], '%Y-%m-%d %H:%M:%S') if sub_data.get('last_message_at') else False
                
                # Descargar imagen de perfil si está disponible
                avatar_image = False
                if sub_data.get('profile_pic'):
                    avatar_image = self._download_profile_image(sub_data['profile_pic'])
                
                # Buscar si ya existe el subscriber
                existing_sub = self.search([('user_ns', '=', sub_data['user_ns'])], limit=1)
                
                vals = {
                    'user_ns': sub_data['user_ns'],
                    'user_id': sub_data['user_id'],
                    'agent_id': sub_data['agent_id'],
                    'channel': sub_data['channel'],
                    'status': sub_data['status'],
                    'first_name': sub_data['first_name'],
                    'last_name': sub_data['last_name'],
                    'name': sub_data['name'],
                    'gender': sub_data['gender'],
                    'email': sub_data['email'],
                    'phone': sub_data['phone'],
                    'language': sub_data['language'],
                    'country': sub_data['country'],
                    'city': sub_data['city'],
                    'profile_pic_url': sub_data['profile_pic'],
                    'avatar_image': avatar_image,
                    'subscribed': subscribed_date,
                    'last_interaction': last_interaction,
                    'last_message_at': last_message_at,
                    'last_message_type': sub_data['last_message_type'],
                    'tags': ', '.join(sub_data['tags']) if sub_data.get('tags') else '',
                }
                
                if existing_sub:
                    existing_sub.write(vals)
                else:
                    self.create(vals)
                    created_count += 1
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sincronización completada'),
                    'message': _('Se sincronizaron %d nuevos subscribers con sus imágenes') % created_count,
                    'type': 'success',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            raise UserError(_('Error al sincronizar subscribers: %s') % str(e))

    def action_sync_messages(self):
        """Acción para sincronizar mensajes manualmente"""
        self.ensure_one()
        try:
            count = self.env['chatby.chat.message'].sync_messages_for_subscriber(self)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Éxito'),
                    'message': _('Se sincronizaron %d nuevos mensajes') % count if count else _('No hay mensajes nuevos'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_('Error al sincronizar mensajes: %s') % str(e))

    @api.model
    def _cron_sync_subscribers(self):
        """Job programado para sincronizar subscribers cada 5 minutos"""
        _logger.info("Iniciando sincronización automática de subscribers desde ChatBy")
        try:
            return self.sync_subscribers()
        except Exception as e:
            _logger.error("Error en la sincronización automática: %s", str(e))
            return False

    @api.model
    def _cron_create_update_partners(self):
        """Job programado para crear/actualizar partners cada 5 minutos"""
        _logger.info("Iniciando creación/actualización automática de partners")
        
        # Obtener subscribers sin partner o con cambios recientes
        domain = [
            '|',
            ('partner_id', '=', False),
            ('write_date', '>=', fields.Datetime.now() - timedelta(minutes=10))
        ]
        
        subscribers = self.search(domain)
        if not subscribers:
            _logger.info("No hay subscribers nuevos o modificados para procesar")
            return True
            
        success_count = 0
        error_count = 0
        
        for subscriber in subscribers:
            try:
                subscriber.action_create_partner()
                success_count += 1
            except Exception as e:
                _logger.error("Error procesando subscriber ID %d: %s", subscriber.id, str(e))
                error_count += 1
        
        _logger.info("Proceso completado: %d exitosos, %d errores", success_count, error_count)
        
        if error_count > 0:
            # Notificar al administrador si hay errores
            self.env['mail.thread'].message_notify(
                subject=_("Errores en creación automática de partners"),
                body=_("Hubo %d errores al crear/actualizar partners desde subscribers.") % error_count,
                partner_ids=[self.env.ref('base.user_admin').partner_id.id],
            )
        
        return True