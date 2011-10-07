from fabric.api import *

import getpass
import sys

# TODO:
# Cron:
#    env.cron_version = "dev"
#    env.cron_version = "www"
#    env.cron_version = "umls"

# Full deploy that restarts everything too
# Cron jobs are a mess
# Pull puppet on kippax, then do everything else
# Use "local" to run Django tests automatically
# Use "local" to run Selenium tests.
# Use "local" to merge code from default into stable for you


# Example use:
# fab dev webserver
# fab dev webserver:buildout=no
# fab dev webserver:buildout=no --hide=running,stdout

###########################################################################
# Server configurations

env.server_lookup = {
    ('webserver', 'dev'): ['yelland.scraperwiki.com'], 
    ('webserver', 'live'): ['rush.scraperwiki.com:7822'],

    ('webstore', 'dev'): ['ewloe.scraperwiki.com'], 
    ('webstore', 'live'): ['burbage.scraperwiki.com:7822'],

    ('firebox', 'dev'): ['kippax.scraperwiki.com'], 
    ('firebox', 'live'): ['horsell.scraperwiki.com:7822'],
}
# This is slightly magic - we want to generate the host list from the pair of
# the service deployed (e.g. firebox) and the flock (e.g. live). This gets
# fabric to call the function do_server_lookup to do that work -
# do_server_lookup in turn uses the env.server_lookup dictionary above
env.roledefs = {
    'webserver' : lambda: do_server_lookup('webserver'),
    'webstore' : lambda: do_server_lookup('webstore'),
    'firebox' : lambda: do_server_lookup('firebox')
}

env.path = '/var/www/scraperwiki'
env.activate = env.path + '/bin/activate'
env.user = 'scraperdeploy'
env.name = getpass.getuser()

# Call one of these tasks first to set which flock of servers you're working on
@task
def dev():
    '''Call first to deploy to development servers'''
    env.flock = 'dev'
    env.branch = 'default'
    env.email_deploy = False

@task
def live():
    '''Call first to deploy to live servers'''
    env.flock = 'live'
    env.branch = 'stable'
    env.email_deploy = "deploy@scraperwiki.com"

###########################################################################
# Helpers

def do_server_lookup(task):
    if not 'flock' in env:
        raise Exception("specify which flock (e.g. dev/live) first")
    hosts = env.server_lookup[(task, env.flock)]
    print "server_lookup: deploying '%s' on flock '%s', hosts: %s" % (task, env.flock, hosts)
    return hosts

def run_in_virtualenv(command):
    temp = 'cd %s; source ' % env.path
    return run(temp + env.activate + '&&' + command)

def run_buildout():
    run_in_virtualenv('buildout -N -qq')

def django_db_migrate():
    run_in_virtualenv('cd web; python manage.py syncdb --verbosity=0')
    run_in_virtualenv('cd web; python manage.py migrate --verbosity=0')

def update_js_cache_revision():
    """
    Put the current HG revision in a file so that Django can use it to avoid caching JS files
    """
    run_in_virtualenv("hg identify | awk '{print $1}' > web/revision.txt")

def install_cron():
    run('crontab %(path)s/cron/crontab.%(cron_version)s' % env)
    sudo('crontab %(path)s/cron/crontab-root.%(cron_version)s' % env)

def restart_webserver():
    "Restart the web server"
    sudo('apache2ctl graceful')

def deploy_done():
    if not env.email_deploy:
        return

    message = """From: ScraperWiki <developers@scraperwiki.com>
Subject: New Scraperwiki Deployment to %(cron_version)s (deployed by %(user)s)

%(user)s deployed

Old revision: %(old_revision)s
New revision: %(new_revision)s

""" % {
        'cron_version' : env.cron_version,
        'user' : env.name,
        'old_revision': env.old_revision,
        'new_revision': env.new_revision,
        }
    sudo("""echo "%s" | sendmail deploy@scraperwiki.com """ % message)

def code_pull():
    with cd(env.path):
        env.old_revision = run("hg identify")
        run("hg pull --quiet; hg update --quiet -C %(branch)s" % env)
        env.new_revision = run("hg identify")
        if env.old_revision == env.new_revision:
            print "WARNING: code hasn't changed since last update"

###########################################################################
# Tasks

@task
@roles('webserver')
def webserver(buildout='yes'):
    '''Deploys Django web application, runs schema migrations, clears caches,
kicks webserver so it starts using new code. 

buildout=no, stops it updating buildout which can be slow'''

    if buildout not in ['yes','no']:
        raise Exception("buildout must be yes or no")

    code_pull()

    if buildout == 'yes':
        run_buildout()
    django_db_migrate()
    update_js_cache_revision()
    restart_webserver()   

    deploy_done()


@task
@roles('webstore')
def webstore(buildout='yes'):
    '''Deploys webstore SQL database. XXX currently doesn't restart any daemons.

buildout=no, stops it updating buildout which can be slow'''

    if buildout not in ['yes','no']:
        raise Exception("buildout must be yes or no")

    code_pull()

    if buildout == 'yes':
        run_buildout()
    deploy_done()


@task
@roles('firebox')
def firebox():
    '''Deploys LXC script sandbox executor. XXX currently doesn't restart any daemons'''
    code_pull()

    deploy_done()

'''
@task
def setup():
    # this really ought to make sure it checks out default vs. stable
    raise Exception("not implemented, really old broken code")

    sudo('hg clone file:///home/scraperwiki/scraperwiki %(path)s' % env)        
    sudo('chown -R %(fab_user)s %(path)s' % env)
    sudo('cd %(path)s; easy_install virtualenv' % env)
    run('hg clone %(web_path)s %(path)s' % env, fail='ignore')
    run('cd %(path)s; virtualenv --no-site-packages .' % env)
    run_in_virtualenv('easy_install pip')

    deploy()
'''

'''
@task
def run_puppet():
    sudo("puppetd --no-daemonize --onetime --debug")        
    
@task
def deploy():
    code_pull()
    
    if env.buildout:
        buildout()
                
    install_cron()

    if env.email_deploy:
        email(old_revision, new_revision)

    print "Deploy successful"
    print "Old revision = %s" % old_revision
    print "New revision = %s" % new_revision

@task
def test():
    if env.host != "dev.scraperwiki.com":
        print "Testing can only be done on the dev machine"
    else:
        run_in_virtualenv('cd web; python manage.py test')

'''
