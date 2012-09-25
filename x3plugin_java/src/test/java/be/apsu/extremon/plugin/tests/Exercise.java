package be.apsu.extremon.plugin.tests;

import java.util.Random;

import org.junit.Test;

import be.apsu.extremon.plugin.Launcher;
import be.apsu.extremon.plugin.Loom;
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

//	static int enqueued=0;
//	static int dequeued=0;
//
//	public static void main(String[] args) throws InterruptedException
//	{	
//		Random random=new Random();
//		
//		Loom loom=new Loom(128,.5);
//		
//		loom.start(new Launcher()
//		{
//			@Override
//			public void launch(String shuttle)
//			{
//				int shuttle_size=shuttle.split("\n").length;
//				dequeued+=shuttle_size;
//				try
//				{
//					Thread.sleep(10);
//				}
//				catch(InterruptedException e)
//				{
//					// TODO Auto-generated catch block
//					e.printStackTrace();
//				}
//			}
//		});
//		
//		int volg=0;
//		
//		for(int j=0;j<10;j++)
//		{		
//			int count=random.nextInt(1024);
//			System.err.println("enqueue " + count + " records");
//			for(int i=0;i<count;i++)
//			{
//				loom.put("lalalalala." + volg,volg);
//				volg++;
//			}
//			
//			enqueued+=count;
//			Thread.sleep(random.nextInt(10000));
//			System.err.println("en=" + enqueued + " de=" + dequeued + " q=" + loom.getQueueLength());
//		}
//		
//		loom.stop();
//		
//		for(int k=0;k<2;k++)
//		{
//			System.err.println("en=" + enqueued + " de=" + dequeued + " q=" + loom.getQueueLength());
//			Thread.sleep(1000);
//		}
//	}
