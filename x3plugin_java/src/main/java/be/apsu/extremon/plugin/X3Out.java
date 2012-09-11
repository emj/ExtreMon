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

public class X3Out extends Loom implements Launcher
{
	public X3Out()
	{
		super(128,.5);
	}
	
	public X3Out(int maxShuttleSize,double maxShuttleAge)
	{
		super(maxShuttleSize,maxShuttleAge);
	}

	public X3Out start()
	{
		X3Out.this.start(this);
		return this;
	}

	@Override
	public void launch(String shuttle)
	{
		System.out.print(shuttle);
		System.out.flush();
	}
}
