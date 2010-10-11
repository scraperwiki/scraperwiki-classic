#!/bin/sh -
"exec" "python" "-O" "$0" "$@"

"""
This script is the interface between the UML/firebox set up and the frontend 
Orbited TCP socket.  

When a connection is made RunnerProtocol listens for data coming from the 
client.  This can be anything


class RunnerProtocol(protocol.Protocol):
class RunnerFactory(protocol.ServerFactory):
    protocol = RunnerProtocol

class spawnRunner(protocol.ProcessProtocol)

"""

import sys
import os
import signal
import time
from optparse import OptionParser
import ConfigParser
import urllib2
import urllib      #  do some asynchronous calls
import datetime

varDir = './var'

# 'json' is only included in python2.6.  For previous versions you need to
# Install siplejson manually.
try:
  import json
except:
  import simplejson as json

from zope.interface import implements

from twisted.internet import protocol, utils, reactor, task
from twisted.protocols.basic import LineOnlyReceiver

# for calling back to the scrapers/twister/status
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer
from twisted.internet.defer import succeed

agent = Agent(reactor)

# the comma is added into format_message and LineOnlyReceiver because lines may be batched and 
# they are decoded in editor.js by attempting to evaluate the json string '['+receiveddata+']'

# perhaps in-line this
def format_message(content, message_type='console'):
    return json.dumps({'message_type' : message_type, 'content' : content})

# the messages of the type given by format_message also get generated by firestarter/runner.py
# and are passed through lineReceived.  Look there fore further formatting information.
# things like exception parsing is done all the way in the controller.py

# I think this class is only for chunking into lines
# see http://twistedmatrix.com/documents/8.2.0/api/twisted.protocols.basic.LineOnlyReceiver.htm

class LocalLineOnlyReceiver(LineOnlyReceiver):
    def lineReceived(self, line):
        if line != "":
            self.client.writeall(line)

# the streaming data from the runner gets chunked into lines so that twister can 
# insert its own messages into the same transport stream
# it would be more efficient to stream it over completely, because editor.js 
# is capable of finding the line feeds itself.
# for now it's separated by commas. (can see the advantage of string.splitlines leaving the trailing linefeeds)

class spawnRunner(protocol.ProcessProtocol):
    def __init__(self, client, code):
        self.client = client
        self.code = code
        self.LineOnlyReceiver = LocalLineOnlyReceiver()
        self.LineOnlyReceiver.transport = self.client.transport
        self.LineOnlyReceiver.client = self.client
        self.LineOnlyReceiver.delimiter = "\r\n"  # this delimeter is inserted in runner.py line 61
        self.LineOnlyReceiver.MAX_LENGTH = 1000000000000000000000
        self._buffer = ""
    

    def connectionMade(self):
        print "Starting run"
        self.transport.write(self.code)
        self.transport.closeStdin()
        # moved into runner.py where the runID is allocated and known
        #startmessage = json.dumps({'message_type' : "startingrun", 'content' : "starting run"})
        #startmessage = format_message("starting run", message_type="startingrun")  # adds a comma
        #self.client.writeall(startmessage)
        
    # see http://twistedmatrix.com/documents/10.0.0/api/twisted.internet.protocol.ProcessProtocol.html
    # reroutes this into LineOnlyReceiver to chunk into lines
    def outReceived(self, data):
        print "out", self.LineOnlyReceiver.client.guid, data
        self.LineOnlyReceiver.dataReceived(data)  # this batches it up into line feeds
        # (if we intercepted this data we could potentially get at the runID)

    def processEnded(self, data):
        self.client.running = False
        self.client.writeall(json.dumps({'message_type':'executionstatus', 'content':'runfinished'}))
        self.client.factory.notifytwisterstatus()
        print "run process ended ", data




