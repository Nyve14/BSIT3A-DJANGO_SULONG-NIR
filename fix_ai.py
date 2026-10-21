import sys
files = {
    'apps/ai_services/apps.py': 'from django.apps import AppConfig\n\n\nclass AiServicesConfig(AppConfig):\n    default_auto_field = "django.db.models.BigAutoField"\n    name = "apps.ai_services"\n    verbose_name = "AI Services"\n',
    'apps/ai_services/__init__.py': '',
    'apps/ai_services/migrations/__init__.py': '',
}
for path, content in files.items():
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
print('AI files rewritten successfully')