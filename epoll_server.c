/**
 * epoll_server.c
 *
 * A connection server using epoll for demonstration purposes.  The server can
 * be configured to:
 * 1. use a static port or dynamically assigned by the kernel to listen on
 * 2. use blocking or nonblocking input from the clients
 * 3. use level-triggered or edge-triggered epoll_wait interface 
 * 
 * There is very little recovery code.  Nothing should fail but if it does then
 * the program will die.
 *
 * This has been tested on Ubuntu 16.04 compiled using: gcc -g -o epoll_server epoll_server.c
 *
 * Copyright 2018 Dahetral Systems
 * David Turvene <dturvene at dahetral dot com>
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/epoll.h>
#include <errno.h>
#include <time.h>

#define die(msg)  do { perror(msg); exit(EXIT_FAILURE); } while (0)

/* write listening port here for local clients to access */
#define PORTFILE "/tmp/server.port"

/********************* command line arguments ************/
char *arguments = "\n"						\
	" -n: set reads to nonblocking mode\n"			\
	" -f portnum: fixed port to listen on\n"		\
	" -e: edge-triggered epoll\n"				\
	" -h: this help\n";

/* this are hack debug globals for demonstration so I don't have
 * to pass around arguments or a context block 
 */
static int nonblocking_read_flag = 0;
static int et_flag = 0;
static int fixed_portnum = 0;

int cmdline_args(int argc, char *argv[]) {
	int opt;
	int argcnt = 0;
	
	while((opt = getopt(argc, argv, "nef:h")) != -1) {
		switch(opt) {
		case 'n':
			nonblocking_read_flag = 1;
			break;
		case 'e':
			et_flag = 1;
			break;
		case 'f':
			fixed_portnum = strtoul(optarg, NULL, 0);
			break;
		case 'h':
			fprintf(stderr, "Usage: %s args: %s\n", argv[0], arguments);
			exit(0);
		default:
			argcnt++;
			break;
		}
	}

	return argcnt;
}

/**
 * @param fd    the file descriptor to set to non-blocking
 *
 * Using fcntl is necessary when accepting an incoming stream because the
 * socket has already been created so cannot do a 
 * socket(domain, SOCK_NONBLOCK...) on it.
 */
void set_nonblocking_read(int fd)
{
	int flags, s;
	
	flags = fcntl(fd, F_GETFL, 0);
	if (flags == -1)
		die("fcntl get");
	
	flags |= O_NONBLOCK;
	s = fcntl(fd, F_SETFL, flags);
	if (s == -1)
		die("fcntl set");
}

/**
 * @param epoll_fd    the local epoll file descriptor
 * @param remote_fd   the remote file descriptor to add to the poll list
 */
void add_fd_to_epoll(int epoll_fd, int remotefd)
{
	struct epoll_event event;

	event.data.fd = remotefd;
	event.events = EPOLLIN;
	if (nonblocking_read_flag) {
		set_nonblocking_read(remotefd);
	}

	if (et_flag) {
		event.events |= EPOLLET;
	}

	fprintf(stderr, "fd=%d set to %s read and %s epoll_wait\n", remotefd,
		nonblocking_read_flag ? "Non-blocking" : "Blocking",
		et_flag ? "Edge-triggered" : "Level-triggered"
		);

	
	if (-1 == epoll_ctl(epoll_fd, EPOLL_CTL_ADD, remotefd, &event))
		die("epoll_ctl adding a newfd");
}


/**
 * @param fd       The file descriptor for which to get socket info
 *
 * write dynamic port to a temp file to coordiante with co-located clients
 */
void dump_port_info(int fd)
{
	struct sockaddr_in addr;
	socklen_t len = sizeof(addr);
	FILE *FD;
	if (-1 == getsockname(fd, (struct sockaddr *)&addr, &len))
		die("getsockname dyn port");
	if (NULL == (FD=fopen(PORTFILE, "w+")) )
		die("fopen");
	fprintf(FD,"%d\n", ntohs(addr.sin_port));
	fclose(FD);

	fprintf(stderr, "writing port=%d to %s\n", ntohs(addr.sin_port), PORTFILE);
}

