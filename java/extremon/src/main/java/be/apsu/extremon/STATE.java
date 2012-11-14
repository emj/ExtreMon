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

package be.apsu.extremon;

import java.util.HashMap;
import java.util.Map;

public enum STATE {
    OK(0, false), WARNING(1, false), ALERT(2, false), MISSING(3, false), OK_RESPONDING(
	    0, true), WARNING_RESPONDING(1, true), ALERT_RESPONDING(2,
	    true), MISSING_RESPONDING(3, true);

    public final static int RESPONDING_BITMASK = 0x04;
    private int code;
    private final static Map<Integer, STATE> byCode;

    static {
	byCode = new HashMap<Integer, STATE>();
	for (STATE state : values())
	    byCode.put(state.getCode(), state);
    }

    STATE(int code, boolean responding) {
	this.code = code | (responding ? RESPONDING_BITMASK : 0);
    }

    STATE(int code) {
	this.code = (byte) code;
    }

    public int getCode() {
	return this.code;
    }

    public boolean isResponding() {
	return (this.code & RESPONDING_BITMASK) != 0;
    }

    public static STATE fromCode(int code) {
	return byCode.get(code);
    }
}
