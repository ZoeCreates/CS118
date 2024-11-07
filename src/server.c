#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>
#include <stdbool.h>

#define MSS 1012 // Maximum Segment Size (payload size)
#define TIMEOUT 1 // Retransmission timeout in seconds

// Diagnostic messages
#define RECV 0
#define SEND 1
#define RTOS 2
#define DUPA 3

//define the packet struct 
typedef struct {
    uint32_t ack;           // Acknowledgment number
    uint32_t seq;           // Sequence number
    uint16_t length;        // Length of payload
    uint8_t flags;          // Flags for SYN/ACK
    uint8_t unused;         // Unused byte
    uint8_t payload[MSS];   // Data payload
} packet;


//debugging function, use fprintf to print to the console
static inline void print_diag(packet* pkt, int diag) {
    switch (diag) {
    case RECV:
        fprintf(stderr, "RECV");
        break;
    case SEND:
        fprintf(stderr, "SEND");
        break;
    case RTOS:
        fprintf(stderr, "RTOS");
        break;
    case DUPA:
        fprintf(stderr, "DUPS");
        break;
    }

    bool syn = pkt->flags & 0b01;
    bool ack = pkt->flags & 0b10;
    fprintf(stderr, " %u ACK %u SIZE %hu FLAGS ", ntohl(pkt->seq),
            ntohl(pkt->ack), ntohs(pkt->length));
    if (!syn && !ack) {
        fprintf(stderr, "NONE");
    } else {
        if (syn) {
            fprintf(stderr, "SYN ");
        }
        if (ack) {
            fprintf(stderr, "ACK ");
        }
    }
    fprintf(stderr, "\n");
}

// Function to send an acknowledgment packet with the next expected sequence number

//client_addr: A pointer to the sockaddr_in structure that contains the client's address information (IP and port).

//ack_num: The acknowledgment number, which is the next sequence number the server expects to receive from the client. This tells the client that all bytes up to (but not including) this sequence number have been received correctly.
void send_ack(int sockfd, struct sockaddr_in *client_addr, socklen_t client_len, uint32_t ack_num) {
    packet ack_packet = {0};
    //ack_num is converted to network byte order using htonl()
    ack_packet.ack = htonl(ack_num);
    //the second-least significant bit represents the ACK flag. Setting this bit to 1 marks the packet as an acknowledgment.
    ack_packet.flags = 1 << 1;  // Set ACK flag
    
    //If The sendto function sends the ack_packet to the client over the socket:
    if (sendto(sockfd, &ack_packet, sizeof(ack_packet), 0, (struct sockaddr*) client_addr, client_len) < 0) {
        perror("Send ACK failed");
    }
}

int main(int argc, char **argv) {
  if (argc < 2) {
    fprintf(stderr, "Usage: server <port>\n");
    exit(1);
  }

  /* Create sockets */
  int sockfd = socket(AF_INET, SOCK_DGRAM, 0);
  // use IPv4  use UDP
  // Error if socket could not be created
  if (sockfd < 0)
    return errno;

  // Set socket for nonblocking
  int flags = fcntl(sockfd, F_GETFL);
  flags |= O_NONBLOCK;
  fcntl(sockfd, F_SETFL, flags);

  // Setup stdin for nonblocking
  flags = fcntl(STDIN_FILENO, F_GETFL);
  flags |= O_NONBLOCK;
  fcntl(STDIN_FILENO, F_SETFL, flags);

  /* Construct our address */
  struct sockaddr_in server_addr;
  server_addr.sin_family = AF_INET;         // use IPv4
  server_addr.sin_addr.s_addr = INADDR_ANY; // accept all connections
                                            // same as inet_addr("0.0.0.0")
                                            // "Address string to network bytes"
  // Set receiving port
  int PORT = atoi(argv[1]);
  server_addr.sin_port = htons(PORT); // Big endian

  /* Let operating system know about our config */
  int did_bind =
      bind(sockfd, (struct sockaddr *)&server_addr, sizeof(server_addr));
  // Error if did_bind < 0 :(
  if (did_bind < 0)
    return errno;

  struct sockaddr_in client_addr; // Same information, but about client
  socklen_t s = sizeof(struct sockaddr_in);
  char buffer[1024];

  int client_connected = 0;

  // Listen loop
  while (1) {
    packet pkt = {0};
    // Receive from socket
    // int bytes_recvd = recvfrom(sockfd, &buffer, sizeof(buffer), 0,
    //                            (struct sockaddr *)&client_addr, &s);
    int bytes_recvd = recvfrom(sockfd, &pkt, sizeof(pkt), 0, (struct sockaddr *)&client_addr, &s);

  

    if (bytes_recvd <= 0 && !client_connected)
      continue;
    client_connected = 1; // At this point, the client has connected and sent data

    // Data available to write
    if (bytes_recvd > 0) { 
      
      
      //store the sequence number and acknowledgment number from the received packet
      uint32_t recv_seq = ntohl(pkt.seq);
      uint32_t recv_ack = ntohl(pkt.ack);

      //handling three way handshake 

      //set the (S)YN on 
      //If the (S)YN flag is on, this means that this packet seeks to synchronize sequence numbers (by providing an initial one in the SEQ field)
      if (pkt.flags & 1) {
        // Respond to SYN with SYN-ACK
        print_diag(&pkt, RECV);
        packet syn_ack_packet = {0};
        syn_ack_packet.seq = htonl(rand() % 10000);//create a random initial sequence number for server
        syn_ack_packet.ack = htonl(recv_seq + 1);
        syn_ack_packet.flags = (1 << 1) | 1;//0000 0011 -> Both SYN and ACK flags set
        
        sendto(sockfd, &syn_ack_packet, sizeof(syn_ack_packet), 0, (struct sockaddr*)&client_addr, s);
        print_diag(&syn_ack_packet, SEND);
      }
      else if (pkt.flags & (1 << 1)) {  // ACK flag is set
              print_diag(&pkt, RECV);
            }
      else{
        //handle incoming data packet(in coherence)
        if (recv_seq == recv_ack) {
          print_diag(&pkt, RECV);
          //write data to standard output 
          write(STDOUT_FILENO, pkt.payload, ntohs(pkt.length));
          //Acknowledge received data
          send_ack(sockfd, &client_addr, s, recv_seq + ntohs(pkt.length));
          }
        else{
          print_diag(&pkt, DUPA);
          send_ack(sockfd, &client_addr, s, recv_ack); // Re-send current ACK to request missing packets
        } 
        }
    }
    else if (bytes_recvd < 0 && errno != EAGAIN && errno != EWOULDBLOCK) {
            perror("Receive failed");
          }

    
}

}
