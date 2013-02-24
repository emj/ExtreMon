/* ExtreMon Project
 * Copyright (C) 2009-2013 Frank Marien
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

public class X3Measure {
    private final String label;
    private final String value;

    public X3Measure(final String label, final String value) {
	this.label = label;
	this.value = value;
    }

    @Override
    public final boolean equals(Object thatObject) {
	if (!(thatObject instanceof X3Measure))
	    return false;
	final X3Measure that = (X3Measure) thatObject;
	return that.label.equals(this.label);
    }

    @Override
    public final int hashCode() {
	return this.label.hashCode();
    }

    public final String getLabel() {
	return this.label;
    }

    public final String getValue() {
	return this.value;
    }
}
