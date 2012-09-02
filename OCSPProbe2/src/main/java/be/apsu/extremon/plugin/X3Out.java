package be.apsu.extremon.plugin;

public class X3Out extends Loom implements Launcher
{
	public X3Out()
	{
		super(128,.5);
	}
	
	public X3Out(int maxShuttleSize,double maxShuttleAge)
	{
		super(maxShuttleSize,maxShuttleAge);
	}

	public X3Out start()
	{
		X3Out.this.start(this);
		return this;
	}

	@Override
	public void launch(String shuttle)
	{
		System.out.print(shuttle);
		System.out.flush();
	}
	
	public static void main(String[] args) throws InterruptedException
	{
		X3Out x3Out=new X3Out(128,.5);
			  x3Out.start();
			  
	    int volg=0;
		for(int i=0;i<10000;i++)
		{
			x3Out.put("tralalalala" + volg,volg);
			volg++;
		}
		
		for(;;)
		{
			Thread.sleep(1000);
		}

	}

}
