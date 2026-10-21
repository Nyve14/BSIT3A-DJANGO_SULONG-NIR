import sys
files = {
    'apps/public_services/apps.py': 'from django.apps import AppConfig\n\n\nclass PublicServicesConfig(AppConfig):\n    default_auto_field = "django.db.models.BigAutoField"\n    name = "apps.public_services"\n    verbose_name = "Public Services"\n',
    'apps/__init__.py': '',
    'apps/public_services/__init__.py': '',
    'apps/public_services/migrations/__init__.py': '',
}
for path, content in files.items():
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
print('Files rewritten successfully')