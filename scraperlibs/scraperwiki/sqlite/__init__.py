import re
import datetime
from scraperwiki.datastore import request
import scraperwiki.console


def strunc(v, t):
    if not t or len(v) < t:
        return v
    return "%s..." % v[:t]

def strencode_trunc(v, t):
    if type(v) == str:
        v = v.decode('utf-8')
    else:
        v = unicode(v)

    try:
        return strunc(v, t).encode('utf-8')
    except:
        return "---"


def ifsencode_trunc(v, t):
    if type(v) in [int, float]:
        return v
    return strencode_trunc(v, t)




def sqlitecommand(command, val1=None, val2=None, verbose=1):
    ds = DataStore(None)
    result = ds.request({"maincommand":'sqlitecommand', "command":command, "val1":val1, "val2":val2})
    if "error" in result:
        raise databaseexception(result)
    if "status" not in result and "keys" not in result:
        raise Exception("possible signal timeout: "+str(result))
    
    # list type for second field in message dump
    if verbose:
        if val2 == None:
            lval2 = [ ]
        elif type(val2) in [tuple, list]:
            lval2 = [ ifsencode_trunc(v, 50)  for v in val2 ]
        elif command == "attach":
            lval2 = [ val2 ]
        elif type(val2) == dict:
            lval2 = [ ifsencode_trunc(v, 50)  for v in val2.values() ]
        else:
            lval2 = [ str(val2) ]
        scraperwiki.console.logSqliteCall(command, val1, lval2)
    
    return result
    

class SqliteError(Exception):  pass
class NoSuchTableSqliteError(SqliteError):  pass

def databaseexception(errmap):
    mess = errmap["error"]
    for k, v in errmap.items():
        if k != "error":
            mess = "%s; %s:%s" % (mess, k, v)
    
    if re.match('sqlite3.Error: no such table:', mess):
        return NoSuchTableSqliteError(mess)
    return SqliteError(mess)
        



def save(unique_keys, data, table_name="swdata", verbose=2):
    if unique_keys != None and type(unique_keys) not in [ list, tuple ]:
        return { "error":'unique_keys must a list or tuple', "unique_keys_type":str(type(unique_keys)) }

    def convdata(unique_keys, scraper_data):
        if unique_keys:
            for key in unique_keys:
                if key not in scraper_data:
                    return { "error":'unique_keys must be a subset of data', "bad_key":key }
                if scraper_data[key] == None:
                    return { "error":'unique_key value should not be None', "bad_key":key }
        jdata = { }
        for key, value in scraper_data.items():
            if not key:
                return { "error": 'key must not be blank', "bad_key":key }
            if type(key) not in [unicode, str]:
                return { "error":'key must be string type', "bad_key":key }
            if not re.match("[a-zA-Z0-9_\- ]+$", key):
                return { "error":'key must be simple text', "bad_key":key }
            
            if type(value) in [datetime.datetime, datetime.date]:
                value = value.isoformat()
            elif value == None:
                pass
            elif isinstance(value, SqliteError):
                return {"error": str(value)}
            elif type(value) == str:
                try:
                    value = value.decode("utf-8")
                except:
                    return {"error": "Binary strings must be utf-8 encoded"}
            elif type(value) not in [int, bool, float, unicode, str]:
                value = unicode(value)
            jdata[key] = value
        return jdata
            

    if type(data) == dict:
        rjdata = convdata(unique_keys, data)
        if rjdata.get("error"):
            return rjdata
    else:
        rjdata = [ ]
        for ldata in data:
            ljdata = convdata(unique_keys, ldata)
            if ljdata.get("error"):
                return ljdata
            rjdata.append(ljdata)
    result = request({"maincommand":'save_sqlite', "unique_keys":unique_keys, "data":rjdata, "swdatatblname":table_name})

    if "error" in result:
        raise databaseexception(result)

    if verbose >= 2:
        pdata = {}
        if type(data) == dict:
            for key, value in data.items():
                pdata[strencode_trunc(key, 50)] = strencode_trunc(value, 50)
        elif data:
            for key, value in data[0].items():
                pdata[strencode_trunc(key, 50)] = strencode_trunc(value, 50)
            pdata["number_records"] = "Number Records: %d" % len(data)
            
        scraperwiki.console.logScrapedData(pdata)
    return result



def attach(name, asname=None, verbose=1):
    return sqlitecommand("attach", name, asname, verbose)
    
def execute(val1, val2=None, verbose=1):
    if val2 is not None and "?" in val1 and type(val2) not in [list, tuple]:
        val2 = [val2]
    return sqlitecommand("execute", val1, val2, verbose)

def commit(verbose=1):
    return sqlitecommand("commit", None, None, verbose)

def select(val1, val2=None, verbose=1):
    if val2 is not None and "?" in val1 and type(val2) not in [list, tuple]:
        val2 = [val2]
    result = sqlitecommand("execute", "select %s" % val1, val2, verbose)
    return [ dict(zip(result["keys"], d))  for d in result["data"] ]

def show_tables(dbname=""):
    name = "sqlite_master"
    if dbname:
        name = "`%s`.%s" % (dbname, name)
    result = sqlitecommand("execute", "select tbl_name, sql from %s where type='table'" % name)
    return dict(result["data"])


def table_info(name):
    sname = name.split(".")
    if len(sname) == 2:
        result = sqlitecommand("execute", "PRAGMA %s.table_info(`%s`)" % tuple(sname))
    else:
        result = sqlitecommand("execute", "PRAGMA table_info(`%s`)" % name)
    return [ dict(zip(result["keys"], d))  for d in result["data"] ]


            # also needs to handle the types better (could save json and datetime objects handily
def save_var(name, value, verbose=2):
    data = {"name":name, "value_blob":value, "type":type(value).__name__}
    save(unique_keys=["name"], data=data, table_name="swvariables", verbose=verbose)

def get_var(name, default=None, verbose=2):
    try:
        result = sqlitecommand("execute", "select value_blob, type from swvariables where name=?", (name,), verbose)
    except NoSuchTableSqliteError, e:
        return default
    data = result.get("data")
    if not data:
        return default
    return data[0][0]

    

    