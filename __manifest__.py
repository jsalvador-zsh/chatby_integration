{
    'name': 'ChatBy Connector',
    'version': '1.0',
    'summary': 'Integración Odoo con la plataforma omnicanal ChatBy',
    'description': """
        Módulo para conectar Odoo con ChatBy
        Permite gestionar leads, contactos, mensajes y más desde plataformas como WhatsApp, Facebook, Instagram, etc.
    """,
    'author': 'Juan Salvador',
    'website': 'https://jsalvador.dev',
    'category': 'Tools',
    'depends': ['base', 'web', 'mail', 'crm', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/chatby_subscriber_views.xml',
        'views/chatby_message_views.xml',
        'views/menu_views.xml',
        'views/res_config_settings_views.xml',
        'data/cron_jobs.xml',
    ],
    'installable': True,
    'application': True,
}