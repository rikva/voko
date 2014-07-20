from django.contrib import admin
from django.db.models.loading import get_models, get_app

for model in get_models(get_app('shared')):
    admin.site.register(model)