# There's one of these 'clients' per editor window open.  All connecting to same factory
class RunnerProtocol(protocol.Protocol):
     
    def __init__(self):
        # Set if a run is currently taking place, to make sure we don't run 
        # more than one scraper at a time.
        self.running = False
        self.guid = ""
        self.scrapername = ""
        self.isstaff = False
        self.username = ""
        self.userrealname = ""
        self.chatname = ""
        self.clientnumber = -1         # number for whole operation of twisted
        self.scrapereditornumber = -1  # number out of all people editing a particular scraper
        self.earliesteditor = datetime.datetime.now()  # used to group together everything in one editing session

    def connectionMade(self):
        self.factory.clientConnectionMade(self)
        # we don't know what scraper they've actually opened until we get the dataReceived
        
    
    def dataReceived(self, data):
        try:
            parsed_data = json.loads(data)
            
            # data uploaded when a new connection is made from the editor
            if parsed_data['command'] == 'connection_open':
                self.connectionopen(parsed_data)
            
            elif parsed_data['command'] == 'saved':
                line = json.dumps({'message_type' : "saved", 'content' : "%s saved" % self.chatname})
                otherline = json.dumps({'message_type' : "othersaved", 'content' : "%s saved" % self.chatname})
                self.writeall(line, otherline)
            
            elif parsed_data['command'] == 'run' and not self.running:
                if 'code' in parsed_data:
                    self.runcode(parsed_data)
                else:
                    raise ValueError('++?????++ Out of Cheese Error. Redo From Start: `code` to run not specified')
            
            elif parsed_data['command'] == "kill":
                # Kill the running process (or other if staff)
                if self.running:
                    self.kill_run()
                
                # someone who didn't start it going hits kill
                elif self.isstaff:
                    for client in self.factory.clients:
                        if client.guid == self.guid and client.running:
                            client.kill_run()

            elif parsed_data['command'] == 'chat':
                message = "%s: %s" % (self.chatname, parsed_data['text'])
                
                if self.guid:
                    self.factory.sendchatmessage(self.guid, message, None)
                
                # unsaved scraper case (just talking to self)
                else:   
                    self.write(format_message(message, message_type='chat'))  # write it back to itself
        
        
        except Exception, e:
            self.transport.write(format_message("Command not valid (%s)  %s " % (e, data)))

    
    def write(self, line, formatted=True):
        self.transport.write(line+",\r\n")  # note the comma added to the end for json parsing when strung together
    
    
    def connectionLost(self, reason):
        if self.running:
            self.kill_run(reason='connection lost')
        if self.guid:
            self.factory.sendchatmessage(self.guid, "%s leaves" % self.chatname, self)
        self.factory.clientConnectionLost(self)
        self.factory.notifytwisterstatus()

    def writeall(self, line, otherline=""):
        self.write(line)  
        
        if not otherline:
            otherline = line
        
        # send any destination output to any staff who are watching
        if self.guid:
            for client in self.factory.clients:
                if client.guid == self.guid and client != self and client.isstaff:
                    client.write(otherline)  
    
    def kill_run(self, reason=''):
        msg = 'Script cancelled'
        if reason:
            msg += " (%s)" % reason
        self.writeall(json.dumps({'message_type':'executionstatus', 'content':'killsignal', 'message':msg}))
        print msg
        try:      # should kill using the new dispatcher call
            os.kill(self.running.pid, signal.SIGKILL)
        except:
            pass

    def runcode(self, parsed_data):
        code = parsed_data['code']
        code = code.encode('utf8')
        
        # these could all be fetched from self
        guid = parsed_data['guid']
        scraperlanguage = parsed_data.get('language', 'python')
        scrapername = parsed_data.get('scrapername', '')
        scraperlanguage = parsed_data.get('language', '')
        urlquery = parsed_data.get('urlquery', '')
        
        assert guid == self.guid
        args = ['./firestarter/runner.py']
        args.append('--guid=%s' % guid)
        args.append('--language=%s' % scraperlanguage)
        args.append('--name=%s' % scrapername)
        args.append('--urlquery=%s' % urlquery)
        
        # args must be an ancoded string, not a unicode object
        args = [i.encode('utf8') for i in args]

        print "./firestarter/runner.py: %s" % args

        # from here we should somehow get the runid
        self.running = reactor.spawnProcess(spawnRunner(self, code), './firestarter/runner.py', args, env={'PYTHON_EGG_CACHE' : '/tmp'})

        message = "%s runs scraper" % self.chatname
        if self.guid:
            self.factory.sendchatmessage(self.guid, message, None)
        else:   
            self.write(format_message(message, message_type='chat'))  # write it back to itself

    def connectionopen(self, parsed_data):
        self.guid = parsed_data.get('guid', '')
        self.username = parsed_data.get('username', '')
        self.userrealname = parsed_data.get('userrealname', self.username)
        self.scrapername = parsed_data.get('scrapername', '')
        self.scraperlanguage = parsed_data.get('language', '')
        self.isstaff = (parsed_data.get('isstaff') == "yes")
        self.isumlmonitoring = (parsed_data.get('umlmonitoring') == "yes")
        
        if self.username:
            self.chatname = self.userrealname or self.username
        else:
            self.chatname = "Anonymous%d" % self.factory.anonymouscount
            self.factory.anonymouscount += 1
            
        self.factory.clientConnectionRegistered(self)  # this will cause a notifyEditorClients to be called for everyone on this scraper
        self.factory.notifytwisterstatus()
        

class StringProducer(object):
    """
    http://twistedmatrix.com/documents/10.1.0/web/howto/client.html
    """
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass


