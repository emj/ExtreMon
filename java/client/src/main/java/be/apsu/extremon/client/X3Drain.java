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

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.SocketException;
import java.net.URL;
import java.security.KeyManagementException;
import java.security.NoSuchAlgorithmException;
import java.util.logging.Logger;

import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLSocketFactory;

import be.apsu.extremon.Launcher;
import be.apsu.extremon.Loom;

public class X3Drain extends Loom implements Launcher
{
	private static final Logger	LOGGER	=Logger.getLogger(X3Drain.class.getName());

	private URL					url;
	private OutputStream		out;
	private SSLSocketFactory	socketFactory;

	public X3Drain(URL url)
	{
		super();
		this.url=url;
	}
	
	public void setSocketFactory(SSLSocketFactory socketFactory)
	{
		this.socketFactory=socketFactory;
	}

	public final void start() throws IOException, InterruptedException, KeyManagementException, NoSuchAlgorithmException
	{
		for(int i=0;i<32;i++)
		{
			//String shuttle=randomShuttle(this.random.nextInt(25));
			String shuttle=	"be.colifra.sumeru.df.data.df_complex.used.percentage.state.responding=1\n" +
							"be.colifra.sumeru.df.data.df_complex.used.percentage.state.responder=Frank Marien\n" +
							"be.colifra.sumeru.df.data.df_complex.used.percentage.state.responder.comment=Testing Operator Response Mechanism\n";
			System.out.println(shuttle);
			final byte[] shuttleBytes=shuttle.getBytes("utf-8");
			
			final HttpsURLConnection connection=(HttpsURLConnection)this.url.openConnection();
			
			if(this.socketFactory!=null)
				connection.setSSLSocketFactory(this.socketFactory);
			
			connection.setDoInput(true);
			connection.setDoOutput(true);
			connection.setUseCaches(false);
			connection.setRequestMethod("POST");
			connection.setRequestProperty("X-ExtreMon-Sequence",Integer.toString(i));
			connection.setRequestProperty("Content-Type","application/x-extremon-shuttle");
			connection.setRequestProperty("Content-Length",Integer.toString(shuttleBytes.length));
			out=connection.getOutputStream();

			this.out.write(shuttleBytes);
			this.out.flush();
			this.out.close();
			
			System.out.println(connection.getHeaderField("X-ExtreMon-Sequence"));
			
			final BufferedReader reader=new BufferedReader(new InputStreamReader(connection.getInputStream(),"UTF-8"));
			try
			{
				char[] inbuf=new char[1024];
				int nread;
			
				nread=reader.read(inbuf);
				while(nread>0)
				{
					System.out.println("["+new String(inbuf,0,nread)+"]");
					nread=reader.read(inbuf);
				}
			}
			catch(SocketException sex)
			{
				System.err.println("socket closed");
			}

			reader.close();
			
			//Thread.sleep(500);
		}
	}

	public final X3Drain stop()
	{
		return this;
	}



	public static void main(String[] argv) throws InterruptedException, IOException, KeyManagementException, NoSuchAlgorithmException
	{
		X3Drain drain=new X3Drain(new URL("https://extremon.net/post"));
		drain.start();

	}

	@Override
	public void launch(String shuttle)
	{
		// TODO Auto-generated method stub
		
	}
}
