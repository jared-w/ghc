GHC Driver Readme
=================

Greetings and well met.
If you are reading this, I can only assume that you are likely interested in working on the testsuite in some capacity.
For more detailed documentation, please see [here][1].

## ToC

1. Entry points of the testsuite
2. Quick overview of program parts
3. How to use the comparison tool
4. Important Types
5. Quick answers for "how do I do X"?


## Entry Points of the Testsuite

The testsuite has two main entry points depending on which perspective you approach it.
From the perspective of the /user/, the entry point is the collect_stats function.
This function is declared in perf_notes.py along with its associated infrastructure.
The purpose of the function is to tell the test driver what metrics to compare when processing the test.
From the perspective of the test-suite, its entry point is the runtests.py file.
In that file contains the main logic for running the individual tests, collecting information, handling failure, and outputting the final results.

## Overview of how the performance test bits work.
During a Haskell Summer of Code project, an intern went through and revamped most of the performance test code, as such there have been a few changes to it that might be unusual to anyone previously familiar with the testsuite.
One of the biggest immediate benefits is that all platform differences, compiler differences, and things such as that are not necessary to be considered by the test writer anymore.
This is due to the fact that the test comparison relies entirely on locally collected metrics on the testing machine.

As such, it is perfectly sufficient to write `collect_stats('all',5)` to measure the 3 potential stats that can be collected for that test and automatically test them for regressions, failing if there is more than a 5% change in any direction.
In fact, even that is not necessary as `collect_stats()` defaults to 'all', and 20% deviation allowed.
See the implementation of collect_stats in /driver/perf_notes.py for more information.

If the performance of a test is improved so much that the test fails, the value will still be recorded and treated as the new best value in subsequent commits.
The warning that will be emitted is merely a precaution so that the programmer can double-check that they didn't introduce a bug;
something that might be suspicious if the test suddenly improves by 70%, for example.

Performance metrics for performance tests are now stored in git notes under the namespace 'perf'.
The format of the git note file is that each line represents a single metric for a particular test:
`$test_env $test_name $test_way $metric_measured $value_collected` (delimited by tabs).

One can view the maximum deviation a test allows by looking inside its respective all.T file;
additionally, if one sets the verbosity level of the test-suite to a value >= 4, they will see a good amount of output per test detailing all the information about values.
This information will also print if the test falls outside of the allowed bounds.
(see the test_cmp function in /driver/perf_notes.py for exact formatting of the message)

The git notes are only appended to by the testsuite in a single atomic python subprocess at the end of the test run;
if the run is canceled at any time, the notes will not be written.
The note appending command will be retried up to 4 times in the event of a failure (such as one happening due to a lock on the repo) although this is never anticipated to happen.
If, for some reason, the 5 attempts were not enough, an error message will be printed out.
Further, there is no current process or method for stripping duplicates, updating values, etc, so if the testsuite is ran multiple times per commit there will be multiple values in the git notes corresponding to the tests ran.
This does seem to be the most sane behavior; as such, only the latest appearing "version" of a test is considered per commit.

## Quick overview of program parts

The relevant bits of the directory tree are as such:

```
├── driver                   -- Testsuite driver directory
    ├── junit.py             -- Contains code implementing JUnit features.
    ├── kill_extra_files.py  -- Some of the uglier implementation details.
    ├── perf_notes.py        -- Code for a comparison tool and performance tests.
    ├── runtests.py          -- Main entrypoint for program; runs tests.
    ├── testglobals.py       -- Declares global data structures and objects.
    ├── testlib.py           -- Bulk of implementation is in here.
    └── testutil.py          -- Misc helper functions.
├── mk
    └── test.mk              -- Master makefile for running tests.
├── tests                    -- Main tests directory.
```

## How to Use the Comparison Tool

The comparison tool exists in `/driver/perf_notes.py`.

When the testsuite is ran, the performance metrics of the performance tests are saved automatically in a local git note that will be attached to the commit.
The comparison tool is designed to help analyze the performance of the compiler across commits using this performance information.

Currently, it can only be ran by executing the file directly, like so:
```
$ python3 perf_notes.py (arguments go here)
```

If you run `perf_notes.py -h` you will see a description of all of the arguments and how to use them.
The optional arguments exist to filter the output to include only commits that you're interested in.
The most typical usage of this tool will likely be running `perf_notes.py HEAD 'HEAD~1' '(commit hash)' ...`

The way the performance metrics are stored in git notes remains strictly local to the machine;
as such, performance metrics will not exist for a commit until you checkout that commit and run the testsuite (or test).

## Important Types

* metric
    - Internal to perf_notes.py, this has the same type as parse_git_notes
* parse_git_notes
    - Exists in testutil.py for legacy reasons but spiritually belongs in perf_notes.py
    - Returns a list of tests; each test is a dict of the form
      ```
      { 'test_env' : 'val',
        'test'    : 'val',
        'way'     : 'val',
        'metric'  : 'val',
        'value'   : 'val',
        'commit'  : 'val', }
        ```
        (Occasionally slightly different names are used in the source code; 'test' is usually called 'name' in testutil.py, for example)
* stats_range_fields
    - Exists in testglobals.py.
    - Is a list of tuples of the form `('metric', value, allowed deviation)`
        Note that this value is one that we collect from git notes and does not
        represent the value outputted from running the test.
* accumulate_metrics
    - Exists in testglobals.py
    - Is a list of strings in the form `'\t'.join('test_env','test','way','metric','value')`
        This is what is written to the git notes for the HEAD commit.
        As such, this 'value' /does/ represent the actual performance measured during the test-suite's run.

## Quick Answers for "How do I do X?"

* Q: How do I add a flag to the make test to extend the functionality of the testsuite?
    1. Add the flag in the appropriate global object in testglobals.py
    2. Add an argument to the parser in runtests.py that sets the flag
    3. Go to the `testsuite/mk/test.mk` file and add a new ifeq (or ifneq) block.
        I suggest adding the block around line 200.
* Q: How do I modify how performance tests work?
    * That functionality resides in perf_notes.py which has pretty good in-comment documentation.
    * Additionally, one will want to look at `compile_and_run`, `simple_run`, and `simple_build` in testutil.py

  [1]: http://ghc.haskell.org/trac/ghc/wiki/Building/RunningTests
