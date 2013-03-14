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

#define RECORD_IOV_SIZE 4
#define MAX_RECORDS_PER_SHUTTLE (IOV_MAX/RECORD_IOV_SIZE)

int tcp_listen(const char *host, const char *serv, socklen_t *addrlenp)       
{                                                                         
  int       listenfd, n;                                                  
  const int   on = 1;                                                     
  struct addrinfo hints, *res, *ressave;                                  
                                                                          
  bzero(&hints, sizeof(struct addrinfo));                                 
  hints.ai_flags = AI_PASSIVE;                                            
  hints.ai_family = AF_UNSPEC;                                            
  hints.ai_socktype = SOCK_STREAM;                                        
                                                                          
  if((n = getaddrinfo(host, serv, &hints, &res)) != 0)
	{
    fprintf(stderr,"tcp_listen error for %s, %s: %s", host, serv, gai_strerror(n));
		exit(1);
	}

  ressave = res;                                                          
                                                                          
  do {                                                                    
    listenfd = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    if (listenfd < 0)                                                     
      continue;   /* error, try next one */                               
                                                                          
    setsockopt(listenfd, SOL_SOCKET, SO_REUSEADDR, &on, sizeof(on));      
    if (bind(listenfd, res->ai_addr, res->ai_addrlen) == 0)               
      break;      /* success */                                           
                                                                          
    close(listenfd);  /* bind error, close and try next one */            
  } while ( (res = res->ai_next) != NULL);                                
                                                                          
  if (res == NULL) 
	{           
    fprintf(stderr,"tcp_listen error for %s, %s", host, serv);
		exit(1);
	}
                                                                          
  listen(listenfd,5);
                                                                          
  if (addrlenp)                                                           
    *addrlenp = res->ai_addrlen;  /* return size of protocol address */   
                                                                          
  freeaddrinfo(ressave);                                                  
  return(listenfd);                                                       
}                        

void web_child(void* arg)                                                     
{
	int i;
	char label[16],value[16];
	char label_value_separator[1],record_separator[1];
	struct iovec iov[IOV_MAX];
	int connfd=(int)arg;

	pthread_detach(pthread_self());
	
  strcpy(label,"label");
	strcpy(value,"value");
	*label_value_separator='=';
	*record_separator='\n';

	for(i=0;i<MAX_RECORDS_PER_SHUTTLE-1;i++)
	{
		iov[i*RECORD_IOV_SIZE].iov_base=label;
		iov[i*RECORD_IOV_SIZE].iov_len=5;
		iov[i*RECORD_IOV_SIZE+1].iov_base=label_value_separator;
		iov[i*RECORD_IOV_SIZE+1].iov_len=1;	
		iov[i*RECORD_IOV_SIZE+2].iov_base=value;
		iov[i*RECORD_IOV_SIZE+2].iov_len=5;
		iov[i*RECORD_IOV_SIZE+3].iov_base=record_separator;
		iov[i*RECORD_IOV_SIZE+3].iov_len=1;
	}
	iov[i*RECORD_IOV_SIZE].iov_base=record_separator;
	iov[i*RECORD_IOV_SIZE].iov_len=1;

  while(writev(connfd,iov,IOV_MAX-3)>0)
	{
		usleep(100000);
  }

	close(connfd);
	return;
}
 
int main(int argc, char **argv)
{
	int				listenfd, connfd;
	pthread_t		tid;
	socklen_t		clilen, addrlen;
	struct sockaddr	*cliaddr;

	if (argc == 2)
	{
		listenfd = tcp_listen(NULL, argv[1], &addrlen);
	}
	else if (argc == 3)
	{
		listenfd = tcp_listen(argv[1], argv[2], &addrlen);
	}
	else
	{
		fprintf(stderr,"usage: serv06 [ <host> ] <port#>");
		exit(1);
	}

	cliaddr = malloc(addrlen);

	for(;;)
	{ 
		clilen = addrlen;
		connfd = accept(listenfd, cliaddr, &clilen);
		pthread_create(&tid, NULL, &web_child, (void *) connfd);
	}
}

