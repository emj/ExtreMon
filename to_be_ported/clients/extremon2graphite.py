#!/usr/bin/python3

#
#    ExtreMon Project
#    Copyright (C) 2009-2013 Frank Marien
#    frank@apsu.be
#  
#    This file is part of ExtreMon.
#    
#    ExtreMon is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    ExtreMon is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with ExtreMon.  If not, see <http://www.gnu.org/licenses/>.
#
#    Graphite Adapter by Koen De Causmaecker
#    koendc@gmail.com
#

import                  re;
from extremon   import  CauldronReceiver

class Extremon2Graphite:
        def __init__(self):
                self.timestamp = 0

        def handle_shuttle(self,data):
                removeItems = set()
                for (label,value) in data:
                        if re.match(".*\.dispatcher\.timestamp$", label):
                                self.timestamp = value
                                removeItems.add((label,value))
                        if re.match(".*\.timestamp$", label):
                                self.timestamp = value
                                removeItems.add((label,value))
                        if re.match(".*\.sequence$", label):
                                removeItems.add((label,value))
                        if re.match(".*\.comment$", label):
                                removeItems.add((label,value))
                for item in removeItems:
                        data.remove(item)
                for (label,value) in data:
                        print("%s %s %s" % (label,value, self.timestamp))

if __name__=='__main__':
        source=CauldronReceiver(Extremon2Graphite(),('224.0.0.1',1249))
        source.receive_forever()
