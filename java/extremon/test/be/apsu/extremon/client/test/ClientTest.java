package be.apsu.extremon.test;

import java.util.Random;

public class ClientTest
{
	private static final char[]	symbols	=new char[36];
	private Random				random;

	static
	{
		for(int idx=0;idx<10;++idx)
			symbols[idx]=(char)('0'+idx);
		for(int idx=10;idx<36;++idx)
			symbols[idx]=(char)('a'+idx-10);
	}
	
	private String randomString(int size)
	{
		char[] buf=new char[2+size];
		for(int idx=0;idx<buf.length;++idx)
			buf[idx]=symbols[random.nextInt(symbols.length)];
		return new String(buf);
	}

	private String randomFloat()
	{
		return Double.toString(random.nextDouble());
	}

	private String randomInt()
	{
		return Integer.toString(random.nextInt());
	}

	private String randomLabel(int size)
	{
		StringBuilder builder=new StringBuilder();
		for(int i=0;i<size;i++)
		{
			builder.append(randomString(this.random.nextInt(7)));
			if(i<size-1)
				builder.append('.');
		}

		return builder.toString();
	}

	private String randomRecord()
	{
		StringBuilder builder=new StringBuilder(randomLabel(7));
		builder.append('=');

		switch(random.nextInt(3))
		{
		case 0:
			builder.append(randomString(7));
			break;
		case 1:
			builder.append(randomInt());
			break;
		default:
			builder.append(randomFloat());
			break;
		}

		builder.append('\n');
		return builder.toString();
	}

	private String randomShuttle(int size)
	{
		StringBuilder builder=new StringBuilder();
		for(int i=0;i<size;i++)
			builder.append(randomRecord());
		// builder.append('\n');
		return builder.toString();
	}
}
