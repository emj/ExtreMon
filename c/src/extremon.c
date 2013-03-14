#include "../config.h"
#include <pthread.h>
#include <sys/types.h>
#include <sys/types.h> /* basic system data types */                     
#include <sys/socket.h>  /* basic socket definitions */                  
#include <netinet/in.h>  /* sockaddr_in{} and other Internet defns */    
#include <arpa/inet.h> /* inet(3) functions */                           
#include <errno.h>                                                       
#include <fcntl.h>   /* for nonblocking */                               
#include <netdb.h>                                                       
#include <signal.h>                                                      
#include <stdio.h>                                                       
#include <stdlib.h>                                                      
#include <string.h>                                                      
#include <sys/stat.h>  /* for S_xxx file mode constants */               
#include <sys/uio.h>   /* for iovec{} and readv/writev */                
#include <unistd.h>
#include <limits.h>

#define MAXBUFSIZE 16384
#define MAX_RECORDS_PER_SHUTTLE (IOV_MAX/RECORD_IOV_SIZE)

int main(int argc, char **argv)
{
   int sock, status, socklen;
   char buffer[MAXBUFSIZE];
   struct sockaddr_in saddr;
   struct ip_mreq membership;

   memset(&saddr, 0, sizeof(struct sockaddr_in));
   memset(&membership, 0, sizeof(struct ip_mreq));
   sock = socket(PF_INET, SOCK_DGRAM, IPPROTO_UDP);
   saddr.sin_family = PF_INET;
   saddr.sin_port = htons(1249); 
   saddr.sin_addr.s_addr = htonl(INADDR_ANY); // bind socket to any interface
   status = bind(sock, (struct sockaddr *)&saddr, sizeof(struct sockaddr_in));
   membership.imr_multiaddr.s_addr = inet_addr("224.0.0.1");
   membership.imr_interface.s_addr = INADDR_ANY;
   status = setsockopt(sock, IPPROTO_IP, IP_ADD_MEMBERSHIP, (const void *)&membership, sizeof(struct ip_mreq));
   socklen = sizeof(struct sockaddr_in);
   status = recvfrom(sock, buffer, MAXBUFSIZE, 0, (struct sockaddr *)&saddr, &socklen);
	 printf("%s\n",buffer);
   close(sock);
   return 0;
}

                                                                          
/*  """ subscribe to the multicast Cauldron at a certain port, handler is   
    called with shuttles boiling at that port.                            
                                                                          
    pass an (address,port) tuple indicating what mcast group/port you     
    want to subscribe to, and a handler instance, which should            
    implement a handle_shuttle(self, set) method, then call               
    receive_forever (which blocks): your handle_shuttle method will be    
    called with a set of (label,value) tuples for each shuttle that       
    boils at the group/port you gave.                                     
  """                                                                     
                                                                          
  def __init__(self,mcast_addr,handler):                                  
    (mcast_group,mcast_port)=mcast_addr                                   
    self.handler=handler                                                  
    self.socket=socket.socket(  socket.AF_INET,                           
                                socket.SOCK_DGRAM,                        
                                socket.IPPROTO_UDP)                       
    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)     
    self.socket.bind(('', mcast_port))                                    
    self.socket.setsockopt( socket.IPPROTO_IP,                            
                            socket.IP_ADD_MEMBERSHIP,                     
                            struct.pack("4sl",                            
                            socket.inet_aton(mcast_group),                
                            socket.INADDR_ANY))                           
    self.shuttle=set()                                                    
                                                                          
                                                                          
  def receive_shuttle(self):                                              
    data=self.socket.recv(131072)                                         
    for line in str(data,'UTF-8').splitlines():                           
      if len(line)>0:                                                     
          labelAndValue=line.split('=')                                   
          if len(labelAndValue)==2:                                       
            self.shuttle.add((labelAndValue[0],labelAndValue[1]))         
    self.handler.handle_shuttle(set(self.shuttle))                        
    self.shuttle.clear()                                                  
                                                                          
                                                                          
  def receive_forever(self):                                              
    while True:                                                           
      self.receive_shuttle()                  

*/
