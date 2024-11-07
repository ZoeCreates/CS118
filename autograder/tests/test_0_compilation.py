import unittest
import subprocess
import os
import glob
from gradescope_utils.autograder_utils.decorators import weight, number, hide_errors

failed = False
dir = ""

class TestCompilation(unittest.TestCase):
    @weight(0)
    @number(0)
    @hide_errors()
    def test_submitted_files(self):
        """Compilation"""

        global failed

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
            failed = True
            self.fail()

        os.chdir(makefile_dir)
        os.system("runuser -u student -- make clean")

        for file in glob.iglob('./**', recursive=True):
            try:
                with open(file, 'r', encoding="utf-8") as f:
                    f.read()
            except UnicodeDecodeError:
                print(f"{file[2:]} is not allowed in your submission (is an executable). Please resubmit without it.")
                failed = True
                self.fail()
            except IsADirectoryError:
                pass

        try:
            subprocess.run("runuser -u student -- make".split(), check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError:
            print("We could not compile your executables. Verify that your Makefile is valid.")
            failed = True
            self.fail()

        if not os.path.isfile(os.path.join(makefile_dir, 'server')):
            print("We could not find your server executable. Make sure it's named `server`.")
            failed = True
            self.fail()

        if not os.path.isfile(os.path.join(makefile_dir, 'client')):
            print("We could not find your client executable. Make sure it's named `client`.")
            failed = True
            self.fail()

        global dir
        dir = makefile_dir

        