from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from piston.resource import Resource
from handlers import ScraperInfoHandler, GetDataHandler

from api import views

scraperinfo_handler = Resource(ScraperInfoHandler)
data_handler = Resource(GetDataHandler)

# Version 1.0 URLS
urlpatterns = patterns('',

    # Standard Views
    url(r'^keys$', views.keys, name='keys'),

    # Documentation
    url(r'^$', 'django.views.generic.simple.direct_to_template', {'template': 'index.html'}),
    url(r'^1\.0/$', 'django.views.generic.simple.direct_to_template', {'template': '1.0.html'}, name='index'),
    url(r'^1\.0/scraperwiki.scraper.search/$', views.explore_scraper_search, name='scraper_search'),

    # API calls

    #explorer
    url(r'^explorer_call$', views.explorer_user_run, name='explorer_call'),
    url(r'^explorer_example/(?P<method>[\w_\-\.\_]+)/$', views.explorer_example, name='explorer_example'),    

    url(r'^1\.0/scraper/getinfo$', scraperinfo_handler),
    url(r'^1\.0/scraper/getdata$', data_handler),

)