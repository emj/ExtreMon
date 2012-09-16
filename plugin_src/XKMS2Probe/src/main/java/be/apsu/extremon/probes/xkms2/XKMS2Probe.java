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
	private static final int DEFAULT_DELAY = 1000;
	
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
	final private String					expectedFailure;
	
	private boolean							running;

	public XKMS2Probe() throws CertificateException
	{
		this.logger=new X3Log();
		this.config=new X3Conf();
		this.out=new X3Out();
		this.trustService=new XKMS2Client(this.config.get("url"));
		this.certChain=new LinkedList<X509Certificate>();
		this.delay=this.config.getInt("delay",DEFAULT_DELAY);
		this.domain=this.config.get("trust.domain").toUpperCase();
		this.prefix=this.config.get("prefix");
		this.returnRevocationData=this.config.getBoolean("return.revocation.data",false);
		this.expectedFailure=this.config.get("expected.failure")!=null?this.config.get("expected.failure").toLowerCase():null;
		this.running=false;
		
		final CertificateFactory certificateFactory=CertificateFactory.getInstance("X.509");

		final String[] chain=this.config.get("chain").toLowerCase().split(",");
		for(String certName:chain)
		{
			final String encodedCert=this.config.get("cert."+certName);
			final X509Certificate cert=(X509Certificate)certificateFactory.generateCertificate(new ByteArrayInputStream(Base64.decodeBase64(encodedCert)));
			this.certChain.add(cert);
		}
		
		this.out.start();
		this.logger.log("Initialized");
	}

	public final void run()
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
				
				if(this.expectedFailure==null)
				{
					this.out.put(this.prefix+".state",0);
					this.out.put(this.prefix+".state.comment","trust service validates chain (as it should)");
				}
				else
				{
					this.out.put(this.prefix+".state",2);
					this.out.put(this.prefix+".state.comment","trust service validates chain (expected reject with [" + this.expectedFailure + "]!)");
				}
			}
			catch(final CertificateEncodingException ex)
			{
				end=System.currentTimeMillis();
				this.out.put(this.prefix+".state",2);
				this.out.put(this.prefix+".state.comment","bad certificate encoding - check test configuration");
				this.logger.log("Certificate Encoding Exception (Configuration Problem?)");
			}
			catch(final TrustDomainNotFoundException ex)
			{
				end=System.currentTimeMillis();
				this.out.put(this.prefix+".state",2);
				this.out.put(this.prefix+".state.comment","trust domain [" + this.domain + "] not found - check test configuration");
				this.logger.log("Trust Domain Not Found (Configuration Problem?)");
			}
			catch(final ValidationFailedException ex)
			{
				end=System.currentTimeMillis();
				boolean expected=false;
				
				if(this.expectedFailure!=null)
				{
					for(String reason:ex.getReasons())
					{
						if(reason.toLowerCase().endsWith(this.expectedFailure))
						{
							expected=true;
							continue;
						}
					}
				}
				
				if(expected)
				{
					this.out.put(this.prefix+".state",0);
					this.out.put(this.prefix+".state.comment","trust service rejects chain with [" + this.expectedFailure + "] (as it should)");
				}
				else
				{
					this.out.put(this.prefix+".state",2);
					this.out.put(this.prefix+".state.comment","trust service rejects chain (expected validation!)");
				}
			}
			catch(final ClientTransportException ex)
			{
				end=System.currentTimeMillis();
				this.out.put(this.prefix+".state",2);
				this.out.put(this.prefix+".state.comment","transport problem");
			}
			
			catch(final RevocationDataNotFoundException ex)
			{
				end=System.currentTimeMillis();
				this.out.put(this.prefix+".state",2);
				this.out.put(this.prefix+".state.comment","revocation data not found");
			}
			
			this.out.put(this.prefix+".responsetime",(end-start));

			try
			{
				Thread.sleep(this.delay);
			}
			catch(final InterruptedException ex)
			{
				this.logger.log("interrupted");
			}
		}
	}

	public static void main(final String[] args) throws CertificateException
	{
		new XKMS2Probe().run();
	}
}
