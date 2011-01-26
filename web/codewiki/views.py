from django.contrib.sites.models import Site
from django.template import RequestContext
from django.template.loader import render_to_string
from django.http import HttpResponseRedirect, HttpResponse, Http404, HttpResponseNotFound
from django.shortcuts import render_to_response
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.core.management import call_command
from tagging.models import Tag, TaggedItem
from tagging.utils import get_tag
from django.db import IntegrityError
from django.contrib.auth.models import User
from django.views.decorators.http import condition
import textile
import random
from django.conf import settings
from django.utils.encoding import smart_str

from managers.datastore import  DataStore

from codewiki import models
from api.emitters import CSVEmitter 
import vc
import frontend

import difflib
import re
import csv
import math
import urllib2
import base64

from cStringIO import StringIO
import csv, types
import datetime
import gdata.docs.service

try:                import json
except ImportError: import simplejson as json

def get_code_object_or_none(klass, short_name):
    try:
        return klass.objects.get(short_name=short_name)
    except:
        return None

def code_error_response(klass, short_name, request):
    if klass.unfiltered.filter(short_name=short_name, deleted=True).count() == 1:
        body = 'Sorry, this %s has been deleted by the owner' % klass.__name__
        string = render_to_string('404.html', {'heading': 'Deleted', 'body': body}, context_instance=RequestContext(request))
        return HttpResponseNotFound(string)
    else:
        raise Http404

def code_overview(request, wiki_type, short_name):
    if wiki_type == 'scraper':
        return scraper_overview(request, short_name)
    else:
        return view_overview(request, short_name)

def scraper_overview(request, short_name):
    """
    Shows info on the scraper plus example data.
    """
    user = request.user
    scraper = get_code_object_or_none(models.Scraper, short_name=short_name)
    if not scraper:
        return code_error_response(models.Scraper, short_name=short_name, request=request)

    # Only logged in users should be able to see unpublished scrapers
    if not scraper.published and not user.is_authenticated():
        return render_to_response('codewiki/access_denied_unpublished.html', context_instance=RequestContext(request))
    
    #get views that use this scraper
    related_views = models.View.objects.filter(relations=scraper)
    
    #get meta data
    user_owns_it = (scraper.owner() == user)
    user_follows_it = (user in scraper.followers())
    scraper_contributors = scraper.contributors()
    scraper_requesters = scraper.requesters()    
    scraper_tags = Tag.objects.get_for_object(scraper)
    
    lscraperrunevents = scraper.scraperrunevent_set.all().order_by("-run_started")[:1] 
    lastscraperrunevent = lscraperrunevents and lscraperrunevents[0] or None

    context = {
        'scraper_tags': scraper_tags,
        'selected_tab': 'overview',
        'scraper': scraper,
        'lastscraperrunevent':lastscraperrunevent,
        'user_owns_it': user_owns_it,
        'user_follows_it': user_follows_it,
        'scraper_contributors': scraper_contributors,
        'scraper_requesters': scraper_requesters,
        'related_views': related_views,
        'schedule_options': models.SCHEDULE_OPTIONS,
        'license_choices': models.LICENSE_CHOICES,
        }
    
    #get data for this scaper in a way that we can see exactly what is being transferred
    column_order = scraper.get_metadata('data_columns')
    if not user_owns_it:
        private_columns = scraper.get_metadata('private_columns')
    else:
        private_columns = None
    data = models.Scraper.objects.data_summary(scraper_id=scraper.guid,
                                               limit=50, 
                                               column_order=column_order,
                                               private_columns=private_columns)

    if len(data['rows']) > 12:
        data['morerows'] = data['rows'][9:]
        data['rows'] = data['rows'][:9]
    
    if data['rows']:
        context['datasinglerow'] = zip(data['headings'], data['rows'][0])
    
    context['data'] = data
    
    dataproxy = DataStore(scraper.guid, scraper.short_name)
    context['sqlitedata'] = dataproxy.request(("sqlitecommand", "datasummary", None, None))
    
    #if user.username == 'Julian_Todd':
    #    return render_to_response('codewiki/scraper_overview_jgt.html', context, context_instance=RequestContext(request))
    return render_to_response('codewiki/scraper_overview.html', context, context_instance=RequestContext(request))


