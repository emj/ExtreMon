package be.apsu.extremon.probes.ocsp;

import java.io.ByteArrayInputStream;
import java.security.InvalidAlgorithmParameterException;
import java.security.NoSuchAlgorithmException;
import java.security.Security;
import java.security.cert.CertPath;
import java.security.cert.CertPathValidator;
import java.security.cert.CertPathValidatorException;
import java.security.cert.CertStore;
import java.security.cert.CertStoreParameters;
import java.security.cert.CertificateException;
import java.security.cert.CertificateFactory;
import java.security.cert.CollectionCertStoreParameters;
import java.security.cert.PKIXParameters;
import java.security.cert.TrustAnchor;
import java.security.cert.X509Certificate;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.apache.commons.codec.binary.Base64;
import be.apsu.extremon.plugin.X3Conf;
import be.apsu.extremon.plugin.X3Log;
import be.apsu.extremon.plugin.X3Out;

public class OCSPProbe
{
	private final X3Conf 		config;
	private final X3Log  		logger;
	private final X3Out  		out;
	private X509Certificate 	certificate;
	private X509Certificate 	trustAnchorCert;
	private CertPath			certificatePath;
	private CertPathValidator 	certificatePathValidator;
	private PKIXParameters 		pkixParams;
	private int					delay;
	private String				prefix;
	
	public OCSPProbe()
	{
		CertificateFactory certificateFactory=null;
		
		this.logger=new X3Log();
		this.config=new X3Conf();
		this.out=new X3Out();
		
		try
		{
			certificateFactory=CertificateFactory.getInstance("X.509");
		}
		catch(CertificateException cex)
		{
			this.logger.log("Don't Have Crypto Libs:" + cex.getMessage());
			System.exit(1);
		}
		
		try
		{
			certificate=(X509Certificate)certificateFactory.generateCertificate(new ByteArrayInputStream(Base64.decodeBase64(this.config.get("certificate"))));
			trustAnchorCert=(X509Certificate)certificateFactory.generateCertificate(new ByteArrayInputStream(Base64.decodeBase64(this.config.get("trustanchor"))));
		}
		catch(CertificateException cex)
		{
			this.logger.log("Certificate and Trust Anchor Required:" + cex.getMessage());
			System.exit(2);
		}
		
		this.delay=Integer.parseInt(this.config.get("delay"));
		this.prefix=this.config.get("prefix");
		
		try
		{
			List<X509Certificate> certs=new ArrayList<X509Certificate>();
			certs.add(this.certificate);
			this.certificatePath=(CertPath)certificateFactory.generateCertPath(certs);
	
			TrustAnchor trustAnchor=new TrustAnchor(this.trustAnchorCert,null);
			Set<TrustAnchor> trustedCertsSet=new HashSet<TrustAnchor>();
			trustedCertsSet.add(trustAnchor);
	
			Set<X509Certificate> certSet=new HashSet<X509Certificate>();
			certSet.add(this.trustAnchorCert);
			CertStoreParameters storeParams=new CollectionCertStoreParameters(certSet);
			CertStore store=CertStore.getInstance("Collection",storeParams);
	
			pkixParams=new PKIXParameters(trustedCertsSet);
			pkixParams.addCertStore(store);
	
			Security.setProperty("ocsp.enable","true");
			Security.setProperty("ocsp.responderURL",this.config.get("url"));
			Security.setProperty("ocsp.responderCertSubjectName",this.trustAnchorCert.getSubjectX500Principal().getName());
	
			this.certificatePathValidator=CertPathValidator.getInstance("PKIX");
		}
		catch(InvalidAlgorithmParameterException iaex)
		{
			this.logger.log("Invalid Algorithm Parameter:" + iaex.getMessage());
			System.exit(3);
		}
		catch(CertificateException cex)
		{
			this.logger.log("Certificate Exception:" + cex.getMessage());
			System.exit(4);
		}
		catch(NoSuchAlgorithmException nsaex)
		{
			this.logger.log("No Such Algorithm:" + nsaex.getMessage());
			System.exit(5);
		}
		catch(Exception ex)
		{
			this.logger.log(ex.getMessage());
			System.exit(6);
		}
		
		this.out.start();
		this.logger.log("Initialized");
	}

	public void run()
	{
		int result;

		this.logger.log("Running");
		for(;;)
		{
			result=0;

			double start=System.currentTimeMillis();

			try
			{
				this.certificatePathValidator.validate(this.certificatePath,this.pkixParams);
			}
			catch(CertPathValidatorException ex)
			{
				result=1;
			}
			catch(InvalidAlgorithmParameterException ex)
			{
				result=2;
			}

			double end=System.currentTimeMillis();

			this.out.put(this.prefix + ".ocspprobe.responsetime",(end-start));
			this.out.put(this.prefix + ".ocspprobe.result",result);

			try
			{
				Thread.sleep(this.delay);
			}
			catch(InterruptedException iex)
			{
				this.logger.log("Interrupted During Sleep:" + iex.getMessage());
				return;
			}
		}	
	}
	
	public static void main(String[] argv)
	{
		new OCSPProbe().run();
	}
}
