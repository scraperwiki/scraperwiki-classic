import os
import re
from subprocess import call
from StringIO import StringIO
from django.core.management import setup_environ
import settings
setup_environ(settings)

from django.contrib.auth.models import User
from frontend.models import UserProfile
from codewiki.models import Code, UserCodeRole, Scraper, Vault, scraper_search_query

def ssh_attach(ssh_agent_cmd):
    sh_cmds=os.popen(ssh_agent_cmd).readlines()
    print sh_cmds
    for sh_line in sh_cmds:
        matches=re.search("(\S+)\=(\S+)\;", sh_line)
        if matches != None:
            os.environ[matches.group(1)]=matches.group(2)

cfg = \
"""repo gitolite-admin
\tRW+\t=\tgit_acl_updater
"""

os.chdir("/tmp")
ssh_attach("/usr/bin/ssh-agent")
call(["ssh-add", "/home/chris/.ssh/git_acl_updater"])
call(["/usr/bin/git", "clone", "git@localhost:gitolite-admin"]) #check for success
os.chdir("/tmp/gitolite-admin")

for user in User.objects.all():
    try: 
        ssh_key = user.get_profile().ssh_public_key
        owned_scrapers = scraper_search_query(user, None) \
                .filter(usercoderole__user=user)
        for scraper in owned_scrapers:
            cfg += "repo %s\n" % (scraper.short_name)
            cfg += "\tRW\t=\t%s\n" % (user.username)
            #maybe also copy files if there's no repo yet?

        keyfile = open("keydir/%s@default.pub" % user.username, "w")
        keyfile.write(ssh_key)
        keyfile.close()

    except UserProfile.DoesNotExist:
        next

print cfg

f = open("conf/gitolite.conf", "w")
f.write(cfg)
f.close()

call(["git", "add", "."])
call(["git", "commit", "-am", "'automated generation'"])
call(["git", "push"])

os.chdir("/tmp")
call(["rm", "-rf", "gitolite-admin"])