def view_admin(request, short_name):
    view = get_code_object_or_none(models.View, short_name=short_name)
    if not view:
        return code_error_response(models.View, short_name=short_name, request=request)

    #you can only get here if you are signed in
    if not request.user.is_authenticated():
        raise Http404

    if request.method == 'POST' and request.is_ajax():
        response = HttpResponse()
        response_text = ''
        element_id = request.POST.get('id', None)
        if element_id == 'divAboutScraper':
            view.description = request.POST.get('value', None)
            response_text = textile.textile(view.description)

        if element_id == 'hCodeTitle':
            view.title = request.POST.get('value', None)
            response_text = view.title

        if element_id == 'divEditTags':
            view.tags = request.POST.get('value', '')
            response_text = ", ".join([tag.name for tag in view.tags])

        #save view
        view.save()
        response.write(response_text)
        return response
    else:
        raise Http404
    
    
def scraper_admin(request, short_name):
    scraper = get_code_object_or_none(models.Scraper, short_name=short_name)
    if not scraper:
        return code_error_response(models.Scraper, short_name=short_name, request=request)

    #you can only get here if you are signed in
    if not request.user.is_authenticated():
        raise Http404

    if request.method == 'POST' and request.is_ajax():
        response = HttpResponse()
        response_text = ''
        element_id = request.POST.get('id', None)
        if element_id == 'divAboutScraper':
            scraper.description = request.POST.get('value', None)
            response_text = textile.textile(scraper.description)
            
        if element_id == 'hCodeTitle':
            scraper.title = request.POST.get('value', None)
            response_text = scraper.title

        if element_id == 'divEditTags':
            scraper.tags = request.POST.get('value', '')
            response_text = ", ".join([tag.name for tag in scraper.tags])

        if element_id == 'spnRunInterval':
            scraper.run_interval = int(request.POST.get('value', None))
            response_text = models.SCHEDULE_OPTIONS_DICT[scraper.run_interval]

        if element_id == 'spnLicenseChoice':
            scraper.license = request.POST.get('value', None)
            response_text = scraper.license

        if element_id == 'publishScraperButton':
            scraper.published = True
            response_text = ''

        #save scraper
        scraper.save()
        response.write(response_text)
        return response
    else:
        raise Http404


def scraper_delete_data(request, short_name):
    scraper = get_code_object_or_none(models.Scraper, short_name=short_name)
    if not scraper:
        return code_error_response(models.Scraper, short_name=short_name, request=request)

    if scraper.owner() != request.user:
        raise Http404
    if request.POST.get('delete_data', None) == '1':
        models.Scraper.objects.clear_datastore(scraper_id=scraper.guid)
        scraper.scrapermetadata_set.all().delete()
        scraper.update_meta()
        scraper.save()


    return HttpResponseRedirect(reverse('code_overview', args=[scraper.wiki_type, short_name]))

# implemented by setting last_run to None
def scraper_schedule_scraper(request, short_name):
    scraper = get_code_object_or_none(models.Scraper, short_name=short_name)
    if not scraper:
        return code_error_response(models.Scraper, short_name=short_name, request=request)

    if scraper.owner() != request.user and not request.user.is_staff:
        raise Http404
    if request.POST.get('schedule_scraper', None) == '1':
        scraper.last_run = None
        scraper.save()
    return HttpResponseRedirect(reverse('code_overview', args=[scraper.wiki_type, short_name]))


def scraper_run_scraper(request, short_name):
    scraper = get_code_object_or_none(models.Scraper, short_name=short_name)
    if not scraper:
        return code_error_response(models.Scraper, short_name=short_name, request=request)

    if not request.user.is_staff:
        raise Http404

    if request.POST.get('run_scraper', None) == '1':
        call_command('run_scrapers', short_name=short_name)
    
    return HttpResponseRedirect(reverse('code_overview', args=[scraper.wiki_type, short_name]))

