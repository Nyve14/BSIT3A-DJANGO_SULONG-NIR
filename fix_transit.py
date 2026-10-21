import sys
files = {
    'apps/transit/apps.py': 'from django.apps import AppConfig\n\n\nclass TransitConfig(AppConfig):\n    default_auto_field = "django.db.models.BigAutoField"\n    name = "apps.transit"\n    verbose_name = "Transit"\n',
    'apps/transit/__init__.py': '',
    'apps/transit/migrations/__init__.py': '',
}
for path, content in files.items():
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
print('Transit files rewritten successfully')