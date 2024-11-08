#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#include <stdbool.h>
#include <time.h>

#define MSS 1012  // Maximum Segment Size
#define RETRY_DELAY 500000  // 500 ms
#define TIMEOUT 3  // Timeout for retrying the handshake

typedef struct {
    uint32_t ack;          // Acknowledgment number
    uint32_t seq;          // Sequence number
    uint16_t length;       // Length of payload
    uint8_t flags;         // Flags for SYN/ACK
    uint8_t unused;        // Unused byte
    uint8_t payload[MSS];  // Data payload
} packet;

// Diagnostic messages
#define RECV 0
#define SEND 1
#define RTOS 2
#define DUPA 3

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

#define WINDOW_SIZE 20 
packet sending_buffer[WINDOW_SIZE];
int unacknowledged_packets = 0; 
int window_start = 0;



int main(int argc, char **argv) {

  if (argc < 3) {
    fprintf(stderr, "Usage: client <hostname> <port> \n");
    exit(1);
  }

  /* Create sockets */
  int sockfd = socket(AF_INET, SOCK_DGRAM, 0);
  if (sockfd < 0) {
    perror("Socket creation failed");
    return errno;
  }

  /* Construct server address */
  struct sockaddr_in server_addr;
  server_addr.sin_family = AF_INET;
  server_addr.sin_addr.s_addr = inet_addr(strcmp(argv[1], "localhost") == 0 ? "127.0.0.1" : argv[1]);
  int PORT = atoi(argv[2]);
  server_addr.sin_port = htons(PORT);
  socklen_t s = sizeof(struct sockaddr_in);
  char buffer[1024];

  srand(time(NULL));
  uint32_t client_seq = rand() % 1000;
  uint32_t server_seq;

  // Step 2: Send SYN packet to initiate the first handshake
  packet syn_packet = {0};
  syn_packet.seq = htonl(client_seq);
  syn_packet.flags = 1;

  for (int attempt = 0; attempt < TIMEOUT; ++attempt) {
    if (sendto(sockfd, &syn_packet, sizeof(syn_packet), 0, 
               (struct sockaddr *)&server_addr, s) < 0) {
        perror("Send SYN failed");
        close(sockfd);
        return errno;
    }
    print_diag(&syn_packet, SEND);

    packet syn_ack_packet = {0};
    int bytes_recvd = recvfrom(sockfd, &syn_ack_packet, sizeof(syn_ack_packet), 0, 
                               (struct sockaddr *)&server_addr, &s);

    if (bytes_recvd > 0) {
      server_seq = ntohl(syn_ack_packet.seq);
      print_diag(&syn_ack_packet, RECV);
      break;  // Exit retry loop if SYN-ACK received
    }

    usleep(RETRY_DELAY);  // Wait before retrying
    fprintf(stderr, "Retrying SYN...\n");
  }

  // Step 3: Send final ACK to complete handshake
  packet ack_packet = {0};
  ack_packet.seq = htonl(client_seq + 1);
  ack_packet.ack = htonl(server_seq + 1);
  ack_packet.flags = 1 << 1;
  
  if (sendto(sockfd, &ack_packet, sizeof(ack_packet), 0, 
             (struct sockaddr *)&server_addr, s) < 0) {
      perror("Send final ACK failed");
      close(sockfd);
      return errno;
  }
  print_diag(&ack_packet, SEND); 

  // Listen loop
  while (1) {
    // Receive from socket
    int bytes_recvd = recvfrom(sockfd, &buffer, sizeof(buffer), 0,
                               (struct sockaddr *)&server_addr, &s);

    // Data available to write
    if (bytes_recvd > 0) {
      write(STDOUT_FILENO, buffer, bytes_recvd);
    }

    // Read from stdin
    int bytes_read = read(STDIN_FILENO, &buffer, sizeof(buffer));

    // Data available to send from stdin
    if (bytes_read > 0) {
      sendto(sockfd, &buffer, bytes_read, 0, (struct sockaddr *)&server_addr,
             sizeof(struct sockaddr_in));
    }
  }

  return 0;
}


//changes 