from django.template import Library, Node

register = Library()

@register.inclusion_tag('frontend/templatetags/sparkline.html')
def sparkline(data_csv, size = 'small', color='336699'):

    #work out size
    width = 80
    height = 20
    if size == 'medium':
        width = 150
        height = 60
    elif size == 'large':
        width = 200
        height = 80

    return {'data_csv': data_csv, 'color': color, 'width': width, 'height': height}