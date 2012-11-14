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
import java.net.URL;
import java.net.UnknownHostException;
import java.util.ArrayList;
import java.util.List;
import java.util.logging.Level;
import java.util.logging.Logger;

import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLSocketFactory;

public class X3Source implements Runnable {
    private static final int RETRY_DELAY = 2000;
    private static final Logger LOGGER = Logger.getLogger(X3Source.class
	    .getName());

    private String name;
    private URL url;
    private X3SourceListener listener;
    private boolean running;
    private SSLSocketFactory socketFactory;

    public X3Source(String name, URL url) {
	super();
	this.name = name;
	this.url = url;
    }

    public void setSocketFactory(SSLSocketFactory socketFactory) {
	this.socketFactory = socketFactory;
    }

    public final X3Source start(X3SourceListener aListener) {
	this.listener = aListener;
	new Thread(this, "X3Source [" + this.url.toString() + "]")
		.start();
	return this;
    }

    public final X3Source stop() {
	this.running = false;
	return this;
    }

    @Override
    public final void run() {
	this.running = true;
	while (this.running) {
	    try {
		final HttpsURLConnection connection = (HttpsURLConnection) this.url
			.openConnection();

		if (this.socketFactory != null)
		    connection.setSSLSocketFactory(this.socketFactory);

		final BufferedReader reader = new BufferedReader(
			new InputStreamReader(
				connection.getInputStream(), "UTF-8"));
		final List<X3Measure> lines = new ArrayList<X3Measure>();
		String line;
		double timeStamp = 0;

		this.listener.sourceConnected(this);

		while (this.running && (line = reader.readLine()) != null) {
		    if (line.length() == 0) {
			this.listener.sourceData(this, timeStamp, lines);
			lines.clear();
			timeStamp = 0;
		    } else {
			final String[] labelValue = line.split("=");
			if (labelValue.length == 2) {
			    lines.add(new X3Measure(labelValue[0],
				    labelValue[1]));

			    if (labelValue[0].endsWith("timestamp")) {
				try {
				    timeStamp = Double
					    .parseDouble(labelValue[1]);
				} catch (NumberFormatException nfe) {
				    LOGGER.log(Level.SEVERE,
					    "failed to parse timestamp",
					    nfe);
				}
			    }
			}
		    }
		}

		reader.close();
		this.listener.sourceDisconnected(this);
	    } catch (UnknownHostException ex) {
		LOGGER.log(Level.SEVERE, null, ex);
	    } catch (IOException ex) {
		LOGGER.log(Level.SEVERE, null, ex);
		this.listener.sourceDisconnected(this);
	    }

	    try {
		Thread.sleep(RETRY_DELAY);
	    } catch (InterruptedException ex) {
		LOGGER.log(Level.SEVERE, null, ex);
	    }
	}
    }

    public final String getName() {
	return this.name;
    }
}
