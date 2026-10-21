import sys
files = {
    'apps/alerts/apps.py': 'from django.apps import AppConfig\n\n\nclass AlertsConfig(AppConfig):\n    default_auto_field = "django.db.models.BigAutoField"\n    name = "apps.alerts"\n    verbose_name = "Emergency Alerts"\n',
    'apps/alerts/__init__.py': '',
    'apps/alerts/migrations/__init__.py': '',
}
for path, content in files.items():
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
print('Alerts files rewritten successfully')