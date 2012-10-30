package be.apsu.extremon;

import java.util.HashMap;
import java.util.Map;

public enum STATE
{
	OK(0,false),WARNING(1,false),ALERT(2,false),MISSING(3,false),OK_RESPONDING(0,true),WARNING_RESPONDING(1,true),ALERT_RESPONDING(2,true),MISSING_RESPONDING(3,true);

	public final static 	int					RESPONDING_BITMASK=0x04;
	private 				int					code;
	private final static	Map<Integer,STATE>	byCode;
	
	static
	{
		byCode=new HashMap<Integer,STATE>();
		for(STATE state:values())
			byCode.put(state.getCode(),state);
	}

	STATE(int code,boolean responding)
	{
		this.code=code | (responding?RESPONDING_BITMASK:0);
	}
	
	STATE(int code)
	{
		this.code=(byte)code;
	}

	public int getCode()
	{
		return this.code;
	}

	public boolean isResponding()
	{
		return (this.code & RESPONDING_BITMASK)!=0;
	}
	
	public static STATE fromCode(int code)
	{
		return byCode.get(code);
	}
}
