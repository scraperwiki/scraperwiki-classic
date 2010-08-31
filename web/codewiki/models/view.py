# encoding: utf-8
import datetime
import time
import settings
import tagging
import code
import scraper
from django.db import models
from django.contrib.auth.models import User
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType

try:
    import json
except:
    import simplejson as json

class View (code.Code):

    mime_type = models.CharField(max_length=255, null=True)
    unfiltered = models.Manager() # django admin gets all confused if this lives in the parent class, so duplicated in child classes

    def __init__(self, *args, **kwargs):
        super(View, self).__init__(*args, **kwargs)
        self.wiki_type = 'view'        

    def save(self, *args, **kwargs):
        self.wiki_type = 'view'
        super(View, self).save(*args, **kwargs)

    class Meta:
        app_label = 'codewiki'


#register tagging
try:
    tagging.register(View)
except tagging.AlreadyRegistered:
    pass