class EditorsOnOneScraper:
    def __init__(self, guid):
        self.guid = guid
        self.sessionstarts = datetime.datetime.now()  # replaces earliesteditor
        self.anonymouseditors = [ ]
        self.usereditors = [ ]  # list of lists of clients
        self.editinguser = ""
        
    def AddClient(self, client):
        assert client.guid == self.guid
        client.earliesteditor = self.sessionstarts
        if client.username:
            bnomatch = True
            for userclients in self.usereditors:
                if userclients[0].username == client.username:
                    userclients.append(client)  # new window by same user
                    bnomatch = False  # this signal is case for use of an else statement on the for
                    break
            if not self.usereditors:
                self.editinguser = client.username
            else:
                assert self.editinguser
            if bnomatch:
                self.usereditors.append([client])
        else:
            self.anonymouseditors.append(client)
        self.notifyEditorClients("%s enters" % client.chatname)
        
    def RemoveClient(self, client):
        assert client.guid == self.guid
        if client.username:
            for i in range(len(self.usereditors)):
                if self.usereditors[i][0].username == client.username:
                    self.usereditors[i].remove(client)  
                    if not self.usereditors[i]:
                        del self.usereditors[i]
                        
                        # fairly inelegant logic to handle passing editing user on to next person
                        if self.editinguser == client.username:
                            if self.usereditors:
                                self.editinguser = self.usereditors[0][0].username
                            else:
                                self.editinguser = ""
                    break
            assert False
        else:
            self.anonymouseditors.remove(client)
        self.notifyEditorClients("%s leaves" % client.chatname)
        return self.usereditors or self.anonymouseditors
        
        
    def notifyEditorClients(self, message):
        editorstatusdata = {'message_type':"editorstatus", 'earliesteditor':self.sessionstarts.isoformat(), "editinguser":self.editinguser, "cansave":False}; 
        editorstatusdata["loggedineditors"] = [ userclients[0].username  for userclients in self.usereditors ]
        editorstatusdata["nanonymouseditors"] = len(self.anonymouseditors)
        editorstatusdata["message"] = message
        for client in self.anonymouseditors:
            editorstatusdata["chatname"] = client.chatname
            client.write(json.dumps(editorstatusdata)); 
        for editorlist in self.usereditors:
            editorstatusdata["cansave"] = (editorlist[0].username == self.editinguser)
            for client in editorlist:
                editorstatusdata["chatname"] = client.chatname
                client.write(json.dumps(editorstatusdata)) 
    
    def Dcountclients(self):
        return len(self.anonymouseditors) + sum([len(editorlist)  for editorlist in self.usereditors])


class RunnerFactory(protocol.ServerFactory):
    protocol = RunnerProtocol
    
    def __init__(self):
        self.clients = [ ]   # all clients
        self.clientcount = 0
        self.anonymouscount = 1
        self.announcecount = 0
        
        self.umlmonitoringclients = [ ]
        self.draftscraperclients = [ ]
        self.guidclientmap = { }  # maps to EditorsOnOneScraper objects
        
        # set the visible heartbeat going
        #self.lc = task.LoopingCall(self.announce)
        #self.lc.start(10)

        self.m_conf        = ConfigParser.ConfigParser()
        config = '/var/www/scraperwiki/uml/uml.cfg'
        self.m_conf.readfp (open(config))
        self.twisterstatusurl = self.m_conf.get('twister', 'statusurl')
        

    # every 10 seconds sends out a quiet poll
    def announce(self):
        self.announcecount += 1
        for client in self.clients:
            res = []
            for c in self.clients:
                res.append(c == client and "T" or "-")
                res.append(c.running and "R" or ".")
            client.write(format_message("%d c %d clients, running:%s" % (self.announcecount, len(self.clients), "".join(res)), message_type='chat'))


    # could get rid of this and replace everywhere with writeall
    def sendchatmessage(self, guid, message, nomessageclient):
        for client in self.clients:
            if client.guid == guid and client != nomessageclient and client.isstaff:
                client.write(format_message(message, message_type='chat'))
        
    # should make a more detailed monitoring timeline message that we then send to everyone
    def notifyMonitoringClients(self, message):
        for client in self.umlmonitoringclients:
            client.write(format_message(message, message_type='chat'))
    

    def clientConnectionMade(self, client):
        client.clientnumber = self.clientcount
        self.clients.append(client)
        self.clientcount += 1
        # will call next function when some actual data gets sent

    def clientConnectionRegistered(self, client):
        if client.isumlmonitoring:
            self.umlmonitoringclients.append(client)
            self.notifyMonitoringClients("%s enters" % client.chatname)
            
        elif not client.guid:   # draft scraper type
            editorstatusdata = {'message_type':"editorstatus", "cansave":True, "loggedineditors":[], "nanonymouseditors":1, 
                                "editinguser":client.username, "chatname":client.chatname, "message":"Draft scraper connection"} 
            client.write(json.dumps(editorstatusdata)); 
            self.draftscraperclients.append(client)
        
        else:
            if client.guid not in self.guidclientmap:
                self.guidclientmap[client.guid] = EditorsOnOneScraper(client.guid)
            self.guidclientmap[client.guid].AddClient(client)

        # check that all clients are accounted for
        assert len(self.clients) == len(self.umlmonitoringclients) + len(self.draftscraperclients) + sum([eoos.Dcountclients()  for eoos in self.guidclientmap.values()])
            
    
    def clientConnectionLost(self, client):
        self.clients.remove(client)  # main list
        
        if client.isumlmonitoring:
            self.umlmonitoringclients.remove(client)

        elif not client.guid:
            self.draftscraperclients.remove(client)
            
        elif (client.guid in self.guidclientmap):   
            if not self.guidclientmap[client.guid].RemoveClient(client):
                del self.guidclientmap[client.guid]
        else:
            pass  # shouldn't happen
        
        # check that all clients are accounted for
        assert len(self.clients) == len(self.umlmonitoringclients) + len(self.draftscraperclients) + sum([eoos.Dcountclients()  for eoos in self.guidclientmap.values()])
    
    
    # this might be deprecated when we can poll twister directly for the state of activity in some kind of ajax or iframe call
    def notifytwisterstatus(self):
        clientlist = [ ]
        for client in self.clients:
            clientdata = { "clientnumber":client.clientnumber, "guid":client.guid, 
                           "username":client.username, "running":bool(client.running), 
                           "scrapereditornumber":client.scrapereditornumber, 
                           "earliesteditor":client.earliesteditor.isoformat() }
            clientlist.append(clientdata)
            
        data = { "value": json.dumps({'message_type' : "currentstatus", 'clientlist':clientlist}) }
        
        d = agent.request('POST', self.twisterstatusurl, Headers({'User-Agent': ['Scraperwiki Twisted']}), StringProducer(urllib.urlencode(data)))
        d.addErrback(lambda e:  sys.stdout.write("notifytwisterstatus failed to get through\n"))  
        
        

