import socket
import time
import random
import fcntl
import os
import subprocess
import string


class ProcessRunner():
    def __init__(self, cmd, data, stderr_file=None):
        super().__init__()
        self.cmd = cmd
        self.process = None
        self.stdout = b""
        self.data = data
        filename = randomword(10)
        f = open(f'/autograder/{filename}', 'wb')
        f.write(data)
        os.system(f'chmod o+r /autograder/{filename}')
        f.close()
        self.f = open(f'/autograder/{filename}', 'rb')

        if stderr_file:
            self.stderr_file = open(f'/autograder/submission/{stderr_file}', 'wb')
        else:
            self.stderr_file = open(f'/autograder/submission/err{randomword(10)}', 'wb')

    def run(self):
        self.process = subprocess.Popen(self.cmd.split(
        ), stdin=self.f, stdout=subprocess.PIPE, stderr=self.stderr_file, bufsize=0)
        if self.process.stdout:
            os.set_blocking(self.process.stdout.fileno(), False)

    @staticmethod
    def run_two_until_size_or_timeout(runner1, runner2, size1, size2, timeout):
        runner1.run()
        time.sleep(0.1)
        runner2.run()
        start_time = time.time()
        runner1_finish = False
        runner2_finish = False
        while time.time() - start_time < timeout:
            output1 = runner1.process.stdout.read(2000)
            if output1:
                runner1.stdout += output1
                if len(runner1.stdout) >= size1:
                    runner1_finish = True

            output2 = runner2.process.stdout.read(2000)
            if output2:
                runner2.stdout += output2
                if len(runner2.stdout) >= size2:
                    runner2_finish = True

            if runner1_finish and runner2_finish:
                break

        # Close stdouts
        runner1.process.stdout.close()
        runner2.process.stdout.close()

        # Kill processes
        runner1.process.kill()
        runner2.process.kill()
        runner1.process.wait()
        runner2.process.wait()

        # Close files
        runner1.stderr_file.close()
        runner2.stderr_file.close()
        runner1.f.close()
        runner2.f.close()


def randomword(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for _ in range(length))


def byte_diff(bytes1, bytes2):
    min_len = min(len(bytes1), len(bytes2))
    max_len = max(len(bytes1), len(bytes2))
    differing_bytes = sum(b1 != b2 for b1, b2 in zip(
        bytes1[:min_len], bytes2[:min_len]))
    differing_bytes += (max_len - min_len)
    return round((differing_bytes / max_len if max_len > 0 else 1) * 100, 2)


def proxy(client_port, server_port, loss_rate, reorder_rate):
    random.seed(4322)

    cli_serv_buffer = []
    serv_cli_buffer = []

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    fcntl.fcntl(s, fcntl.F_SETFL, os.O_NONBLOCK)
    fcntl.fcntl(c, fcntl.F_SETFL, os.O_NONBLOCK)
    c.bind(('localhost', client_port))
    c_addr = None

    last_flush = int(time.time() * 1000)

    while True:
        try:
            data, c_addr = c.recvfrom(4096)
            if len(data) > 2000 or len(data) <= 0:
                continue

            if random.random() > loss_rate:
                if random.random() > reorder_rate:
                    # send immediately
                    s.sendto(data, ('localhost', server_port))
                else:
                    # store in buffer
                    cli_serv_buffer.append(data)
            else:
                continue
        except BlockingIOError:
            pass

        try:
            data, _ = s.recvfrom(4096)
            if len(data) > 2000 or len(data) <= 0:
                continue
            if random.random() > loss_rate:
                if c_addr:
                    if random.random() > reorder_rate:
                        c.sendto(data, c_addr)
                    else:
                        serv_cli_buffer.append(data)
                else:
                    continue
            else:
                continue
        except BlockingIOError:
            pass

        epoch_ms = int(time.time() * 1000)

        # Flush reorder buffer if more than 300 ms
        if len(cli_serv_buffer) > 5 or (len(cli_serv_buffer) and epoch_ms - last_flush > 300):
            random.shuffle(cli_serv_buffer)
            for d in cli_serv_buffer:
                s.sendto(d, ('localhost', server_port))
            cli_serv_buffer = []
            last_flush = epoch_ms

        if len(serv_cli_buffer) > 5 or (len(serv_cli_buffer) and epoch_ms - last_flush > 300):
            random.shuffle(serv_cli_buffer)
            for d in serv_cli_buffer:
                if c_addr:
                    c.sendto(d, c_addr)
            serv_cli_buffer = []
            last_flush = epoch_ms

