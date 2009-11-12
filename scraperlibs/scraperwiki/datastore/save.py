# encoding: utf-8
import hashlib
import os
import datetime
import connection
try:
  import json
except:
  import simplejson as json

import cgi

def save(unique_keys, data=None, **kwargs):
  """
  Save function
  """
  
  if not data:
    data = {}
  if isinstance(data,list):
    if kwargs:
      raise TypeError("""
        \tIncorrect use of arguments when saving multipul rows.  
        \tLook up 'saving multipul rows' in the suport pages for more information.
        """)
    ids = []
    for row in data:
      ids.append(__save_row(unique_keys,row))
    return ids
  else:
    return __save_row(unique_keys, data, kwargs)

    
def __create_unique(unique_keys, data):
  data_set = set(data)
  unique_keys = set(unique_keys)
  
  if not unique_keys.issubset(data_set):
      raise ValueError("""
        key(s) [%s] not in data.
        `unique_keys` must only contain keys that exist in `data`.
        See the support pages for more information
        """ % ','.join( ['"%s"' % k for k in unique_keys.difference(data)] ))

  unique_values = [str(data[v]) for v in unique_keys]
  return hashlib.md5("%s" % ("≈≈≈".join(unique_values))).hexdigest()


def __save_row(unique_keys, data, kwargs):
  """
  Takes a single row and saves it.
  """
  DUMMY_RUN = True
  if os.environ.has_key('SCRAPER_GUID'):
    scraper_id = os.environ['SCRAPER_GUID']
    DUMMY_RUN = False
  
  # Add all the kwargs in to data
  data.update(kwargs)

  # Create a unique hash
  unique_hash = __create_unique(unique_keys, data)
  
  indexed_rows = ['date', 'latlng']
  
  for k in indexed_rows:
    if k not in data.keys():
      data[k] = None
  item = {'unique_hash' : unique_hash}
  for k,v in data.items():
    if k in indexed_rows:
      item[k] = v
    if v is None:
      del data[k]
  
  
  new_item_id = None    
  if not DUMMY_RUN:
    conn = connection.Connection()
    c = conn.connect()
    if c.execute("SELECT item_id FROM items WHERE unique_hash='%s'" % unique_hash):  
      item_id = c.fetchone()
      c.execute("DELETE FROM kv WHERE item_id=%s" % item_id[0])
      c.execute("DELETE FROM items WHERE unique_hash=%s", (unique_hash,))
  
    c.execute("UPDATE sequences SET id=LAST_INSERT_ID(id+1);")
    c.execute("SELECT LAST_INSERT_ID();")
    new_item_id = c.fetchone()[0]
    item['item_id'] = new_item_id
 
    
    # for date scraped
    now = datetime.datetime.now()
    str_now = now.strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute("INSERT INTO `items` (`scraper_id`,`item_id`,`unique_hash`,`date`, `latlng`, `date_scraped`) \
      VALUES (%s, %s, %s, %s, %s, %s);", (scraper_id, item['item_id'], unique_hash, item['date'], item['latlng'],str_now))
  
    for k,v in data.items():  
      c.execute("""INSERT INTO `kv` (`item_id`,`key`,`value`) VALUES (%s, %s, %s);""", (item['item_id'], k,v))
    
      # clean for printing to the console

  for k,v in data.items():  
    data[k] = cgi.escape(str(v))
    
    
  
  print '<scraperwiki:message type="data">%s' % json.dumps(data)
  return new_item_id


  
  
  
if __name__ == "__main__":
  
  # Test one: Save a single row with a data dict passed
  unique_keys = ['message_id',]
  data = {
  'message_id' : '1',
  'message' : 'This is an example',
  'sender' : 'Sym',
  }
  save(unique_keys, data, date='16/10/2009', latlng=[52.38431,1.11112])

  
  # test two: Save a single row without a data dict, just named arguments
  print save(['id'], id=3, name='Sym', something_else='foo')
  
  # test three: Save many rows
  unique_keys = ['message_id']
  data = [
  {
  'message_id' : '1',
  'message' : 'This is an example',
  'sender' : 'Sym',
  },
  {
  'message_id' : '2',
  'message' : 'This is an example reply',
  'sender' : 'Someone Else',
  }
  ]
  print save(unique_keys, data)
  
  
  