/**
 * Create the local socket and bind to listen for incoming connections.
 * This uses a pre-defined port and is the simplest setup.  However, if
 * the port is already taken, this will die.
 *
 * @return the file descriptor to use for listening on the socket
 */
int create_and_bind_fixed(void)
{
	int listenfd;
	struct sockaddr_in serv_addr;

	if (-1 == (listenfd=socket(AF_INET, SOCK_STREAM, 0)))
		die("socket");

	memset(&serv_addr, 0, sizeof(serv_addr));
	serv_addr.sin_family = AF_INET;
	serv_addr.sin_addr.s_addr = htonl(INADDR_ANY);
	serv_addr.sin_port = htons(fixed_portnum);

	if (-1 == bind(listenfd, (struct sockaddr*) &serv_addr, sizeof(serv_addr)))
		die("bind");

	return listenfd;
}

/**
 * Create a local socket and bind to listen for incoming connections.
 * This uses the first available socket provided by the kernel.
 *
 * @return the file descriptor to use for listening on the socket
*/
int create_and_bind_dyn(void)
{
	struct addrinfo hints;
	struct addrinfo *result, *rp;
	int listenfd;
	int s;
	int enable = 1;
	int found = 0;

	memset (&hints, 0, sizeof (struct addrinfo));
	hints.ai_family = AF_UNSPEC;     /* All address families */
	hints.ai_socktype = SOCK_STREAM; /* Only Streams */
	hints.ai_flags = AI_PASSIVE;     /* Accept on all interfaces, node must be NULL */
	hints.ai_protocol = IPPROTO_TCP; /* TCP only */

	if (0 != (s=getaddrinfo(NULL, "0", &hints, &result)))
		die(gai_strerror(s));

	/* All we want is the first port and if it fails for some reason then die
	 * See man:getaddrinfo for boilerplate loop, which breaks out on the
	 * first bind anyway
	 */
	if (result)
		rp = result;
	else
		die("no result returned from getaddrinfo");

	/* need to put the listener into NONBLOCK to multiplex */
	if (-1 == (listenfd=socket(rp->ai_family,
				   rp->ai_socktype,
				   rp->ai_protocol)))
	{
		/* this should never happen so something is hosed... */
		die("listening socket failed");
	}
	
	if (-1 == setsockopt(listenfd, SOL_SOCKET, SO_REUSEADDR, &enable, sizeof(enable)))
		die("setsockopt");
	
	/* bind will return 0 for success or -1 otherwise */
	if (-1 == bind(listenfd, rp->ai_addr, rp->ai_addrlen)) {
		die("bind");
	}

	/* free dynamically created result */
	freeaddrinfo(result);
	
	return listenfd;
}

/** 
 *
 * @param listen_fd    the listening socket to accept the incoming connection
 * @param epoll_fd     the epoll file descriptor
 * 
 * Accepts and incoming connection and adds it the epoll list.
 */
void add_remote(int listen_fd, int epoll_fd)
{
	struct sockaddr in_addr;
	socklen_t in_len = sizeof(in_addr);
	char hbuf[32], sbuf[32];
	int infd;
		
	if (-1 == (infd=accept(listen_fd, &in_addr, &in_len))) {
		die("accept");
	}

	/* debug about incoming connection */
	if (0 == getnameinfo(&in_addr, in_len,
			     hbuf, sizeof(hbuf),
			     sbuf, sizeof(sbuf),
			     0)) {
		fprintf(stderr, "Accepting connection from host=%s port=%s\n", hbuf, sbuf);
	}

	/* add accepted infd to epoll list */
	add_fd_to_epoll(epoll_fd, infd);
}

/**
 * @param remote_fd       the remote file descriptor from which to read
 * @return total number of characters read
 * 
 * Read until the local buffer available data from the remote up to
 * the size of the buffer. It writes the read string to stderr.
 */
