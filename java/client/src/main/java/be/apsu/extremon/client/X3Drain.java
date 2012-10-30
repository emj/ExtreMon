/*
 * ExtreMon Project
 * Copyright (C) 2009-2012 Frank Marien
 * frank@apsu.be
 *  
 * This file is part of ExtreMon.
 *    
 * ExtreMon is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 * 
 * ExtreMon is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with ExtreMon.  If not, see <http://www.gnu.org/licenses/>.
 */

package be.apsu.extremon.client;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.UnsupportedEncodingException;
import java.net.SocketException;
import java.net.URL;
import java.util.logging.Level;
import java.util.logging.Logger;

import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLSocketFactory;

import be.apsu.extremon.Launcher;
import be.apsu.extremon.Loom;

public class X3Drain extends Loom implements Launcher
{
	private static final Logger	LOGGER	=Logger.getLogger(X3Drain.class.getName());

	private final	URL					url;
	private 		SSLSocketFactory	socketFactory;
	private			int					missed;
	private			byte[]				responseBuffer;

	public X3Drain(URL url)
	{
		this(null,url);
	}
	
	public X3Drain(String prefix,URL url)
	{
		this(prefix,url,Loom.DEFAULT_MAX_SHUTTLE_SIZE,Loom.DEFAULT_MAX_SHUTTLE_AGE);
	}
	
	public X3Drain(String prefix,URL url,int maxShuttleSize,double maxShuttleAge)
	{
		super(prefix, maxShuttleSize,maxShuttleAge);
		this.url=url;
		this.missed=0;
		this.responseBuffer=new byte[128];
	}
	
	public X3Drain start()
	{
		LOGGER.finest("Starting X3Drain [" + this.url + "]");
		super.start(this);
		return this;
	}
	
	public X3Drain stop() throws InterruptedException
	{
		LOGGER.finest("Stopping X3Drain [" + this.url + "]");
		super.stop();
		return this;
	}
	
	public void setSocketFactory(SSLSocketFactory socketFactory)
	{
		LOGGER.finest("setting SSLSocketFactory to " + socketFactory.toString());
		this.socketFactory=socketFactory;
	}
	
	public int getMissed()
	{
		return this.missed;
	}

	@Override
	public void launch(String shuttle)
	{
		try
		{
			byte[] shuttleBytes=shuttle.getBytes("utf-8");
			
			try
			{
				HttpsURLConnection 	connection=(HttpsURLConnection)this.url.openConnection();
									connection.setDoInput(true);
									connection.setDoOutput(true);
									connection.setUseCaches(false);
									connection.setRequestMethod("POST");
									connection.setRequestProperty("Content-Type","application/x-extremon-shuttle");
									connection.setRequestProperty("Content-Length",Integer.toString(shuttleBytes.length));
									if(this.socketFactory!=null)
										connection.setSSLSocketFactory(this.socketFactory);
				
				OutputStream 		out=connection.getOutputStream();
									out.write(shuttleBytes);
									out.flush();
									out.close();
									
				if(connection.getResponseCode()!=202)
					this.missed+=1;
				
				InputStream responseStream=connection.getInputStream();
				int responseLength=connection.getHeaderFieldInt("Content-Length",0);
				if(responseLength>0)
				{
					if(responseLength>responseBuffer.length)
					{
						LOGGER.severe("Response Too Long");
						responseLength=responseBuffer.length;
					}
					
					try
					{
						if(responseStream.read(this.responseBuffer,0,responseLength)!=responseLength)
						{
							LOGGER.severe("Response Incompletely Read");
						}
						
					}
					catch(SocketException soex)
					{
						LOGGER.log(Level.SEVERE,"SocketException",soex);
					}
				}

				responseStream.close();
			}
			catch(IOException ioex)
			{
				LOGGER.log(Level.SEVERE,"IOException",ioex);
			}	
		}
		catch(UnsupportedEncodingException ueex)
		{
			LOGGER.log(Level.SEVERE,"ExtreMon Requires UTF-8 Encoding Capability",ueex);
			return;
		}
	}
}
