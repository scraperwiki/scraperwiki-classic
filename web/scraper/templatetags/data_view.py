from django.template import Library, Node

register = Library()

def field_errors(field):
    return {'errors': field.errors}

register.inclusion_tag('frontend/templatetags/field_errors.html')(field_errors)
