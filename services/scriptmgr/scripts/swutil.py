#!/usr/bin/env python
# swutil.py

"""Utility functions.  For code that supports the running of
Python scripts.
"""

import inspect
import re
import sys
import traceback
import urllib
from urllib2 import HTTPError


def as_unicode(text):
    """Try quite hard to convert text to unicode."""
    try:    return unicode(text)
    except UnicodeDecodeError:     pass
    try:    return unicode(text, encoding='utf8')
    except UnicodeDecodeError:     pass
    try:    return unicode(text, encoding='latin1')
    except UnicodeDecodeError:     pass
    return unicode(text, errors='replace')

def formatvalue(value):
    r = repr(value)
    if len(r) < 1000:
        return '=%s' % r
    return "=%s ...\n\n*** %d characters omitted ***\n\n %s" % (r[:700:], len(r) - 900, r[-200:])

def getExceptionTraceback(code):
    """Convert traceback (from sys.exc_info()) to a dict that
    contains the raw data.  The dict is intended to be coded as
    JSON and then sent to scriptmgr/twister/editor.  *code* is
    the code that was executing, as a single string.
    """

    exc_type, exc_value, exc_traceback = sys.exc_info()
    codelines = code.splitlines()
    stackdump = [ ]
        # outer level is the controller, 
        # second level is the module call.
        # anything beyond is within a function.  
        # Move the function call description up one level to the correct place
    
    for frame, file, linenumber, func, lines, index in inspect.getinnerframes(exc_traceback, context=1)[1:]:  # skip outer frame
        stackentry = { "linenumber":linenumber, "file":file }
        if func != "<module>":
            try:
                args, varargs, varkw, locals = inspect.getargvalues(frame)
                funcargs = inspect.formatargvalues(args, varargs, varkw, locals, formatvalue=formatvalue)
                stackentry["furtherlinetext"] = "%s(%s)" % (func, funcargs)  # double brackets to make it stand out
            except:
                # TODO: Do something useful here.
                pass
                
        if file == "<string>" and 0 <= linenumber - 1 < len(codelines):
            # have to do this as context=1 doesn't work (it doesn't give me anything in lines)
            stackentry["linetext"] = codelines[linenumber - 1]
        else:
            # XXX bit of a hack to show the line number in third party libraries
            stackentry["file"] += ":" + str(linenumber)
 
        if stackdump and stackdump[-1] == stackentry:
            duplicates += 1
        else:
            if stackdump:
                stackdump[-1]["duplicates"] = duplicates
            stackdump.append(stackentry)
            duplicates = 0
        
        if file.startswith("/usr/lib/python"):
            break
        
    if stackdump:
        stackdump[-1]["duplicates"] = duplicates
    
    if exc_type in [ SyntaxError, IndentationError ]:
        stackentry = {"linenumber":exc_value.lineno,
          "file":exc_value.filename, "offset":exc_value.offset,
          "duplicates":1}
        if (stackentry["file"] == "<string>" and
          0 <= stackentry["linenumber"] - 1 < len(codelines)):
            # Can't seem to recover the text from the SyntaxError
            # object, though it is in its repr.
            stackentry["linetext"] = as_unicode(codelines[stackentry["linenumber"] - 1])
        stackentry["furtherlinetext"] = exc_value.msg
        stackdump.append(stackentry)
        
    # truncate the list
    if len(stackdump) > 50:
        stackdump = stackdump[:20] + [{"furtherlinetext": "%d entries omitted" % (len(stackdump)-40) }] + stackdump[-20:]
    
    result = { "message_type": 'exception',
      "exceptiondescription": "%s: %s" % (exc_value.__class__.__name__, as_unicode(str(exc_value))),
      "stackdump": stackdump }
    
    #raise IOError('http error', 403, 'Scraperwiki blocked access to "http://tits.ru/".  Click <a href="/whitelist/?url=http%3A//tits.ru/">here</a> for details.', <httplib.HTTPMessage instance at 0x84c318c>)
    if exc_type == HTTPError and exc_value.code == 403:
        mblockaccess = re.search('Scraperwiki blocked access to "(.*)"', exc_value.msg)
        if mblockaccess:
            result["blockedurl"] = urllib.unquote(mblockaccess.group(1))
            result["blockedurlquoted"] = mblockaccess.group(1)
    
    return result
