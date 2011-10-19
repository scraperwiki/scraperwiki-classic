"""
Datastore.py

A server that handles incoming connections to various Sqlite databases that 
are stored on disk and access over a network.
"""
from twisted.internet import reactor, protocol
from twisted.protocols import basic

from datalib import SQLiteDatabase
import re, uuid, urlparse
import json

class DatastoreProtocol(basic.LineReceiver):
    """
    """
    
    def __init__(self, *args, **kwargs):
        """
        Initialise the local attributes that we want
        """
        self.have_read_header = False
        self.headers = {}
        self.params = None
        self.action = None
        self.db = None
        
        
    def process(self, obj):
        """ 
        Process the provided JSON obj (has already been converted to JSON)
        and make sure the response is sent with self.sendLine()
        """
        if self.db is None:
            # We don't have a database yet so this must be the first message
            firstmessage = {"status":"good"}
            # Are these passed in parameters? Check self.params?
            firstmessage["short_name"] = '' # short_name
            firstmessage["runID"]      = '' #runID
            firstmessage["dataauth"]   = '' #dataauth
            self.sendLine( json.dumps(firstmessage)  )
            
            db = datalib.SQLiteDatabase(self, config.get('dataproxy', 'resourcedir'), self.short_name, self.dataauth, self.runID, self.attachables)            
        else:
            # Decide what to do based on the command in obj
            pass
        
    def lineReceived(self, line):
        """
        Handles incoming lines of text (correctly separated) these,
        after the http headers will be JSON which expect a JSON response
        """
        # See if we have read all of the HTTP header yet.
        # Store what we need to store for this client 
        # connection
        print line
        
        self.factory.connection_count += 1
        if not self.have_read_header and line.strip() == '':
            self.have_read_header = True
            return
            
        if self.have_read_header:
            print self.action
            print self.params
            print self.headers
            
            try:
                obj = json.loads(line)
                self.process( obj )                
            except Exception, e:
                print e
                
        else:
            if self.params is None:
                self.parse_params(line)
            else:
                k,v = line.split(':')
                self.headers[k.strip()] = v.strip()


    def connectionLost(self, reason):
        """
        Called when the connection was lost, we should clean up the DB here
        by closing the connection we have to it.
        """
        if self.db:
            self.db.close()
            self.db = None


    def parse_params(self, line):
        """
        Parse the GET request and store the parameters we received.
        """
        self.params = {}        
        m = re.match('GET /(.*) HTTP/(\d+).(\d+)', line)
        if not m:
            return
            
        qs = m.groups(0)[0]
        if '?' in qs:
            self.action = qs[ :qs.find('?') ]            
            qs = qs[ qs.find('?')+1: ]
        else:
            self.action = qs
            qs = None
    
        if qs:
            self.params.update( dict( [ p.split('=') for p in qs.split('&') ] ) )

            
class DatastoreFactory( protocol.ServerFactory ):
    protocol = DatastoreProtocol
    
    connection_count = 0
    
    
if __name__ == '__main__':
    reactor.listenTCP( 2112, DatastoreFactory())
    reactor.run()