def scraper_screenshoot_scraper(request, wiki_type, short_name):
    if wiki_type == 'scraper':
        code_object = get_code_object_or_none(models.Scraper, short_name=short_name)
        if not code_object:
            return code_error_response(models.Scraper, short_name=short_name, request=request)
    else:
        code_object = get_code_object_or_none(models.View, short_name=short_name)
        if not code_object:
            return code_error_response(models.View, short_name=short_name, request=request)

    if not request.user.is_staff:
        raise Http404

    if request.POST.get('screenshoot_scraper', None) == '1':
        call_command('take_screenshot', short_name=short_name, domain=settings.VIEW_DOMAIN, verbose=False)
    
    return HttpResponseRedirect(reverse('code_overview', args=[code_object.wiki_type, short_name]))


def scraper_delete_scraper(request, wiki_type, short_name):
    if wiki_type == 'scraper':
        code_object = get_code_object_or_none(models.Scraper, short_name=short_name)
        if not code_object:
            return code_error_response(models.Scraper, short_name=short_name, request=request)
    else:
        code_object = get_code_object_or_none(models.View, short_name=short_name)
        if not code_object:
            return code_error_response(models.View, short_name=short_name, request=request)

    if code_object.owner() != request.user:
        raise Http404

    if request.POST.get('delete_scraper', None) == '1':
        code_object.deleted = True
        code_object.save()
        request.notifications.add("Your %s has been deleted" % wiki_type)
        return HttpResponseRedirect('/')

    return HttpResponseRedirect(reverse('code_overview', args=[code_object.wiki_type, short_name]))


def view_overview (request, short_name):
    user = request.user
    scraper = get_code_object_or_none(models.View, short_name=short_name)
    if not scraper:
        return code_error_response(models.View, short_name=short_name, request=request)

    scraper_tags = Tag.objects.get_for_object(scraper)
    user_owns_it = (scraper.owner() == user)
    
    #get scrapers used in this view
    related_scrapers = scraper.relations.filter(wiki_type='scraper')
    
    context = {'selected_tab': 'overview', 'scraper': scraper, 'scraper_tags': scraper_tags, 'related_scrapers': related_scrapers, 'user_owns_it': user_owns_it}
    return render_to_response('codewiki/view_overview.html', context, context_instance=RequestContext(request))
    
    
def view_fullscreen (request, short_name):
    user = request.user
    urlquerystring = request.META["QUERY_STRING"]

    scraper = get_code_object_or_none(models.View, short_name=short_name)
    if not scraper:
        return code_error_response(models.View, short_name=short_name, request=request)

    return render_to_response('codewiki/view_fullscreen.html', {'scraper': scraper, 'urlquerystring':urlquerystring}, context_instance=RequestContext(request))

def comments(request, wiki_type, short_name):

    user = request.user
    scraper = get_code_object_or_none(models.Code, short_name=short_name)
    if not scraper:
        return code_error_response(models.Code, short_name=short_name, request=request)

    # Only logged in users should be able to see unpublished scrapers
    if not scraper.published and not user.is_authenticated():
        return render_to_response('codewiki/access_denied_unpublished.html', context_instance=RequestContext(request))

    user_owns_it = (scraper.owner() == user)
    user_follows_it = (user in scraper.followers())

    scraper_owner = scraper.owner()
    scraper_contributors = scraper.contributors()
    scraper_followers = scraper.followers()

    scraper_tags = Tag.objects.get_for_object(scraper)

    context = { 'scraper_tags': scraper_tags, 'scraper_owner': scraper_owner, 'scraper_contributors': scraper_contributors,
                   'scraper_followers': scraper_followers, 'selected_tab': 'comments', 'scraper': scraper,
                   'user_owns_it': user_owns_it, 'user_follows_it': user_follows_it }
    return render_to_response('codewiki/comments.html', context, context_instance=RequestContext(request))


