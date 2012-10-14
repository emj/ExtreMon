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

import be.apsu.extremon.Launcher;
import be.apsu.extremon.Loom;

public class X3Out extends Loom implements Launcher
{
	protected static final int	DEFAULT_DELAY				=1000;
	protected static final String RESULT_COMMENT_SUFFIX 	="result.comment";
	protected static final String RESULT_SUFFIX 			="result";
	
	private Map<String,String> config;
	
	public X3Out()
	{
		this(512,.5);
	}
	
	public X3Out(int maxShuttleSize,double maxShuttleAge)
	{
		super(maxShuttleSize,maxShuttleAge);
		
		this.config=new HashMap<String,String>();
		for (Map.Entry<String, String> entry : System.getenv().entrySet())
		{
			if(entry.getKey().startsWith("X3MON_"))
				this.config.put(entry.getKey().substring(6).toLowerCase().replace('_','.'),entry.getValue());
		}
		
		String prefix=confStr("prefix");
		if(prefix!=null)
			setPrefix(prefix);	
	}
	
	public String confStr(String key)
	{
		return this.config.get(key);
	}
	
	public int confInt(String key, int defaultValue)
	{
		String strInt=this.config.get(key);
		if(strInt==null)
			return defaultValue;
		return Integer.parseInt(strInt);
	}
	
	public boolean confBool(String key,boolean defaultValue)
	{
		String strBool=this.config.get(key);
		if(strBool==null)
			return defaultValue;
		return Boolean.parseBoolean(strBool);
	}

	public X3Out start()
	{
		X3Out.this.start(this);
		return this;
	}
	
	public X3Out log(String message)
	{
		System.err.println(message);
		System.err.flush();
		return this;
	}

	@Override
	public void launch(String shuttle)
	{
		System.out.print(shuttle);
		System.out.flush();
	}
}
