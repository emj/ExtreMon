package be.apsu.extremon.plugin.tests;

import org.junit.Test;
import be.apsu.extremon.plugin.X3Out;

public class Exercise
{
	@Test
	public void excercise() throws InterruptedException
	{
		X3Out x3Out=new X3Out(128,.5);
		x3Out.start();

		int volg=0;
		for(int i=0;i<10000;i++)
		{
			x3Out.put("yadda"+volg,volg);
			volg++;
		}

		for(;;)
		{
			Thread.sleep(1000);
		}

	}

}