def scraper_history(request, wiki_type, short_name):
    user = request.user
    
    scraper = get_code_object_or_none(models.Code, short_name=short_name)
    if not scraper:
        return code_error_response(models.Code, short_name=short_name, request=request)

    # Only logged in users should be able to see unpublished scrapers
    if not scraper.published and not user.is_authenticated():
        return render_to_response('codewiki/access_denied_unpublished.html', context_instance=RequestContext(request))

    dictionary = { 'selected_tab': 'history', 'scraper': scraper, "user":user }
    
    itemlog = [ ]
    
    for commitentry in scraper.get_commit_log():
        try:    user = User.objects.get(pk=int(commitentry["userid"]))
        except: user = None
        
        item = {"type":"commit", "rev":commitentry['rev'], "datetime":commitentry["date"], "user":user}
        item['earliesteditor'] = commitentry['description'].split('|||')
        item["users"] = set([item["user"]])
        item["firstrev"] = item["rev"]
        item["firstdatetime"] = item["datetime"]
        item["revcount"] = 1
        itemlog.append(item)
    
    itemlog.reverse()
    
    # now obtain the run-events and zip together
    if scraper.wiki_type == 'scraper':
        runevents = scraper.scraper.scraperrunevent_set.all().order_by('run_started')
        for runevent in runevents:
            item = { "type":"runevent", "runevent":runevent, "datetime":runevent.run_started }
            if runevent.run_ended:
                runduration = runevent.run_ended - runevent.run_started
                item["runduration"] = runduration
                item["durationseconds"] = "%.0f" % (runduration.days*24*60*60 + runduration.seconds)
            item["runevents"] = [ runevent ]
            itemlog.append(item)
        
        itemlog.sort(key=lambda x: x["datetime"], reverse=True)
    
    # aggregate the history list
    aitemlog = [ ]
    previtem = None
    for item in itemlog:
        if previtem and item["type"] == "commit" and previtem["type"] == "commit" and \
                                        item["earliesteditor"] == previtem["earliesteditor"]:
            previtem["users"].add(item["user"])
            previtem["firstrev"] = item["rev"]
            previtem["firstdatetime"] = item["datetime"]
            previtem["revcount"] += 1
            timeduration = previtem["datetime"] - item["datetime"]
            previtem["durationminutes"] = "%.0f" % (timeduration.days*24*60 + timeduration.seconds/60.0)

        elif len(aitemlog) >= 3 and aitemlog[-2]["type"] == "runevent" and item["type"] == "runevent" and previtem["type"] == "runevent" and aitemlog[-3]["type"] == "runevent" and \
                        aitemlog[-2]["runevent"].run_ended and previtem["runevent"].run_ended and \
                        bool(previtem["runevent"].exception_message) == bool(aitemlog[-2]["runevent"].exception_message):
            aitemlog[-2]["runevents"].insert(0, previtem["runevent"])
            aitemlog[-2]["runduration"] += previtem["runduration"]
            runduration = aitemlog[-2]["runduration"] / len(aitemlog[-2]["runevents"])  # average
            aitemlog[-2]["durationseconds"] = "%.0f" % (runduration.days*24*60*60 + runduration.seconds)
            aitemlog[-1] = item
            previtem = item
            
        else:
            aitemlog.append(item)
            previtem = item
    
    dictionary["itemlog"] = aitemlog
    dictionary["filestatus"] = scraper.get_file_status()
    
    return render_to_response('codewiki/history.html', dictionary, context_instance=RequestContext(request))



def tags(request, wiki_type, short_name):
    if wiki_type == 'scraper':
        code_object = get_code_object_or_none(models.Scraper, short_name)
    else:
        code_object = get_code_object_or_none(models.View, short_name)
    return HttpResponse(", ".join([tag.name for tag in code_object.tags]))


def raw_about_markup(request, wiki_type, short_name):
    code_object = get_code_object_or_none(models.Code, short_name=short_name)
    if not code_object:
        return code_error_response(models.Code, short_name=short_name, request=request)

    response = HttpResponse(mimetype='text/x-web-textile')
    response.write(code_object.description)
    return response


        
# see http://stackoverflow.com/questions/2922874/how-to-stream-an-httpresponse-with-django
# also inlining the crappy CSVEmitter.to_csv pointless functionality
# this is all painfully inefficient due to the unstructuredness of the datastore 
# and the fact that if you leave the output hanging too long the gateway times out
import time

# see http://stackoverflow.com/questions/1189111/unicode-to-utf8-for-csv-files-python-via-xlrd
# for issues about how the csv model can't handle unicode
def stringnot(v):
    if v == None:
        return ""
    if type(v) in [unicode, str]:
        return v.encode("utf-8")
    return v

