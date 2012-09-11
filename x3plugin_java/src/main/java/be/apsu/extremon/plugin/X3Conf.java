/*   ExtreMon Project                                                      
 *   Copyright (C) 2012 Frank Marien                                  
 *   frank@apsu.be                                                         
 *                                                                         
 *   This file is part of ExtreMon.                                        
 *                                                                         
 *   ExtreMon is free software: you can redistribute it and/or modify      
 *   it under the terms of the GNU General Public License as published by  
 *   the Free Software Foundation, either version 3 of the License, or     
 *   (at your option) any later version.                                   
 *                                                                         
 *   ExtreMon is distributed in the hope that it will be useful,           
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of        
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         
 *   GNU General Public License for more details.                          
 *                                                                         
 *   You should have received a copy of the GNU General Public License     
 *   along with ExtreMon.  If not, see <http://www.gnu.org/licenses/>.     
 */  

package be.apsu.extremon.plugin;
import java.util.HashMap;
import java.util.Map;


public class X3Conf
{
	private Map<String,String> config;
	
	public X3Conf()
	{
		this.config=new HashMap<String,String>();
		for (Map.Entry<String, String> entry : System.getenv().entrySet())
		{
			if(entry.getKey().startsWith("X3MON_"))
				this.config.put(entry.getKey().substring(6).toLowerCase().replace('_','.'),entry.getValue());
		}
	}

	public String get(String key)
	{
		return this.config.get(key);
	}
	
	public int getInt(String key, int defaultValue)
	{
		String strInt=this.config.get(key);
		if(strInt==null)
			return defaultValue;
		return Integer.parseInt(strInt);
	}
	
	public boolean getBoolean(String key,boolean defaultValue)
	{
		String strBool=this.config.get(key);
		if(strBool==null)
			return defaultValue;
		return Boolean.parseBoolean(strBool);
	}
}