int read_client_blocking(int remote_fd)
{
	ssize_t n;
	char buf[4]; /* make a very small buffer to force blocking */

	n = read(remote_fd, buf, sizeof(buf));

	if (n == -1)
		die("read failure");
	else if (n == 0) {
		fprintf(stderr, "closing remote fd=%d\n", remote_fd);
		close(remote_fd);
	} else {
		if (-1 == write(1, buf, n))
			die("write stdout");
	}
	
	return n;
}

/**
 * @param remote_fd       the remote file descriptor from which to read
 * @return total number of characters read
 * 
 * This will read until there is an EWOULDBLOCK error indicating no more
 * data.  It writes the read string to stderr.
 */
int read_client_nonblocking(int remote_fd)
{
	ssize_t n;
	int reading = 1;
	char buf[4];  /* make a very small buffer to force looping */
	int total_n = 0;
	
	do {
		/* read until buffer is full */
		n = read(remote_fd, buf, sizeof(buf));
		if (n == -1) {
			/* This non-blocking read will block so no more data, 
			 * go back to main loop.
			 * NOTE: EWOULDBLOCK is defined as EAGAIN
			 */
			if (errno == EWOULDBLOCK) {
				reading = 0;
			} else
				die("read !EWOULDBLOCK");
		} else if (n == 0) {
			/* EOF, remote closed */
			fprintf(stderr, "closing remote fd=%d\n", remote_fd);
			close(remote_fd);
			reading = 0;
		} else {
			if (-1 == write(1, buf, n))
				die("write stdout");
		}
		total_n += n;
	} while (reading);

	return total_n;
}

/**
 * @param remote_fd       the remote file descriptor from which to read
 * 
 * Selects the appropriate read function and writes out the total number of
 * bytes read.
 */
void read_client(int remote_fd)
{
	int n;

	if (nonblocking_read_flag)
		n = read_client_nonblocking(remote_fd);
	else
		n = read_client_blocking(remote_fd);
	fprintf(stderr, "%s: Reading %d bytes\n", __func__, n);
}


int main (int argc, char *argv[])
{
	int listen_fd, epoll_fd;
	int conn;
	struct epoll_event event, events[4];
	int reading;

	cmdline_args(argc, argv);

	/* this will always be valid */
	if (!fixed_portnum)
		listen_fd = create_and_bind_dyn();
	else
		listen_fd = create_and_bind_fixed();

	/* get the assigned port info and save to a file */
	dump_port_info(listen_fd);

	/* listen for incoming connections */
	if (-1 == listen(listen_fd, 4))
		die("listen");

	if (-1 == (epoll_fd=epoll_create1(0)))
		die("epoll");

	/* set up listening socket 
	 * this does not need to be edge-triggered, only
	 * incoming connections
	 */
	event.data.fd = listen_fd;
	event.events = EPOLLIN;
	if (-1 == epoll_ctl(epoll_fd, EPOLL_CTL_ADD, listen_fd, &event))
		die("epoll_ctl");

	/* add stdin to poll list */
	add_fd_to_epoll(epoll_fd, 0);

	while(1) {
		int i, n;

		/* block waiting for epoll events */
		if (-1 == (n=epoll_wait(epoll_fd, events, 4, -1)))
			die("epoll_wait");

		/* event loop */
		for (i=0; i<n; i++) {

			/* this is a bad event on the remote connection */
			if ((events[i].events & EPOLLERR) ||
			    (events[i].events & EPOLLHUP) ||
			    (!(events[i].events & EPOLLIN))) {
				fprintf(stderr, "epoll error on %d\n", events[i].data.fd);
				close(events[i].data.fd);
				continue;
			}

			if (events[i].data.fd == listen_fd) {
				add_remote(listen_fd, epoll_fd);
			} else {
				read_client(events[i].data.fd);
			}
		} /* event loop */
	} /* while forever */
}
