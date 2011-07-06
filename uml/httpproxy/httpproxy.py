import os,sys

import ConfigParser

import memcache

from twisted.web import proxy, http
from twisted.python import log


USAGE = " [--uid=#] [--gid=#] [--allowAll] [--varDir=dir] [--config=file] [--useCache] [--mode=H|S|P]"

class ScraperProxyClient(proxy.ProxyClient):

    def handleHeader( self, key, value ):
        proxy.ProxyClient.handleHeader(self, key, value)
        
    def handleResponsePart(self, data):
        proxy.ProxyClient.handleResponsePart(self,data)
        
    def handleResponseEnd(self):
        proxy.ProxyClient.handleResponseEnd(self)
        
        
class ScraperProxyClientFactory(proxy.ProxyClientFactory):
    
    def buildProtocol(self, addr):
        client = proxy.ProxyClientFactory.buildProtocol(self, addr)
        client.__class__ = ScraperProxyClient
        return client


class ScraperProxyRequest(proxy.ProxyRequest):
    protocols = { 'http': ScraperProxyClientFactory }

    def __init__(self, *args):
        proxy.ProxyRequest.__init__(self, *args)
        
    def process(self):
        # TODO Process self.uri to see if we are allowed to access it
        # We probably want to do an ident with the current controller and 
        # probably a notify as well.  Once we know we can carry on then 
        # we should
        proxy.ProxyRequest.process(self)
        
        
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
    
    port = int( config.get('httpproxy', 'port') )
    # Don't believe we need both, the single proxy should be able to handle either
    secure_port = int( config.get('httpsproxy', 'port') )
    
    log.msg("Starting server on port ", port)
    px = ScraperProxyFactory()
    reactor.listenTCP( port, px)
    reactor.listenTCP( secure_port, px)    
    reactor.run()