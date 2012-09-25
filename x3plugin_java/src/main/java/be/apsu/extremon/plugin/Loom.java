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
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;


public class Loom implements Runnable
{
	protected enum STATE
	{
		OK(0),WARNING(1),ALERT(2),MISSING(3),TACKLED(4);
		
		private byte code;
		
		STATE(int code)
		{
			this.code=(byte)code;
		}
		
		byte getCode()
		{
			return this.code;
		}
	}
	
	private final LinkedBlockingQueue<X3Record> outQueue;
	private final Thread						worker;
	private final Map<String,String>			shuttle;
	private final int 							maxShuttleSize;
	private final int							maxShuttleAge;
	private final X3Record						requestStop;
	private  	  String						prefix;
	private 	  Launcher						launcher;
	private 	  long							nextDeadline;
	private		  boolean						ending,lazy;
	
	public Loom(int maxShuttleSize,double maxShuttleAge)
	{
		super();
		this.outQueue=new LinkedBlockingQueue<X3Record>();
		this.worker=new Thread(this,"Loom");
		this.worker.setDaemon(true);
		this.shuttle=new HashMap<String,String>();
		this.maxShuttleSize=maxShuttleSize;
		this.maxShuttleAge=(int)(maxShuttleAge*1000.0);
		this.launcher=null;
		this.requestStop=new X3Record("","");
		this.ending=false;
		this.lazy=false;
		this.reset();
	}
	
	public String getPrefix()
	{
		return prefix;
	}

	public void setPrefix(String prefix)
	{
		this.prefix = prefix;
	}

	public Loom start(Launcher launcher)
	{
		if(launcher==null)
			throw new NullPointerException("launcher is null.");
		this.launcher=launcher;
		this.worker.start();
		return this;
	}
	
	public Loom stop() throws InterruptedException
	{
		this.outQueue.offer(requestStop);
		this.worker.join();
		return this;
	}
	
	public Loom put(String label, String value)
	{
		if(label.indexOf('=')!=-1 || label.indexOf('\n')!=-1 || value.indexOf('=')!=-1 || value.indexOf('\n')!=-1)
			throw new IllegalArgumentException("\"=\" and \"\\n\" Are Illegal in X3Mon Labels And Values");
		this.outQueue.offer(new X3Record(makeLabel(label),value.toLowerCase().replace('=', ':').replace('\n',' ')));
		return this;
	}
	
	public Loom put(String label, STATE state)
	{
		this.outQueue.offer(new X3Record(makeLabel(label),String.valueOf((int)state.getCode())));
		return this;
	}
	
	public Loom put(String label, long value)
	{
		this.outQueue.offer(new X3Record(makeLabel(label),String.valueOf(value)));
		return this;
	}
	
	public Loom put(String label, int value)
	{
		this.outQueue.offer(new X3Record(makeLabel(label),String.valueOf(value)));
		return this;
	}
	
	public Loom put(String label, double value)
	{
		this.outQueue.offer(new X3Record(makeLabel(label),String.valueOf(value)));
		return this;
	}
	
	public Loom put(String label, float value)
	{
		this.outQueue.offer(new X3Record(makeLabel(label),String.valueOf(value)));
		return this;
	}
	
	public Loom put(String label, boolean value)
	{
		this.outQueue.offer(new X3Record(makeLabel(label),value?"1":"0"));
		return this;
	}
	
	private String makeLabel(String suffix)
	{
		StringBuilder builder=new StringBuilder(this.prefix);
		builder.append('.');
		builder.append(suffix);
		return builder.toString();
	}
	
	private void reset()
	{
		this.nextDeadline=System.currentTimeMillis()+this.maxShuttleAge;   
	}
	
	private void launchAndClear()
	{
		StringBuilder builder=new StringBuilder();
		for (Map.Entry<String, String> entry : this.shuttle.entrySet())
		{
			builder.append(entry.getKey());
		    builder.append("=");
		    builder.append(entry.getValue());
		    builder.append("\n");
		}
		builder.append("\n");
		this.launcher.launch(builder.toString());
		this.shuttle.clear();
		this.reset();
	}

	private class X3Record
	{
		private final String label;
		private final String value;
		
		public X3Record(String label,String value)
		{
			super();
			this.label=label;
			this.value=value;
		}

		public String getLabel()
		{
			return label;
		}

		public String getValue()
		{
			return value;
		}
	}
	



	@Override
	public void run()
	{
		this.lazy=false;
		this.ending=false;
		for(;;)
		{
			X3Record record=null;
			
			try
			{
				if(this.lazy)
				{
					record=this.outQueue.take();
				}
				else
				{
					record=this.outQueue.poll(this.maxShuttleAge,TimeUnit.MILLISECONDS);
				}
			}
			catch(InterruptedException iex)
			{
				this.lazy=false;
				this.ending=true;
			}
			
			if(record!=null) // queue not empty
			{
				if(this.lazy)
					this.reset();
				
				if(record==this.requestStop)
					this.ending=true;
				else
					this.shuttle.put(record.getLabel(),record.getValue());
				
				if(this.shuttle.size()>=this.maxShuttleSize )
				{
					this.launchAndClear();
				}
				else if(System.currentTimeMillis()>this.nextDeadline)
				{
					this.launchAndClear();	
				}
				
				this.lazy=false;
			}
			else 			// queue empty
			{
				if(this.shuttle.size()>0)
				{
					if(System.currentTimeMillis()>this.nextDeadline)
					{
						this.launchAndClear();
					}
				}
				else if(!this.ending)
				{
					this.lazy=true;
				}
				else
				{
					return;
				}
			}	
		}	
	}
	
	public int getQueueLength()
	{
		return this.outQueue.size();
	}
}