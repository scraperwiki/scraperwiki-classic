import os,sys

import ConfigParser
import urllib2
import memcache
import OpenSSL

from twisted.web import proxy, http
from twisted.internet import defer, threads, ssl
from twisted.python import log
deferred = threads.deferToThread.__get__

USAGE = " [--uid=#] [--gid=#] [--allowAll] [--varDir=dir] [--config=file] [--useCache] [--mode=H|S|P]"
cache_client = None

@deferred
def do_ident():
    """
    Code taken from original proxy for identifying the user
    
    (scraperID, runID, cache, blocked, )
    """
    scraperID = None
    runID     = None
    cache     = 0
    allowed = []
    blocked = []
    
    ident = None
    rem = ['localhost', 9000]
#        rem       = self.connection.getpeername()
#        loc       = self.connection.getsockname()
#        port = loc[1]
    port = 80
    sys.stdout.flush()
    for attempt in range(5):
        try:
            ident = urllib2.urlopen('http://%s:9001/Ident?%s:%s' % (rem[0], rem[1], port)).read()
            if ident.strip() != "":
                break
            print 'Ident call %d failed' % attempt
        except:
            pass

    if not ident:
        #raise TypeError('')
        return (0, 0, True, [],)

    for line in string.split (ident, '\n'):
        if line == '' :
            continue
        key, value = string.split (line, '=')
        if key == 'runid' :
            runID     = value
            continue
        if key == 'scraperid' :
            scraperID = value
            continue
        if key == 'allow'  :
            allowed.append (value)
            continue
        if key == 'block'  :
            blocked.append (value)
            continue
        if key == 'option' :
            name, opt = string.split (value, ':')
            if name == 'webcache' : cache = int(opt)        
    
    return (scraperID, runID, cache, blocked, )


class ScraperProxyClient(proxy.ProxyClient):

    headers = {}
    buffer = ''
    first = False
    
    def handleHeader( self, key, value ):
#        print self.father.scraperId, self.father.runId, self.father.cache
#        self.buffer = self.buffer + '%s=%s\r\n' % (key,value,)
        proxy.ProxyClient.handleHeader(self, key, value)
        
    def handleResponsePart(self, data):
#        if self.first:
#            self.first = False
#            self.buffer = self.buffer + '\r\n'
#        self.buffer = self.buffer + data
        proxy.ProxyClient.handleResponsePart(self,data)
        
    def handleResponseEnd(self):
#        if cache_client and self.father.cache and self.father.key:
#            cache_client.set(self.father.key, self.buffer)
        proxy.ProxyClient.handleResponseEnd(self)
        
        
class ScraperProxyClientFactory(proxy.ProxyClientFactory):
    
    def buildProtocol(self, addr):
        print 'buildProtocol'
        client = proxy.ProxyClientFactory.buildProtocol(self, addr)
        client.__class__ = ScraperProxyClient
        return client
        
    def startedConnecting(self, connector):
        print 'startedConnecting'
        proxy.ProxyClientFactory.startedConnecting(self, connector)
        

class ScraperProxyRequest(proxy.ProxyRequest):
    protocols = { 'http': ScraperProxyClientFactory,  'https': ScraperProxyClientFactory }

    def __init__(self, *args):
        proxy.ProxyRequest.__init__(self, *args)
        
    def process(self):
        # TODO Process self.uri to see if we are allowed to access it
        # We probably want to do an ident with the current controller and 
        # probably a notify as well.  Once we know we can carry on then 
        # we should
        print 'request.process()'
        do_ident().addCallback(self.ident_complete).addErrback(self.ident_failed)
                
    def ident_failed(self, failure):                
        print failure
                
    def ident_complete(self, tup):
        # Do something with the tuple arguments and make sure we can access it from
        # the client above
        # tup = (scraperID, runID, cache, blocked, )
        import hashlib
        
        self.scraperId = tup[0]
        self.runId     = tup[1]
        self.cache     = tup[2]
        self.key       = None
        
        if self.cache:
            self.key = hashlib.sha224( self.uri ).hexdigest()
            page = cache_client.get(self.key)            
            if page:
                print 'Returning ', page, 'from cache'
                proxy.ProxyRequest.write(self, page)              
                proxy.ProxyRequest.finish(self)    
                return 
            else:
                print 'Not in cache'
                
        proxy.ProxyRequest.process(self)
            
        
    def connection_lost(self):
        print 'Connection lost'
            
        
