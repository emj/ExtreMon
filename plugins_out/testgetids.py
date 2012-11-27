#!/usr/bin/env python2
import urllib2,json

def getIDs(screenNames):
  try:
    stream=urllib2.urlopen("https://api.twitter.com/1/users/"
                 "lookup.json?screen_name=%s"
                 "&include_entities=false" % (','.join(screenNames)))
    return dict((profile['screen_name'],profile['id_str']) for profile in json.load(stream))
  except urllib2.HTTPError:
    return []

print getIDs(['fedtron,BartHanssens'])


