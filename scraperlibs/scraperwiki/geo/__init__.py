from osgb import eastnorth_to_osgb, osgb_to_lonlat, lonlat_to_eastnorth
from geo_helper import turn_osgb36_into_wgs84, turn_eastingnorthing_into_osgb36, turn_eastingnorthing_into_osie36, turn_osie36_into_wgs84

import urllib
import re
import sys
sys.path.append('..')
from scraperwiki.datastore import connection

try:
  import json
except:
  import simplejson as json

'''standardized to wgs84 (if possible)'''

def gb_postcode_to_latlng(postcode):
    '''Convert postcode to latlng using google api'''
    return GBPostcode(postcode).latlng

def os_easting_northing_to_latlng(easting, northing, grid='GB'):
    '''Convert easting, northing to latlng assuming altitude 200m'''
    result = Point()
    if grid == 'GB':
        oscoord = turn_eastingnorthing_into_osgb36(easting, northing)
        result.latlng = turn_osgb36_into_wgs84(oscoord[0], oscoord[1], 200)
    elif grid == 'IE':
        oscoord = turn_eastingnorthing_into_osie36 (easting, northing)
        result.latlng = turn_osie36_into_wgs84(oscoord[0], oscoord[1], 200)
    return result.latlng

def extract_gb_postcode(string):
    postcode = False
    matches = re.findall(r'[A-Z][A-Z]?[0-9][A-Z0-9]? ?[0-9][ABDEFGHJLNPQRSTUWXYZ]{2}\b', string, re.IGNORECASE)

    if len(matches) > 0:
        postcode = matches[0]

    return postcode

class Point:
    def __init__(self):    
        self.latlng = []

# implement above user functions through classes with their conversion outputs
class GBPostcode:   # (geopoint)

    def __init__(self, postcode):
        self.coordinatesystem = "GBPostcode"
        self.postcode = postcode
        self.latlng = None
        try:

            #open connection
            conn = connection.Connection()
            c = conn.cursor()
            sql = " select AsText(location) from postcode_lookup where postcode = %s"
            c.execute(sql, (postcode,))            
            result = c.fetchone()[0]
            if result:
                self.latlng = result.replace('POINT(', '').replace(')', '').split(' ')
                self.latlng = [float(self.latlng[0]), float(self.latlng[1])]
        except:
            self.latlng = None
            
    def __str__(self):
        return "GBPostcode('%s')" % self.postcode
        

        
