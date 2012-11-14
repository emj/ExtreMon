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

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.logging.Level;
import java.util.logging.Logger;

public class X3Client implements X3SourceListener {
    private static final Logger LOGGER = Logger.getLogger(X3Client.class
	    .getName());

    private Set<X3Source> sources;
    private Set<X3ClientListener> listeners;
    private Map<String, Map<X3Source, X3TimeValue>> cache;
    private Set<X3Measure> shuttle;

    public X3Client() {
	super();
	this.sources = new HashSet<X3Source>();
	this.listeners = new HashSet<X3ClientListener>();
	this.cache = new HashMap<String, Map<X3Source, X3TimeValue>>();
	this.shuttle = new HashSet<X3Measure>();
    }

    public final void addSource(X3Source source) {
	this.sources.add(source);
	source.start(this);
    }

    public final void removeSource(X3Source source) {
	source.stop();
	this.sources.add(source);
    }

    public final void addListener(X3ClientListener listener) {
	this.listeners.add(listener);
    }

    public final void removeListener(final X3ClientListener listener) {
	this.listeners.remove(listener);
    }

    @Override
    public void sourceConnected(X3Source source) {
    }

    @Override
    public void sourceDisconnected(X3Source source) {
    }

    @Override
    public final synchronized void sourceData(X3Source source,
	    double timeStamp, List<X3Measure> measures) {
	for (X3Measure measure : measures) {
	    LOGGER.log(
		    Level.FINEST,
		    "SOURCEDATA " + source.getName() + " ["
			    + measure.getLabel() + "="
			    + measure.getValue() + "]");

	    Map<X3Source, X3TimeValue> sourceTimeValue = this.cache
		    .get(measure.getLabel());

	    if (sourceTimeValue == null) {
		LOGGER.finest("\tADDLBL " + measure.getLabel() + "("
			+ source.getName() + ")");
		sourceTimeValue = new HashMap<X3Source, X3TimeValue>();
		sourceTimeValue.put(source, new X3TimeValue(timeStamp,
			measure.getValue()));
		this.cache.put(measure.getLabel(), sourceTimeValue);
	    } else {
		X3TimeValue timeValue = sourceTimeValue.get(source);
		if (timeValue == null) {
		    LOGGER.finest("\tADDSRC " + measure.getLabel() + "("
			    + source.getName() + ")");
		    timeValue = new X3TimeValue(timeStamp,
			    measure.getValue());
		    sourceTimeValue.put(source, timeValue);
		} else {
		    LOGGER.finest("\tUPDATE " + measure.getLabel() + "("
			    + source.getName() + ")");
		    timeValue.setValue(measure.getValue());
		}
	    }

	    this.shuttle.add(measure);
	}

	for (X3ClientListener listener : this.listeners)
	    listener.clientData(this, this.shuttle);
	this.shuttle.clear();
    }
}
