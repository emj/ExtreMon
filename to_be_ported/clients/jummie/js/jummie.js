//
//    ExtreMon Project
//    Copyright (C) 2009-2013 Frank Marien
//    frank@apsu.be
//  
//    This file is part of ExtreMon.
//    
//    ExtreMon is free software: you can redistribute it and/or modify
//    it under the terms of the GNU General Public License as published by
//    the Free Software Foundation, either version 3 of the License, or
//   (at your option) any later version.
//
//    ExtreMon is distributed in the hope that it will be useful,
//    but WITHOUT ANY WARRANTY; without even the implied warranty of
//    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//    GNU General Public License for more details.
//
//    You should have received a copy of the GNU General Public License
//    along with ExtreMon.  If not, see <http://www.gnu.org/licenses/>.
//
//    Jummie JS Client by Koen De Causmaecker
//    koendc@gmail.com
//

// fixes issues with dots and other special characters in the id.
function jq(myid) { 
	return myid.replace(/(:|\.)/g,'\\$1');
}
function getParameterByName( name )
{
  name = name.replace(/[\[]/,"\\\[").replace(/[\]]/,"\\\]");
  var regexS = "[\\?&]"+name+"=([^&#]*)";
  var regex = new RegExp( regexS );
  var results = regex.exec( window.location.href );
  if( results == null )
   	return "";
  else
   	return decodeURIComponent(results[1].replace(/\+/g, " "));
}
