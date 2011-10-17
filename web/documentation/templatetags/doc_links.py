#!/usr/bin/env python

from django import template
register = template.Library()

from documentation.titles import page_titles

@register.simple_tag
def doc_link_full(template_name, language):
    template_name = template_name.replace('LANG', language)
    
    # Catch anything requesting javascript before it is time.
    if not page_titles in template_name:
        page_titles = 'python'
        
    title = page_titles[template_name][0]
    return '''<a href="/docs/%s/%s">%s</a>''' % (language, template_name, title)

@register.simple_tag
def doc_change_lang(request, from_lang, to_lang):
    return request.path.replace(from_lang, to_lang)