class ScraperProxy(proxy.Proxy):
    
    def __init__(self):
        proxy.Proxy.__init__(self)
        
    def requestFactory(self, *args):
        return ScraperProxyRequest(*args)
    
        
class ScraperProxyFactory(http.HTTPFactory):
    
    def __init__(self):
        http.HTTPFactory.__init__(self)
        
    def buildProtocol(self, addr):
        protocol = ScraperProxy()
        return protocol
        

class ScraperContextFactory(ssl.ContextFactory):        
    def getContext(self):
        import os
        
        ctx = OpenSSL.SSL.Context(OpenSSL.SSL.SSLv23_METHOD)
        fpem = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'server.pem')
        print 'Creating SSL context from ', fpem
        ctx.use_privatekey_file (fpem)
        ctx.use_certificate_file(fpem)
        return ctx



def get_parsed_arguments():        
    """
    Gets and processes the command line arguments to this process returning
    the options object and args as a tuple.
    """
    from optparse import OptionParser
    
    parser = OptionParser(usage=USAGE)
    parser.add_option("-u", "--uid", type='int', dest="uid",
                       help="Run as supplied uid")
    parser.add_option("-g", "--gid", type='int', dest="gid",
                       help="Run as supplied gid")
    parser.add_option("-v", "--varDir", dest="varDir",
                        help="Specify var directory")
    parser.add_option("-c", "--config", dest="config",
                        help="Specify config file")
                        
    parser.add_option("-x", "--useCache", action="store_false", dest="useCache", default=False,
                  help="Force use of cache")
    parser.add_option("-a", "--allowAll", action="store_false", dest="allowAll", default=False,
                  help="Allow all urls")
    
    return parser.parse_args()
        
        
        
if __name__ == '__main__':
    from twisted.internet import reactor

    (options, args) = get_parsed_arguments()

    # Following only needed when not using twistd
    log.startLogging(sys.stdout)

    # Set uid and gid if they were provided as command line arguments            
    if options.uid:
        log.msg('Switching to UID %s' % options.uid)
        os.setreuid (options.uid, options.uid)

    if options.gid:
        log.msg('Switching to GID %s' % options.gid)
        os.setregid (options.gid, options.gid)

    # Log startup arguments
    log.msg("Starting with var directory: %s" % options.varDir )
    log.msg("Reading config file: %s" % (options.config or 'uml.cfg',) )
    log.msg("Force cache: %s" % options.useCache )
    log.msg("Allow all: %s" % options.allowAll )    

    # Load config file
    config = ConfigParser.ConfigParser()
    try:
        config.readfp( open( options.config or 'uml.cfg') )
    except IOError, ioe: 
        log.err(ioe, "Trying to read log file")
        sys.exit()

    # Fix hard-coded name
    cache_hosts = config.get('httpproxy', 'cache')
    if cache_hosts:
        log.msg("Cache is at %s" % cache_hosts )    
        cache_client = memcache.Client( cache_hosts.split(',') )        
    
    # Don't believe we need both, the single proxy should be able to handle either
    port = int( config.get('httpproxy', 'port') )
    secure_port = int( config.get('httpsproxy', 'port') )
    
    log.msg("Starting server on port ", port)
    px = ScraperProxyFactory()
    reactor.listenTCP( port, px)
# Temporarily disabled
#    reactor.listenSSL( secure_port, px, ScraperContextFactory())    
    reactor.run()