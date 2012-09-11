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

package be.apsu.extremon.probes.xkms2;

import java.io.ByteArrayInputStream;
import java.security.cert.CertificateEncodingException;
import java.security.cert.CertificateException;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.util.LinkedList;
import java.util.List;
import org.apache.commons.codec.binary.Base64;
import be.apsu.extremon.plugin.X3Conf;
import be.apsu.extremon.plugin.X3Log;
import be.apsu.extremon.plugin.X3Out;
import be.fedict.trust.client.XKMS2Client;
import be.fedict.trust.client.exception.RevocationDataNotFoundException;
import be.fedict.trust.client.exception.TrustDomainNotFoundException;
import be.fedict.trust.client.exception.ValidationFailedException;
import com.sun.xml.ws.client.ClientTransportException;

public class XKMS2Probe
{
	// extremon config
	final private X3Conf					config;
	final private X3Out						out;
	final private X3Log						logger;

	// probe config
	final private XKMS2Client				trustService;
	final private List<X509Certificate>		certChain;
	final private String					domain,prefix;
	final private int						delay;
	final private boolean					returnRevocationData;
	
	private boolean							running;

	public XKMS2Probe() throws CertificateException
	{
		this.logger=new X3Log();
		this.config=new X3Conf();
		this.out=new X3Out();
		this.trustService=new XKMS2Client(this.config.get("url"));
		this.certChain=new LinkedList<X509Certificate>();
		this.delay=this.config.getInt("delay",1000);
		this.domain=this.config.get("trust.domain").toUpperCase();
		this.prefix=this.config.get("prefix");
		this.returnRevocationData=this.config.getBoolean("return.revocation.data",false);
		this.running=false;
		
		CertificateFactory certificateFactory=CertificateFactory.getInstance("X.509");

		String[] chain=this.config.get("chain").toLowerCase().split(",");
		for(String certName:chain)
		{
			String encodedCert=this.config.get("cert."+certName);
			X509Certificate cert=(X509Certificate)certificateFactory.generateCertificate(new ByteArrayInputStream(Base64.decodeBase64(encodedCert)));
			this.certChain.add(cert);
		}
		
		this.out.start();
		this.logger.log("Initialized");
	}

	public void run()
	{
		double start=0,end=0;
		this.logger.log("running");
		this.running=true;
		while(this.running)
		{
			try
			{
				start=System.currentTimeMillis();
				trustService.validate(this.domain,this.certChain,this.returnRevocationData);
				end=System.currentTimeMillis();
				this.out.put(this.prefix+".xkms2probe.result",0);
				this.out.put(this.prefix+".xkms2probe.result.comment","trust service validates chain");
			}
			catch(CertificateEncodingException ex)
			{
				end=System.currentTimeMillis();
				this.out.put(this.prefix+".xkms2probe.result",-1);
				this.out.put(this.prefix+".xkms2probe.result.comment","bad certificate encoding");
				this.logger.log("Certificate Encoding Exception (Configuration Problem?)");
			}
			catch(TrustDomainNotFoundException ex)
			{
				end=System.currentTimeMillis();
				this.out.put(this.prefix+".xkms2probe.result",-2);
				this.out.put(this.prefix+".xkms2probe.result.comment","trust domain not found");
				this.logger.log("Trust Domain Not Found (Configuration Problem?)");
			}
			catch(ValidationFailedException ex)
			{
				end=System.currentTimeMillis();
				this.out.put(this.prefix+".xkms2probe.result",1);
				this.out.put(this.prefix+".xkms2probe.result.comment","trust service rejects chain");
			}
			catch(ClientTransportException ex)
			{
				end=System.currentTimeMillis();
				this.out.put(this.prefix+".xkms2probe.result",2);
				this.out.put(this.prefix+".xkms2probe.result.comment","transport problem");
			}
			
			catch(RevocationDataNotFoundException ex)
			{
				end=System.currentTimeMillis();
				this.out.put(this.prefix+".xkms2probe.result",3);
				this.out.put(this.prefix+".xkms2probe.result.comment","revocation data not found");
			}
			
			this.out.put(this.prefix+".xkms2probe.responsetime",(end-start));

			try
			{
				Thread.sleep(this.delay);
			}
			catch(InterruptedException ex)
			{
				this.logger.log("interrupted");
			}
		}
	}

	public static void main(String[] args) throws CertificateException
	{
		new XKMS2Probe().run();
	}
}
