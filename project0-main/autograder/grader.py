import os
import unittest

from gradescope_utils.autograder_utils.json_test_runner import JSONTestRunner

if __name__ == '__main__':
    os.system("chmod -R o+rwx /autograder/submission")
    suite = unittest.defaultTestLoader.discover('tests')
    with open('/autograder/results/results.json', 'w') as f:
        def post_process(json):
            json['test_output_format'] = 'md'
            for test in json['tests']:
                if 'output' in test:
                    test['output'] = test['output'].replace('Test failed', '')
            json['tests'] = sorted(json['tests'], key=lambda x: x['number'])
        runner = JSONTestRunner(
            visibility='visible', stream=f, failure_prefix="", post_processor=post_process)
        runner.run(suite)
