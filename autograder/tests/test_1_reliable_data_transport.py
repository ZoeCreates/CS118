import unittest
import multiprocessing
import os

import test_0_compilation

from random import randbytes, choice
from string import ascii_letters
from gradescope_utils.autograder_utils.decorators import weight, number, hide_errors
from utils import proxy, byte_diff, ProcessRunner

DROP_RATE = 0.1
REORDER_RATE = 1
start_port = 8080


class TestRDT(unittest.TestCase):

    def make_test(self, size1: int, size2: int, timeout: int, use_ascii: bool, ref_client: bool, ref_server: bool, drop_rate: float, reorder_rate: float, name: str) -> None:
        global start_port
        start_port += 1
        server_port = start_port
        start_port += 1
        client_port = start_port

        # Find dir
        paths_to_check = [
            "/autograder/submission/project/Makefile",
            "/autograder/submission/Makefile"
        ]
        
        makefile_dir = None
        for path in paths_to_check:
            if os.path.isfile(path):
                makefile_dir = os.path.dirname(path)
                break

        if makefile_dir is None:
            print("Makefile not found. Verify your submission has the correct files.")
            self.fail()

        # Start proxy
        p_thread = multiprocessing.Process(target=proxy, args=(
            client_port, server_port, drop_rate, reorder_rate))
        p_thread.start()

        # Generate random file to send
        if use_ascii:
            file1 = b''.join([choice(ascii_letters).encode()
                            for _ in range(size1)])
            file2 = b''.join([choice(ascii_letters).encode()
                            for _ in range(size2)])
        else:
            file1 = randbytes(size1)
            file2 = randbytes(size2)

        # Create server and client
        if ref_server:
            server_runner = ProcessRunner(
                f'/autograder/source/src/server {server_port}', file1, name + "_refserver.out")
        else:
            server_runner = ProcessRunner(
                f'runuser -u student -- {makefile_dir}/server {server_port}', file1, name + "_yourserver.out")

        if ref_client:
            client_runner = ProcessRunner(
                f'/autograder/source/src/client localhost {client_port}', file2, name + "_refclient.out")
        else:
            client_runner = ProcessRunner(
                f'runuser -u student -- {makefile_dir}/client localhost {client_port}', file2, name + "_yourclient.out")

        # Run both processes and stop when both have outputted the right amount
        # of bytes (or on timeout)
        ProcessRunner.run_two_until_size_or_timeout(
            server_runner, client_runner, size1, size2, timeout)
        p_thread.terminate()

        # Compare both the server and client output to original file
        fail = False
        if file2 != server_runner.stdout:
            fail = True

            if not ref_server and not ref_client:
                print("Your server didn't produce the expected result.")
                print(
                    f"We inputted {size2} bytes in your client and we received {len(server_runner.stdout)} bytes ", end='')
            elif ref_server:
                print("Your client didn't send data back to our server correctly.")
                print(
                    f"We inputted {size2} bytes in your client and we received {len(server_runner.stdout)} bytes ", end='')
            else:
                print("Your server didn't receive data from our client correctly.")
                print(
                    f"We sent {size2} bytes and your server received {len(server_runner.stdout)} bytes ", end='')
            print(
                f'with a percent difference of {byte_diff(file2, server_runner.stdout)}%')

        if file1 != client_runner.stdout:
            fail = True

            if not ref_server and not ref_client:
                print("Your client didn't produce the expected result.")
                print(
                    f"We inputted {size1} bytes in your server and we received {len(client_runner.stdout)} bytes ", end='')
            elif ref_client:
                print("Your server didn't send data back to our client correctly.")
                print(
                    f"We inputted {size1} bytes in your server and we received {len(client_runner.stdout)} bytes ", end='')
            else:
                print("Your client didn't receive data from our server correctly.")
                print(
                    f"We sent {size1} bytes and your client received {len(client_runner.stdout)} bytes ", end='')
            print(
                f'with a percent difference of {byte_diff(file1, client_runner.stdout)}%')

        if fail:
            self.fail()

    @weight(10)
    @number(1.1)
    @hide_errors()
    def test_self_ascii(self):
        """Data Transport (Your Client <-> Your Server): Small, ASCII only file (20 KB)"""
        if test_0_compilation.failed:
            self.fail()

        FILE_SIZE = 20000
        TIMEOUT = 3

        self.make_test(FILE_SIZE, FILE_SIZE, TIMEOUT, True, False, False,
                       0, 0, self.test_self_ascii.__name__)

    @weight(10)
    @number(1.2)
    @hide_errors()
    def test_self(self):
        """Data Transport (Your Client <-> Your Server): Small file (20 KB)"""
        if test_0_compilation.failed:
            self.fail()

        FILE_SIZE = 20000
        TIMEOUT = 3

        self.make_test(FILE_SIZE, FILE_SIZE, TIMEOUT, False, False,
                       False, 0, 0, self.test_self.__name__)

    @weight(20)
    @number(1.3)
    @hide_errors()
    def test_client_normal(self):
        """Data Transport (Your Client <-> Reference Server): Small file (20 KB)"""
        if test_0_compilation.failed:
            self.fail()

        FILE_SIZE = 20000
        TIMEOUT = 3

        self.make_test(FILE_SIZE, FILE_SIZE, TIMEOUT, False, False, True,
                       0, 0, self.test_client_normal.__name__)

    @weight(20)
    @number(1.4)
    @hide_errors()
    def test_client_only(self):
        """Data Transport (Your Client <-> Reference Server): Small file (20 KB, client only)"""
        if test_0_compilation.failed:
            self.fail()

        FILE_SIZE = 20000
        TIMEOUT = 3

        self.make_test(0, FILE_SIZE, TIMEOUT, False, False, True,
                       0, 0, self.test_client_only.__name__)

    @weight(20)
    @number(1.5)
    @hide_errors()
    def test_server_normal(self):
        """Data Transport (Reference Client <-> Your Server): Small file (20 KB)"""
        if test_0_compilation.failed:
            self.fail()

        FILE_SIZE = 20000
        TIMEOUT = 3

        self.make_test(FILE_SIZE, FILE_SIZE, TIMEOUT, False, True, False,
                       0, 0, self.test_server_normal.__name__)

    @weight(20)
    @number(1.6)
    @hide_errors()
    def test_server_only(self):
        """Data Transport (Reference Client <-> Your Server): Small file (20 KB, server only)"""
        if test_0_compilation.failed:
            self.fail()

        FILE_SIZE = 20000
        TIMEOUT = 3

        self.make_test(FILE_SIZE, 1, TIMEOUT, False, True, False,
                       0, 0, self.test_server_only.__name__)
