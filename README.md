# Networking Research
This repo contains demonstration programs for 

## Epoll Edge-trigger and Non-blocking Server
There is a lot of mysterious code out there related to the epoll edge-triggered
feature so I decided to write a simple TCP server using epoll to test out some
of the concepts.  See `epoll_server.c` for the code.

### Running the Server
Start *epoll_server* in one window.  It will start and listen either a static port you give
it or a dynamic port assigned by the kernel.  Either way, the port will be
written to a temp file for the clients to connect on.


### Running Local Clients
Use *nc* (or *netcat*) in other windows to generate traffic to the server.
These can be interleavened, along with server standard in.

```
nc localhost $(cat /tmp/server.port)
... enter data 
^D to exit
```

```
nc localhost $(cat /tmp/server.port) < /tmp/dumpfile.log
```

### Edge-triggered Reads
If clients are configured for edge-triggered reads, `epoll_wait` will wait for
only NEW data from the client.  If there is un-read data from a previous
stream, it will not be read.  This is best illustrated by starting the server
without putting the clients in non-blocking mode:

```
epoll_server -e
```

and entering some data either from stdin or nc.  The (very small) buffer will
be filled and written

### Non-blocking Reads
If clients are configured for non-blocking reads, `epoll_wait` will wait for
data and then it will all be read.

```
epoll_server -n
```

## Summary
The edge-triggered epoll does not seem to be very helpful.  If I set the
clients to non-blocking and level-triggered it seems to have the same impact as
edge-triggered. 

However, if I set only edge-triggered epoll then it will not read the client
streams correctly.