def execute (port) :
    
    runnerfactory = RunnerFactory()
    reactor.listenTCP(port, runnerfactory)
    reactor.callLater(1, runnerfactory.notifytwisterstatus)
    reactor.run()   # this function never returns


def sigTerm (signum, frame) :

    try    : os.kill (child, signal.SIGTERM)
    except : pass
    try    : os.remove (varDir + '/run/twister.pid')
    except : pass
    sys.exit (1)


if __name__ == "__main__":
    
    parser = OptionParser()

    parser.add_option("-p", "--port", dest="port", action="store", type='int',
                      help="Port that receives connections from orbited.",  
                      default=9010, metavar="port no (int)")
    parser.add_option("-v", "--varDir", dest="varDir", action="store", type='string',
                      help="/var directory for logging and pid files",  
                      default="/var", metavar="/var directory (string)")
    parser.add_option("-s", "--subproc", dest="subproc", action="store_true",
                      help="run in subprocess",  
                      default=False, metavar="run in subprocess")
    parser.add_option("-d", "--daemon", dest="daemon", action="store_true",
                      help="run as daemon",  
                      default=False, metavar="run as daemon")
    parser.add_option("-u", "--uid", dest="uid", action="store", type='int',
                      help="run as specified user",  
                      default=None, metavar="run as specified user")
    parser.add_option("-g", "--gid", dest="gid", action="store", type='int',
                      help="run as specified group",  
                      default=None, metavar="run as specified group")

    (options, args) = parser.parse_args()
    varDir = options.varDir

    #  If executing in daemon mode then fork and detatch from the
    #  controlling terminal. Basically this is the fork-setsid-fork
    #  sequence.
    #
    if options.daemon :

        if os.fork() == 0 :
            os .setsid()
            sys.stdin  = open ('/dev/null')
            sys.stdout = open (options.varDir + '/log/twister', 'w', 0)
            sys.stderr = sys.stdout
            if os.fork() == 0 :
                ppid = os.getppid()
                while ppid != 1 :
                    time.sleep (1)
                    ppid = os.getppid()
            else :
                os._exit (0)
        else :
            os.wait()
            sys.exit (1)

        pf = open (options.varDir + '/run/twister.pid', 'w')
        pf.write  ('%d\n' % os.getpid())
        pf.close  ()

    if options.gid is not None : os.setregid (options.gid, options.gid)
    if options.uid is not None : os.setreuid (options.uid, options.uid)
    
    #  If running in subproc mode then the server executes as a child
    #  process. The parent simply loops on the death of the child and
    #  recreates it in the event that it croaks.
    #
    if options.subproc :

        signal.signal (signal.SIGTERM, sigTerm)

        while True :

            child = os.fork()
            if child == 0 :
                time.sleep (1)
                break

            sys.stdout.write("Forked subprocess: %d\n" % child)
            sys.stdout.flush()
    
            os.wait()

    execute (options.port)
