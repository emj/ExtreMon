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

import be.apsu.extremon.STATE;
import be.apsu.extremon.plugin.X3Out;
import be.fedict.trust.client.XKMS2Client;
import be.fedict.trust.client.exception.RevocationDataNotFoundException;
import be.fedict.trust.client.exception.TrustDomainNotFoundException;
import be.fedict.trust.client.exception.ValidationFailedException;

import com.sun.xml.ws.client.ClientTransportException;

public class XKMS2Probe extends X3Out
{	
	private static final String XKMS2_REASONURI_PREFIX 	= "http://www.w3.org/2002/03/xkms#";

	// probe config
	final private XKMS2Client				trustService;
	final private List<X509Certificate>		certChain;
	final private String					domain;
	final private int						delay;
	final private boolean					returnRevocationData;
	final private String					expectedFailure;
	private boolean							running;

	public XKMS2Probe() throws CertificateException
	{
		super();
		this.trustService=new XKMS2Client(confStr("url"));
		this.certChain=new LinkedList<X509Certificate>();
		this.delay=confInt("delay",DEFAULT_DELAY);
		this.domain=confStr("trust.domain").toUpperCase();
		this.returnRevocationData=confBool("return.revocation.data",false);
		this.expectedFailure=confStr("expected.failure")!=null?confStr("expected.failure").toLowerCase():null;
		this.running=false;
		
		final CertificateFactory certificateFactory=CertificateFactory.getInstance("X.509");

		final String[] chain=confStr("chain").toLowerCase().split(",");
		for(String certName:chain)
		{
			final String encodedCert=confStr("cert."+certName);
			final X509Certificate cert=(X509Certificate)certificateFactory.generateCertificate(new ByteArrayInputStream(Base64.decodeBase64(encodedCert)));
			this.certChain.add(cert);
		}
		
		start();
		log("initialized");
	}

	public final void probe_forever()
	{
		double start=0,end=0;
		log("running");
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
					put(RESULT_SUFFIX,STATE.OK);
					put(RESULT_COMMENT_SUFFIX,"validates ok");
				}
				else
				{
					put(RESULT_SUFFIX,STATE.ALERT);
					put(RESULT_COMMENT_SUFFIX,"validates (expected [" + this.expectedFailure + "]) trust service compromised?");
				}
			}
			catch(final CertificateEncodingException ex)
			{
				end=System.currentTimeMillis();
				put(RESULT_SUFFIX,STATE.ALERT);
				put(RESULT_COMMENT_SUFFIX,"bad certificate encoding");
				log("Certificate Encoding Exception (Configuration Problem?)");
			}
			catch(final TrustDomainNotFoundException ex)
			{
				end=System.currentTimeMillis();
				put(RESULT_SUFFIX,STATE.ALERT);
				put(RESULT_COMMENT_SUFFIX,"trust domain [" + this.domain + "] not found.");
				log("Trust Domain Not Found (Configuration Problem?)");
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
					put(RESULT_SUFFIX,STATE.OK);
					put(RESULT_COMMENT_SUFFIX,"rejects with [" + getPrintableReasons(ex.getReasons()) + "] ok");
				}
				else
				{
					put(RESULT_SUFFIX,STATE.ALERT);
					put(RESULT_COMMENT_SUFFIX,"rejects with [" + getPrintableReasons(ex.getReasons()) + "] expected validation");
				}
			}
			catch(final ClientTransportException ex)
			{
				end=System.currentTimeMillis();
				put(RESULT_SUFFIX,2);
				put(RESULT_COMMENT_SUFFIX,"transport problem");
			}
			
			catch(final RevocationDataNotFoundException ex)
			{
				end=System.currentTimeMillis();
				put(RESULT_SUFFIX,STATE.OK);
				put(RESULT_COMMENT_SUFFIX,"revocation data not found");
			}
			
			put("responsetime",(end-start));

			try
			{
				Thread.sleep(this.delay);
			}
			catch(final InterruptedException ex)
			{
				log("interrupted");
			}
		}
	}
	
	private String getPrintableReasons(final List<String> reasons)
    {
		final StringBuilder builder=new StringBuilder();
        for(int i=0;i<reasons.size();i++)
        {
        	final String reason=reasons.get(i);
            if(reason.startsWith(XKMS2_REASONURI_PREFIX))
            {
                builder.append(reason.substring(XKMS2_REASONURI_PREFIX.length()));
                if(i<(reasons.size()-1))
                	builder.append(',');
            }
        }		
        return builder.toString();
    }

	public static void main(final String[] args) throws CertificateException
	{
		new XKMS2Probe().probe_forever();
	}
}
