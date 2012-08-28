package be.apsu.extremon.plugin;

public class X3Log
{
	public X3Log log(String message)
	{
		System.err.println(message);
		System.err.flush();
		return this;
	}
}
