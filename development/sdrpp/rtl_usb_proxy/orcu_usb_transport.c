// SPDX-License-Identifier: MIT
// OpenRoadCode client for the Android Bridge RTL-SDR USB transport.
#include <arpa/inet.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define ORCU_MAGIC 0x4f524355u
#define ORCU_VERSION 1u
#define ORCU_OP_INFO 1u
#define ORCU_OP_CLAIM 2u
#define ORCU_OP_RELEASE 3u
#define ORCU_OP_CONTROL 4u
#define ORCU_OP_BULK 5u
#define ORCU_OP_RESET 6u
#define ORCU_OP_CLOSE 7u

static int write_all(int fd,const void *p,size_t n){const uint8_t *b=p;while(n){ssize_t r=send(fd,b,n,0);if(r<=0)return -1;b+=r;n-=r;}return 0;}
static int read_all(int fd,void *p,size_t n){uint8_t *b=p;while(n){ssize_t r=recv(fd,b,n,0);if(r<=0)return -1;b+=r;n-=r;}return 0;}
static int put32(int fd,uint32_t v){v=htonl(v);return write_all(fd,&v,4);}
static int get32(int fd,int32_t *v){uint32_t n;if(read_all(fd,&n,4))return -1;*v=(int32_t)ntohl(n);return 0;}
static int request(int fd,uint16_t op){uint32_t m=htonl(ORCU_MAGIC);uint16_t v=htons(ORCU_VERSION),o=htons(op);return write_all(fd,&m,4)||write_all(fd,&v,2)||write_all(fd,&o,2)?-1:0;}

static int result(int fd,uint8_t *data,size_t cap,int *transferred){
    int32_t rc,len;if(get32(fd,&rc)||get32(fd,&len)||len<0)return -1;
    if((size_t)len>cap)return -1;
    if(len&&read_all(fd,data,(size_t)len))return -1;
    if(transferred)*transferred=len;
    return rc;
}

int orcu_connect(const char *host,uint16_t port){
    int fd=socket(AF_INET,SOCK_STREAM,0);if(fd<0)return -1;
    struct sockaddr_in a={0};a.sin_family=AF_INET;a.sin_port=htons(port);
    if(inet_pton(AF_INET,host,&a.sin_addr)!=1||connect(fd,(struct sockaddr*)&a,sizeof(a))<0){close(fd);return -1;}
    return fd;
}

int orcu_claim(int fd,int iface,int force){
    if(request(fd,ORCU_OP_CLAIM)||put32(fd,(uint32_t)iface))return -1;
    uint8_t f=force?1:0;if(write_all(fd,&f,1))return -1;
    return result(fd,NULL,0,NULL);
}

int orcu_release(int fd,int iface){
    if(request(fd,ORCU_OP_RELEASE)||put32(fd,(uint32_t)iface))return -1;
    return result(fd,NULL,0,NULL);
}

int orcu_control(int fd,int request_type,int req,int value,int index,uint8_t *buf,int len,int timeout_ms){
    if(len<0)return -1;
    if(request(fd,ORCU_OP_CONTROL)||put32(fd,request_type)||put32(fd,req)||put32(fd,value)||put32(fd,index)||put32(fd,len)||put32(fd,timeout_ms))return -1;
    if(!(request_type&0x80)&&len&&write_all(fd,buf,(size_t)len))return -1;
    int got=0;int rc=result(fd,(request_type&0x80)?buf:NULL,(request_type&0x80)?(size_t)len:0,&got);
    return rc<0?rc:rc;
}

int orcu_bulk_read(int fd,int endpoint,uint8_t *buf,int len,int timeout_ms){
    if(len<0)return -1;
    if(request(fd,ORCU_OP_BULK)||put32(fd,endpoint)||put32(fd,len)||put32(fd,timeout_ms))return -1;
    return result(fd,buf,(size_t)len,NULL);
}

int orcu_reset(int fd){
    if(request(fd,ORCU_OP_RESET))return -1;
    return result(fd,NULL,0,NULL);
}

void orcu_close(int fd){
    if(fd<0)return;
    request(fd,ORCU_OP_CLOSE);
    int32_t rc,len;get32(fd,&rc);get32(fd,&len);
    close(fd);
}

#ifdef ORCU_SMOKE_TEST
int main(void){
    int fd=orcu_connect("127.0.0.1",35100);
    if(fd<0){perror("connect 127.0.0.1:35100");return 1;}
    int rc=orcu_claim(fd,0,1);
    printf("claim interface 0: %s (%d)\n",rc==0?"OK":"FAILED",rc);
    if(rc==0){
        rc=orcu_release(fd,0);
        printf("release interface 0: %s (%d)\n",rc==0?"OK":"FAILED",rc);
    }
    orcu_close(fd);
    return rc==0?0:1;
}
#endif
