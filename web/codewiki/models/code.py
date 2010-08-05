import datetime
import time

from django.db import models
from django.contrib.auth.models import User
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
import settings

import codewiki.managers.scraper
from codewiki import managers
from django.db.models.signals import post_save
from registration.signals import user_registered

import tagging
from frontend import models as frontendmodels

import codewiki.vc

try:
    import json
except:
    import simplejson as json

from django.core.mail import send_mail

LANGUAGES = (
    ('Python', 'Python'),
    ('PHP', 'PHP'),
    ('Ruby', 'Ruby'),
    ('HTML', 'HTML'),
)

class Code(models.Model):
    """
        A 'Scraper' is the definition of all versions of a particular scraper
        that are classed as being the same, though changed over time as the
        data required changes and the page being scraped changes, thus
        breaking a particular version.
    """
    title             = models.CharField(max_length=100, 
                                        null=False, 
                                        blank=False, 
                                        verbose_name='Scraper Title', 
                                        default='Untitled Scraper')
    short_name        = models.CharField(max_length=50)
    source            = models.CharField(max_length=100, blank=True)
    description       = models.TextField(blank=True)
    revision          = models.CharField(max_length=100, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)
    disabled          = models.BooleanField()
    deleted           = models.BooleanField()
    status            = models.CharField(max_length=10, blank=True)
    users             = models.ManyToManyField(User, through='UserCodeRole')
    guid              = models.CharField(max_length=1000)
    published         = models.BooleanField(default=False)
    first_published_at   = models.DateTimeField(null=True, blank=True)
    featured          = models.BooleanField(default=False)
    istutorial        = models.BooleanField(default=False)
    isstartup         = models.BooleanField(default=False)
    language          = models.CharField(max_length=32, choices=LANGUAGES, default='Python')
    objects = managers.scraper.ScraperManager()
    unfiltered = models.Manager()

    def __unicode__(self):
        return self.short_name
    
    def buildfromfirsttitle(self):
        assert not self.short_name and not self.guid
        import hashlib
        self.short_name = util.SlugifyUniquely(self.title, Scraper, slugfield='short_name', instance=self)
        self.created_at = datetime.datetime.today()  # perhaps this should be moved out to the draft scraper
        self.guid = hashlib.md5("%s" % ("**@@@".join([self.short_name, str(time.mktime(self.created_at.timetuple()))]))).hexdigest()
     
    def owner(self):
        if self.pk:
            owner = self.users.filter(UserCodeRole__role='owner')
            if len(owner) >= 1:
                return owner[0]
        return None

    def contributors(self):
        if self.pk:
            contributors = self.users.filter(UserCodeRole__role='editor')
        return contributors
    
    def followers(self):
        if self.pk:
            followers = self.users.filter(UserCodeRole__role='follow')
        return followers

    def add_user_role(self, user, role='owner'):
        """
        Method to add a user as either an editor or an owner to a scraper/view.
  
        - `user`: a django.contrib.auth.User object
        - `role`: String, either 'owner' or 'editor'
        
        Valid role are:
          * "owner"
          * "editor"
          * "follow"
        
        """

        valid_roles = ['owner', 'editor', 'follow']
        if role not in valid_roles:
            raise ValueError("""
              %s is not a valid role.  Valid roles are:\n
              %s
              """ % (role, ", ".join(valid_roles)))

        #check if role exists before adding 
        u, created = UserCodeRole.objects.get_or_create(user=user, 
                                                           scraper=self, 
                                                           role=role)

    def unfollow(self, user):
        """
        Deliberately not making this generic, as you can't stop being an owner
        or editor
        """
        UserCodeRole.objects.filter(scraper=self, 
                                       user=user, 
                                       role='follow').delete()
        return True

    def followers(self):
        return self.users.filter(UserCodeRole__role='follow')

    def is_published(self):
        return self.status == 'Published'

    # currently, the only editor we have is the owner of the scraper.
    def editors(self):
        return (self.owner(),)
            
    # this functions to go
    def saved_code(self):
        return vc.MercurialInterface().getstatus(self)["code"]

        
    @models.permalink
    def get_absolute_url(self):
        return ('scraper_overview', [self.short_name])

    def is_good(self):
        # don't know how goodness is going to be defined yet.
        return True

    # update scraper meta data (lines of code etc)    
    def update_meta(self):
        # if publishing for the first time set the first published date
        if self.published and self.first_published_at == None:
            self.first_published_at = datetime.datetime.today()

    def content_type(self):
        return ContentType.objects.get(app_label="scraper", model="Scraper")

    def get_metadata(self, name, default=None):
        try:
            return json.loads(self.scrapermetadata_set.get(name=name).value)
        except:
            return default


class UserCodeEditing(models.Model):
    """
    Updated by Twisted to state which scrapers/views are being editing at this moment
    """
    user    = models.ForeignKey(User, null=True)
    code = models.ForeignKey(Code, null=True)
    editingsince = models.DateTimeField(blank=True, null=True)
    runningsince = models.DateTimeField(blank=True, null=True)
    closedsince  = models.DateTimeField(blank=True, null=True)
    twisterclientnumber = models.IntegerField(default=-1)
    twisterscraperpriority = models.IntegerField(default=0)   # >0 another client has priority on this scraper

    def __unicode__(self):
        return "Editing: Scraper_id: %s -> User: %s (%d)" % (self.code, self.user, self.twisterclientnumber)
        

class UserCodeRole(models.Model):
    """
    This embodies the roles associated between particular users and scrapers/views.
    This should be used to store all user/code relationships, ownership,
    editorship, whatever.
    """
    user    = models.ForeignKey(User)
    code = models.ForeignKey(Code)
    role    = models.CharField(max_length=100)

    def __unicode__(self):
        return "Scraper_id: %s -> User: %s (%s)" % \
                                        (self.code, self.user, self.role)
                                        
class CodeCommitEvent(models.Model):
    revision = models.IntegerField()

    def __unicode__(self):
        return unicode(self.revision)

    @models.permalink
    def get_absolute_url(self):
        return ('commit_event', [self.id])
                                        