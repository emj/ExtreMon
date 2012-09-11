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

package be.apsu.extremon.probes.tsp;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.math.BigInteger;
import java.net.URL;
import java.net.URLConnection;
import java.security.Security;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.util.Arrays;
import java.util.Random;
import org.apache.commons.codec.binary.Base64;
import org.bouncycastle.asn1.cms.AttributeTable;
import org.bouncycastle.asn1.pkcs.PKCSObjectIdentifiers;
import org.bouncycastle.cms.SignerInformationVerifier;
import org.bouncycastle.cms.jcajce.JcaSimpleSignerInfoVerifierBuilder;
import org.bouncycastle.tsp.TSPAlgorithms;
import org.bouncycastle.tsp.TSPException;
import org.bouncycastle.tsp.TimeStampRequest;
import org.bouncycastle.tsp.TimeStampRequestGenerator;
import org.bouncycastle.tsp.TimeStampResponse;
import org.bouncycastle.tsp.TimeStampToken;
import org.bouncycastle.tsp.TimeStampTokenInfo;
import be.apsu.extremon.plugin.X3Conf;
import be.apsu.extremon.plugin.X3Log;
import be.apsu.extremon.plugin.X3Out;

public class TSPProbe 
{
	// extremon config
	final private X3Conf					config;
	final private X3Out						out;
	final private X3Log						logger;
	// probe config
	final private String					prefix;
	final private int						delay;
	final private TimeStampRequestGenerator requestGenerator;
	final private URL						url;
	final private SignerInformationVerifier	signerVerifier;
	final private Random					random;

	private boolean							running;

	public TSPProbe() throws Exception
	{
		this.logger=new X3Log();
		this.config=new X3Conf();
		this.out=new X3Out();
		this.delay=this.config.getInt("delay",1000);
		this.prefix=this.config.get("prefix");
		this.running=false;

		Security.addProvider(new org.bouncycastle.jce.provider.BouncyCastleProvider());

		url=new URL(this.config.get("url"));
		
		this.requestGenerator=new TimeStampRequestGenerator();
		this.requestGenerator.setCertReq(true);
		
		CertificateFactory certificateFactory=CertificateFactory.getInstance("X.509");
		String encodedCert=this.config.get("cert.tsa");
		X509Certificate tsaCert=(X509Certificate)certificateFactory.generateCertificate(new ByteArrayInputStream(Base64.decodeBase64(encodedCert)));
		JcaSimpleSignerInfoVerifierBuilder verifierBuilder=new JcaSimpleSignerInfoVerifierBuilder();
		this.signerVerifier=verifierBuilder.build(tsaCert);
		
		this.random=new Random();
		
		this.out.start();
		this.logger.log("Initialized");
	}

	private TimeStampResponse probe(TimeStampRequest request) throws IOException, TSPException
	{
		URLConnection 	connection=this.url.openConnection();
						connection.setDoInput(true);
						connection.setDoOutput(true);
						connection.setUseCaches(false);
						connection.setRequestProperty("Content-Type","application/timestamp-query");				
		OutputStream 	outputStream=(connection.getOutputStream());
						outputStream.write(request.getEncoded());
						outputStream.flush();
						outputStream.close();
		InputStream		inputStream=connection.getInputStream();
		TimeStampResponse response=new TimeStampResponse(inputStream);
		inputStream.close();
		return response;
	}
	
	

	public void run()
	{
		byte[] requestHashedMessage=new byte[64];
		double start=0, end=0;
		BigInteger requestNonce;
		this.logger.log("running");
		
		this.running=true;
		while(this.running)
		{
			this.random.nextBytes(requestHashedMessage);
			requestNonce=new BigInteger(512,this.random);
			TimeStampRequest request=requestGenerator.generate(TSPAlgorithms.SHA512,requestHashedMessage,requestNonce);
			
			end=0;
			start=System.currentTimeMillis();

			try
			{
				TimeStampResponse response=probe(request);
				end=System.currentTimeMillis();
				TimeStampToken timestampToken=response.getTimeStampToken();
				timestampToken.validate(this.signerVerifier);
				AttributeTable table=timestampToken.getSignedAttributes();
				
				TimeStampTokenInfo  tokenInfo=timestampToken.getTimeStampInfo();
				BigInteger 			responseNonce=tokenInfo.getNonce();
				byte[] 				responseHashedMessage=tokenInfo.getMessageImprintDigest();
				long				genTimeSeconds=(tokenInfo.getGenTime().getTime())/1000;
				long				currentTimeSeconds=(long)(start+((end-start)/2))/1000;
				
				if(!responseNonce.equals(requestNonce))
				{
					error("Response has Incorrect Nonce");
				}
				else if(!Arrays.equals(responseHashedMessage,requestHashedMessage))
				{
					error("Response has Incorrect Hashed Message");
				}
				else if(table.get(PKCSObjectIdentifiers.id_aa_signingCertificate)==null)
				{
					error("Response Is Missing SigningCertificate");
				}
				else
				{
					ok("granted and validated");
					this.out.put(this.prefix+".tspprobe.clockskew",(genTimeSeconds-currentTimeSeconds)*1000);
				}
			}
			catch(TSPException tspEx)
			{
				error("TSP Exception: " + tspEx.getMessage());
			}
			catch(IOException iox)
			{
				error("I/O Exception: " + iox.getMessage());
			}
			catch(Exception ex)
			{
				error("Unexpected Exception: " + ex.getMessage() + " Please Fix TSPProbe to handle this properly.");
			}
			finally
			{
				if(end==0)
					end=System.currentTimeMillis();
			}

			this.out.put(this.prefix+".tspprobe.responsetime",(end-start));

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
	
	private void error(String reason)
	{
		this.succeeds(false,reason);
	}
	
	private void ok(String joy)
	{
		this.succeeds(true,joy);
	}
	
	private void succeeds(boolean succeeds, String message)
	{
		this.out.put(this.prefix+".tspprobe.result",succeeds?"0":"1");
		if(message!=null)
			this.out.put(this.prefix+".tspprobe.result.comment",message.replace('=',':').replace('\n',' '));
	}

	public static void main(String[] args) throws Exception
	{
		new TSPProbe().run();
	}
}


