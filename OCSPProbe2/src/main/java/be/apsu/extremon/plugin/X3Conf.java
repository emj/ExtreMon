package be.apsu.extremon.plugin;
import java.util.HashMap;
import java.util.Map;


public class X3Conf
{
	private Map<String,String> config;
	
	public X3Conf()
	{
		this.config=new HashMap<String,String>();
		for (Map.Entry<String, String> entry : System.getenv().entrySet())
		{
			if(entry.getKey().startsWith("X3MON_"))
				this.config.put(entry.getKey().substring(6).toLowerCase().replace('_','.'),entry.getValue());
		}
	}

	public String get(Object key)
	{
		return this.config.get(key);
	}
}
