# Networking Research
This repo contains demonstration programs for 

## Epoll Edge-trigger and Non-blocking Server
There is a lot of mysterious code out there related to the epoll edge-triggered
feature so I decided to write a simple TCP server using epoll to test out some
of the concepts.  See `epoll_server.c` for the code.

### Running the Program

Start `epoll_server` in one window. Do `epoll_server -h` to see a list of
command-line arguments.

Use `nc` (or `netcat`) to generate traffic to the server:

{code}
test
{code}

### Edge-triggered Reading