def generate_csv(dictlist, offset, max_length=None):
    keyset = set()
    for row in dictlist:
        if "latlng" in row:   # split the latlng
            row["lat"], row["lng"] = row.pop("latlng") 
        row.pop("date_scraped", None) 
        keyset.update(row.keys())

    fout = StringIO()
    writer = csv.writer(fout, dialect='excel')
    truncated = False

    if offset == 0:
        writer.writerow([k.encode("utf-8") for k in keyset])
    for rowdict in dictlist:
        if max_length:
            # Save the length of the file in case adding
            # the next line takes it over the limit
            last_good_length = fout.tell()
            
        writer.writerow([stringnot(rowdict.get(key)) for key in keyset])

        if max_length and fout.tell() > max_length:
            fout.seek(last_good_length)
            truncated = True
            break

    result = fout.getvalue(True)
    fout.close()
    return result, truncated

def stream_csv(scraper, step=5000, max_rows=1000000):
    for offset in range(0, max_rows, step):
        dictlist = models.Scraper.objects.data_dictlist(scraper_id=scraper.guid, limit=step, offset=offset)
        
        yield generate_csv(dictlist, offset)[0]
        if len(dictlist) != step:
            break   #we've reached the end of the data


# see http://stackoverflow.com/questions/2922874/how-to-stream-an-httpresponse-with-django
@condition(etag_func=None)
def export_csv(request, short_name):
    """
    This could have been done by having linked directly to the api/csvout, but
    difficult to make the urlreverse for something in a different app code here
    itentical to scraperwiki/web/api/emitters.py CSVEmitter render()
    """
    scraper = get_code_object_or_none(models.Scraper, short_name=short_name)
    if not scraper:
        return code_error_response(models.Scraper, short_name=short_name, request=request)

    response = HttpResponse(stream_csv(scraper), mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=%s.csv' % (short_name)
    return response


def export_gdocs_spreadsheet(request, short_name):
    #TODO: this funciton needs to change to cache things on disc and read the size from tehre rather than in memory
    scraper = get_code_object_or_none(models.Scraper, short_name=short_name)
    if not scraper:
        return code_error_response(models.Scraper, short_name=short_name, request=request)

    #get the csv, it's size and choose a title for the file
    title = scraper.title + " - from ScraperWiki.com"
    csv_url = 'http://%s%s' % (Site.objects.get_current().domain,  reverse('export_csv', kwargs={'short_name': scraper.short_name}))

    row_limit = 5000

    truncated_message = 'THIS IS A SUBSET OF THE DATA ONLY. GOOGLE DOCS LIMITS FILES TO 1MB. DOWNLOAD THE FULL DATASET AS CSV HERE: %s\n' % str(csv_url)
    subset_message = 'THIS IS A SUBSET OF THE DATA ONLY. A MAXIMUM OF %s RECORDS CAN BE UPLOADED FROM SCRAPERWIKI. DOWNLOAD THE FULL DATASET AS CSV HERE: %s\n' % (str(row_limit), csv_url)
    
    max_length = settings.GDOCS_UPLOAD_MAX - max(len(truncated_message), len(subset_message))
    csv_data, truncated = generate_csv(models.Scraper.objects.data_dictlist(scraper_id=scraper.guid, limit=row_limit), 0, max_length)

    if truncated:
        title = title + ' [SUBSET ONLY]'
        csv_data = truncated_message.encode('utf-8') + csv_data
    elif scraper.record_count > row_limit:
        csv_data = subset_message.encode('utf-8') + csv_data

    #create client and authenticate
    client = gdata.docs.service.DocsService()
    client.ClientLogin(settings.GDOCS_UPLOAD_USER, settings.GDOCS_UPLOAD_PASSWORD)

    #create a document reference
    ms = gdata.MediaSource(file_handle=StringIO(csv_data), content_type=gdata.docs.service.SUPPORTED_FILETYPES['CSV'], content_length=len(csv_data))

    #try to upload it
    #try:
    entry = client.Upload(ms, title, folder_or_uri=settings.GDOCS_UPLOAD_FOLDER_URI)
    
    #redirect
    print "redirecting"
    return HttpResponseRedirect(entry.GetAlternateLink().href)
        
    #except gdata.service.RequestError:
    #    print "failed to upload for some other reason"

def scraper_table(request):
    dictionary = { }
    dictionary["scrapers"] = models.Scraper.objects.filter(published=True).order_by('-created_at')
    dictionary["numpublishedscraperstotal"] = dictionary["scrapers"].count()
    dictionary["numunpublishedscraperstotal"] = models.Scraper.objects.filter(published=False).count()
    dictionary["numdeletedscrapers"] = models.Scraper.unfiltered.filter(deleted=True).count()
    dictionary["user"] = request.user
    return render_to_response('codewiki/scraper_table.html', dictionary, context_instance=RequestContext(request))



def follow (request, short_name):
    scraper = get_code_object_or_none(models.Scraper, short_name=short_name)
    if not scraper:
        return code_error_response(models.Scraper, short_name=short_name, request=request)

    user = request.user
    user_owns_it = (scraper.owner() == user)
    user_follows_it = (user in scraper.followers())
    # add the user to follower list
    scraper.add_user_role(user, 'follow')
    # Redirect after POST
    return HttpResponseRedirect('/scrapers/show/%s/' % scraper.short_name)


def unfollow(request, short_name):
    scraper = get_code_object_or_none(models.Scraper, short_name=short_name)
    print scraper
    if not scraper:
        return code_error_response(models.Scraper, short_name=short_name, request=request)
    print scraper

    user = request.user
    user_owns_it = (scraper.owner() == user)
    user_follows_it = (user in scraper.followers())
    # remove the user from follower list
    scraper.unfollow(user)
    # Redirect after POST
    return HttpResponseRedirect('/scrapers/show/%s/' % scraper.short_name)



def htmlview(request, short_name):
    view = get_code_object_or_none(models.View, short_name=short_name)
    if not view:
        return code_error_response(models.View, short_name=short_name, request=request)

    return HttpResponse(view.saved_code())


def choose_template(request, wiki_type):

    #get templates
    templates = models.Code.objects.filter(isstartup=True, wiki_type=wiki_type).order_by('language')
    
    sourcescraper = request.GET.get('sourcescraper', '')
    
    #choose template (ajax vs normal)
    template = 'codewiki/choose_template.html'
    if request.GET.get('ajax', False):
        template = 'codewiki/includes/choose_template.html'
        
    return render_to_response(template, {'wiki_type': wiki_type, 'templates': templates, 
                                         'languages': sorted([ ll[1] for ll in models.code.LANGUAGES ]), 
                                         'sourcescraper':sourcescraper }, 
                              context_instance=RequestContext(request))


    
def delete_draft(request):
    if request.session.get('ScraperDraft', False):
        del request.session['ScraperDraft']

    # Remove any pending notifications, i.e. the "don't worry, your scraper is safe" one
    request.notifications.used = True

    return HttpResponseRedirect(reverse('frontpage'))


def convtounicode(text):
    try:   return unicode(text)
    except UnicodeDecodeError:  pass
        
    try:   return unicode(text, encoding='utf8')
    except UnicodeDecodeError:  pass
    
    try:   return unicode(text, encoding='latin1')
    except UnicodeDecodeError:  pass
        
    return unicode(text, errors='replace')


def proxycached(request):
    cacheid = request.POST.get('cacheid')
    
    # delete this later when no more need for debugging
    if not cacheid:  
        cacheid = request.GET.get('cacheid')
    
    if not cacheid:
        return HttpResponse(json.dumps({'type':'error', 'content':"No cacheid found"}), mimetype="text/plain")
    
    proxyurl = settings.HTTPPROXYURL + "/Page?" + cacheid
    result = { 'proxyurl':proxyurl, 'cacheid':cacheid }
    try:
        fin = urllib2.urlopen(proxyurl)
        result["mimetype"] = fin.headers.type
        if fin.headers.maintype == 'text' or fin.headers.type == "application/json":
            result['content'] = convtounicode(fin.read())
        else:
            result['content'] = base64.encodestring(fin.read())
            result['encoding'] = "base64"
    except urllib2.URLError, e: 
        result['type'] = 'exception'
        result['content'] = str(e)
    
    return HttpResponse(json.dumps(result), mimetype="text/plain")



