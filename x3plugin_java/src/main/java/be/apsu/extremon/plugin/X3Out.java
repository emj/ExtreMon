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
}
