{
    'name': "Custom Login Logo",
    'version': '1.0',
    'author': "Ayoub Akhrif",
    'depends': ['web'],
    'data': [
        'views/login_inherit.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'custom_login_logo/static/src/css/login.css',
        ],
    },
}
