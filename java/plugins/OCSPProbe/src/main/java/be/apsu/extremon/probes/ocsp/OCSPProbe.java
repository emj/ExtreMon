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
import be.apsu.extremon.STATE;
import be.apsu.extremon.plugin.X3Out;

public class OCSPProbe extends X3Out
{
	private X509Certificate 	certificate;
	private X509Certificate 	trustAnchorCert;
	private CertPath			certificatePath;
	private CertPathValidator 	certificatePathValidator;
	private PKIXParameters 		pkixParams;
	private int					delay;
	
	public OCSPProbe()
	{
		CertificateFactory certificateFactory=null;
		
		try
		{
			certificateFactory=CertificateFactory.getInstance("X.509");
		}
		catch(CertificateException cex)
		{
			log("Don't Have Crypto Libs:" + cex.getMessage());
			System.exit(1);
		}
		
		try
		{
			certificate=(X509Certificate)certificateFactory.generateCertificate(new ByteArrayInputStream(Base64.decodeBase64(confStr("certificate"))));
			trustAnchorCert=(X509Certificate)certificateFactory.generateCertificate(new ByteArrayInputStream(Base64.decodeBase64(confStr("trustanchor"))));
		}
		catch(CertificateException cex)
		{
			log("certificate and trustanchor required in config:" + cex.getMessage());
			System.exit(2);
		}
		
		this.delay=confInt("delay",DEFAULT_DELAY);
		
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
			Security.setProperty("ocsp.responderURL",confStr("url"));
			Security.setProperty("ocsp.responderCertSubjectName",this.trustAnchorCert.getSubjectX500Principal().getName());
	
			this.certificatePathValidator=CertPathValidator.getInstance("PKIX");
		}
		catch(InvalidAlgorithmParameterException iaex)
		{
			log("Invalid Algorithm Parameter:" + iaex.getMessage());
			System.exit(3);
		}
		catch(CertificateException cex)
		{
			log("Certificate Exception:" + cex.getMessage());
			System.exit(4);
		}
		catch(NoSuchAlgorithmException nsaex)
		{
			log("No Such Algorithm:" + nsaex.getMessage());
			System.exit(5);
		}
		catch(Exception ex)
		{
			log(ex.getMessage());
			System.exit(6);
		}
		
		start();
		log("Initialized");
	}

	public void probe_forever()
	{
		log("running");
		for(;;)
		{
			double start=System.currentTimeMillis();

			try
			{
				this.certificatePathValidator.validate(this.certificatePath,this.pkixParams);
				put(RESULT_SUFFIX,STATE.OK);
				put(RESULT_COMMENT_SUFFIX,"responder validates ok");
			}
			catch(CertPathValidatorException ex)
			{
				put(RESULT_SUFFIX,STATE.ALERT);
				put(RESULT_COMMENT_SUFFIX,"ocsp responder does not validate cert:" + ex.getMessage());
			}
			catch(InvalidAlgorithmParameterException ex)
			{
				put(RESULT_SUFFIX,STATE.ALERT);
				put(RESULT_COMMENT_SUFFIX,"ocsp responder finds invalid algorithm parameter:" + ex.getMessage());
			}

			double end=System.currentTimeMillis();

			put("responsetime",(end-start));

			try
			{
				Thread.sleep(this.delay);
			}
			catch(InterruptedException iex)
			{
				log("Interrupted During Sleep:" + iex.getMessage());
				return;
			}
		}	
	}
	
	public static void main(String[] argv)
	{
		new OCSPProbe().probe_forever();
	}
}
