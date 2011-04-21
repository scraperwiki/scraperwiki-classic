#!/usr/bin/env python

from django.core.cache import cache
from django import template
from django.contrib.auth.models import User
from codewiki.models import Scraper, View
register = template.Library()

def cache_value(key):
    def decorator(fn):
        def inner():
            val = cache.get(key)
            if not val:
                val = fn()
                cache.set(key, val, 60)
            return val
        inner.__name__ = fn.__name__
        return inner
    return decorator

@register.simple_tag
@cache_value('num_scrapers')
def num_scrapers():
    return Scraper.objects.count()

@register.simple_tag
@cache_value('num_views')
def num_views():
    return View.objects.count()

@register.simple_tag
@cache_value('num_users')
def num_users():
    return User.objects.count()
