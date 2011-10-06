from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse, Http404, HttpResponseNotFound, HttpResponseForbidden
from django.template.loader import render_to_string
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail, mail_admins

import smtplib

from django.conf import settings

from codewiki import models, runsockettotwister
import frontend
import urllib
import subprocess
import re
import base64
import cgi
import ConfigParser
import datetime

import logging
logger = logging


try:                import json
except ImportError: import simplejson as json

config = ConfigParser.ConfigParser()
config.readfp(open(settings.CONFIGFILE))

def MakeRunner(request, scraper, code):
    runner_path = "%s/runner.py" % settings.FIREBOX_PATH
    failed = False

    urlquerystring = request.META["QUERY_STRING"]
    
    # append post values to the query string (so we can consume them experimentally)
    # we could also be passing in the sets of scraper environment variables in this way too
    # though maybe we need a generalized version of the --urlquery= that sets an environment variables explicitly
    # the bottleneck appears to be the runner.py command line instantiation
    # (POST is a django.http.QueryDict which destroys information about the order of the incoming parameters) 
    if list(request.POST):
        qsl = cgi.parse_qsl(urlquerystring)
        qsl.extend(request.POST.items())
        urlquerystring = urllib.urlencode(qsl)
        print "sending in new querystring:", urlquerystring
    
    
    args = [ runner_path.encode('utf8') ]
    args.append('--guid=%s' % scraper.guid.encode('utf8'))
    args.append('--language=%s' % scraper.language.lower().encode('utf8'))
    args.append('--name=%s' % scraper.short_name.encode('utf8'))
    args.append('--cpulimit=80')
    args.append('--urlquery=%s' % urlquerystring.encode('utf8'))
    
    runner = subprocess.Popen(args, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    runner.stdin.write(code.encode('utf8'))
    
    runner.stdin.close()
    return runner



def scraperwikitag(scraper, html, panepresent):
    mswpane = re.search('(?i)<div[^>]*?id="scraperwikipane"[^>/]*(?:/\s*>|>.*?</div>)', html)
    if mswpane:
        startend = (mswpane.start(0), mswpane.end(0))
        mclass = re.search('class="([^"]*)"', mswpane.group(0))
        if mclass:
            paneversion = mclass.group(1)
        else:
            paneversion = "version-2"
        if panepresent != None:
            panepresent["scraperwikipane"].append(mswpane)
    
    elif panepresent == None:  # case where no div#scraperwikipane is found and it's all there (we're not streaming the html out using php)
        # have to insert the pane -- favour doing it after the body tag if it exists
        mbody = re.search("(?i)<body.*?>", html)
        if mbody:
            startend = (mbody.end(0), mbody.end(0))
        else:
            startend = (0, 0) # (0,0)
        paneversion = "version-2"
    
    else:
        if len(panepresent["firstfivelines"]) < 5 and re.search("\S", html):
            panepresent["firstfivelines"].append(html)
        return html
    
    
    urlbase = settings.MAIN_URL
    urlscraperoverview = urlbase + reverse('code_overview', args=[scraper.wiki_type, scraper.short_name])
    urlscraperedit = urlbase + reverse('editor_edit', args=[scraper.wiki_type, scraper.short_name])
    urlpoweredlogo = settings.MEDIA_URL + "images/powered.png";
    
    swdivstyle = "border:thin #aaf solid; display:block; position:fixed; top:0px; right:0px; background:#eef; margin: 0em; padding: 6pt; font-size: 10pt; z-index: 8675309; "
    swlinkstyle = "width:167px; height:17px; margin:0; padding: 0; border-style: none; "

    if paneversion == "version-1":
        swpane = [ '<div id="scraperwikipane" style="%s;">' % swdivstyle ]
        swpane.append('<a href="%s" id="scraperwikipane" style="%s"><img style="border-style: none" src="%s" alt="Powered by ScraperWiki"></a>' % (urlbase, swlinkstyle, urlpoweredlogo))
        swpane.append('<br><a href="%s" title="Go to overview page">%s</a>' % (urlscraperoverview, scraper.title))
        swpane.append(' (<a href="%s" title="Edit source code for this view">edit</a>)' % (urlscraperedit))
        swpane.append('</div>')
    
    else:
        swpane = [ '<div id="scraperwikipane" style="%s;">' % swdivstyle ]
        swpane.append('<a href="%s" id="scraperwikipane" style="%s"><img style="border-style: none" src="%s" alt="Powered by ScraperWiki"></a>' % (urlscraperoverview, swlinkstyle, urlpoweredlogo))
        swpane.append('</div>')

    return "%s%s%s" % (html[:startend[0]], "".join(swpane), html[startend[1]:])


def rpcexecute(request, short_name, revision=None):
    try:
        scraper = models.Code.objects.get(short_name=short_name)
    except models.Code.DoesNotExist:
        return HttpResponseNotFound(render_to_string('404.html', {'heading':'Not found', 'body':"Sorry, this view does not exist"}, context_instance=RequestContext(request)))
    if not scraper.actionauthorized(request.user, "rpcexecute"):
        return HttpResponseForbidden(render_to_string('404.html', scraper.authorizationfailedmessage(request.user, "rpcexecute"), context_instance=RequestContext(request)))
    
    if revision:
        try: 
            revision = int(revision)
        except ValueError: 
            revision = None
    
    # quick case where we have PHP with no PHP code in it (it's all pure HTML)
    if scraper.language in ['html', 'php', 'javascript']:
        code = scraper.saved_code(revision)
        if scraper.language == 'php' and not re.search('<\?', code):
            return HttpResponse(scraperwikitag(scraper, code, None))
        if scraper.language == 'html':
            return HttpResponse(scraperwikitag(scraper, code, None))
        if scraper.language == 'javascript':
            return HttpResponse(code, mimetype='application/javascript')

    if revision == None:
        revision = -1
    
    # run it the socket method for staff members who can handle being broken
#    if request.user.is_staff:
    runnerstream = runsockettotwister.RunnerSocket()
    runnerstream.runview(request.user, scraper, revision, request.META["QUERY_STRING"])
#    else:
#        runner = MakeRunner(request, scraper, code)
#        runnerstream = runner.stdout

    # we build the response on the fly in case we get a contentheader value before anything happens
    response = None 
    panepresent = {"scraperwikipane":[], "firstfivelines":[]}
    contenttypesettings = { }
    for line in runnerstream:
        if line == "":
            continue
            
        try:
            message = json.loads(line)
        except:
            pass
            
        # Need to log the message here in debug mode so we can track down the
        # 'no output for some unknown reason'. Appears to be missing console 
        # messages from the lxc/uml and has been happening for a while.
        
        if message['message_type'] == "console":
            if not response:
                response = HttpResponse()

            if message.get('encoding') == 'base64':
                response.write(base64.decodestring(message["content"]))
            else:
                response.write(scraperwikitag(scraper, message["content"], panepresent))
        
        elif message['message_type'] == 'exception':
            if not response:
                response = HttpResponse()
            
            response.write("<h3>%s</h3>\n" % str(message.get("exceptiondescription")).replace("<", "&lt;"))
            for stackentry in message["stackdump"]:
                response.write("<h3>%s</h3>\n" % str(stackentry).replace("<", "&lt;"))

        
        # parameter values have been borrowed from http://php.net/manual/en/function.header.php
        elif message['message_type'] == "httpresponseheader":
            contenttypesettings[message['headerkey']] = message['headervalue']
            if message['headerkey'] == 'Content-Type':
                if not response:
                    response = HttpResponse(mimetype=message['headervalue'])
                else:
                    response.write("<h3>Error: httpresponseheader('%s', '%s') called after start of stream</h3>" % (message['headerkey'], message['headervalue']))
                    
            elif message['headerkey'] == 'Content-Disposition':
                if not response:
                    response = HttpResponse()
                response['Content-Disposition'] = message['headervalue']
            
            elif message['headerkey'] == 'Location':
                if not response:
                    response = HttpResponseRedirect(message['headervalue'])
                else:
                    response.write("<h3>Error: httpresponseheader('%s', '%s') called after start of stream</h3>" % (message['headerkey'], message['headervalue']))
            
            else:
                if not response:
                    response = HttpResponse()
                response.write("<h3>Error: httpresponseheader(headerkey='%s', '%s'); headerkey can only have values 'Content-Type' or 'Content-Disposition'</h3>" % (message['headerkey'], message['headervalue']))
            
                    
    if not response:
        response = HttpResponse('No output received from view.')
        
    # now decide about inserting the powered by scraperwiki panel (avoid doing it on json)
    # print [response['Content-Type']]  default is DEFAULT_CONTENT_TYPE, comes out as 'text/html; charset=utf-8'
    
    # How about 
    if 'Content-Type' in response  and 'text/html' in response['Content-Type']:
        response.write(scraperwikitag(scraper, '<div id="scraperwikipane" class="version-2"/>', panepresent))
    return response
            

# liable to hang if UMLs not operative
def testactiveumls(n):
    result = [ ]
    code = "from subprocess import Popen, PIPE\nprint Popen(['hostname'], stdout=PIPE).communicate()[0]"
    
    runner_path = "%s/runner.py" % settings.FIREBOX_PATH
    args = [runner_path, '--language=python', '--cpulimit=80']
    
    for i in range(n):
        runner = subprocess.Popen(args, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        runner.stdin.write(code)
        runner.stdin.close()
        
        lns = [ ]
        for line in runner.stdout:
            message = json.loads(line)
            if message['message_type'] == "console":
                if message.get('message_sub_type') != 'consolestatus':
                    lns.append(message['content'].strip())
            elif message['message_type'] == "executionstatus":
                pass
            else:
                lns.append(line)
        result.append('\n'.join(lns))
    return result


# this form is protected by the django key known to twister, so does not need to be obstructed by the csrf machinery
@csrf_exempt
def twistermakesrunevent(request):
    try:
        return Dtwistermakesrunevent(request)
    except Exception, e:
        logger.error("twistermakesruneventerror: %s" % (str(e)))
        mail_admins(subject="twistermakesruneventerror: %s" % (str(e)[:50]), message=(str(e)))
    return HttpResponse("no done %s" % str(e))
        

def Dtwistermakesrunevent(request):
    if request.POST.get("django_key") != config.get('twister', 'djangokey'):
        logger.error("twister wrong djangokey")
        return HttpResponse("no access")
    run_id = request.POST.get("run_id")
    if not run_id:
        logger.error("twisterbad run_id")
        return HttpResponse("bad run_id - %s" % (request.POST,) )
        
    matchingevents = models.ScraperRunEvent.objects.filter(run_id=run_id)
    if not matchingevents:
        event = models.ScraperRunEvent()
        event.scraper = models.Scraper.objects.get(short_name=request.POST.get("scrapername"))
        clientnumber = request.POST.get("clientnumber")  # would be used to kill it
        #event.pid = "client# "+ request.POST.get("clientnumber") # only applies when this runner is active
        event.pid = (100000000+int(clientnumber)) # only applies when this runner is active
        event.run_id = run_id               # set by execution status
        event.run_started = datetime.datetime.now()   # reset by execution status

        # set the last_run field so we don't select this one again for the overdue scrapers
        # this field should't exist because we should use the runobjects isntead, 
        # where we can work from a far richer report on what has been happening.
        event.scraper.last_run = datetime.datetime.now()
        event.scraper.save()
    else:
        event = matchingevents[0]

    # standard updates
    event.output = request.POST.get("output")
    event.records_produced = int(request.POST.get("records_produced"))
    event.pages_scraped = int(request.POST.get("pages_scraped"))
    event.first_url_scraped = request.POST.get("first_url_scraped", "")
    event.exception_message = request.POST.get("exception_message", "")
    event.run_ended = datetime.datetime.now()   # last update time

    # run finished case
    if request.POST.get("exitstatus"):
        event.pid = -1  # disable the running state of the event
        
        event.scraper.status = request.POST.get("exitstatus") == "exceptionmessage" and "sick" or "ok"
        event.scraper.last_run = datetime.datetime.now()
        event.scraper.update_meta() # enable if views ever have metadata that needs updating each refresh
        event.scraper.save()

        # report the pages that were scraped
        jdomainscrapes = request.POST.get("domainscrapes")
        domainscrapes = json.loads(jdomainscrapes)
        for netloc, vals in domainscrapes.items():
            domainscrape = models.DomainScrape(scraper_run_event=event, domain=netloc)
            domainscrape.pages_scraped = vals["pages_scraped"]
            domainscrape.bytes_scraped = vals["bytes_scraped"]
            domainscrape.save()

    event.save()

    # Send email if this is an email scraper
    if request.POST.get("exitstatus"):
        emailers = event.scraper.users.filter(usercoderole__role='email')
        if emailers.count() > 0:
            subject, message = getemailtext(event)
            if event.scraper.status == 'ok':
                if message:  # no email if blank
                    for user in emailers:
                        try:
                            send_mail(subject=subject, message=message, from_email=settings.EMAIL_FROM, recipient_list=[user.email], fail_silently=False)
                        except smtplib.SMTPException, e:
                            logger.error("emailer failed %s %s" % (str(user), str(e)))
                            mail_admins(subject="email failed to send: %s" % (str(user)), message=str(e))
            else:
                logger.error("emailer failed %s %s" % (str(user), str(e)))
                mail_admins(subject="SICK EMAILER: %s" % subject, message=message)

    return HttpResponse("done")


    # maybe detect the subject title here
def getemailtext(event):
    message = event.output
    message = re.sub("(?:^|\n)EXECUTIONSTATUS:.*", "", message).strip()
    
    msubject = re.search("(?:^|\n)EMAILSUBJECT:(.*)", message)
    if msubject:
        subject = msubject.group(1)    # snip out the subject
        message = "%s%s" % (message[:msubject.start(0)], message[msubject.end(0):])
    else:
        subject = 'Your ScraperWiki Email - %s' % event.scraper.short_name
    
    return subject, message
