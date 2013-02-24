#!/bin/bash

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

export PYTHONPATH=$PYTHONPATH:/opt/extremon

/opt/extremon/clients/extremon2graphite.py | /opt/graphite/bin/carbon-client.py localhost:2004:a
