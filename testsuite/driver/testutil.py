import errno
import os
import platform
import subprocess
import shutil
import threading

def strip_quotes(s):
    # Don't wrap commands to subprocess.call/Popen in quotes.
    return s.strip('\'"')

def getStdout(cmd_and_args):
    # Can't use subprocess.check_output as it's not available in Python 2.6;
    # It's also not quite the same as check_output, since we also verify that
    # no stderr was produced
    p = subprocess.Popen([strip_quotes(cmd_and_args[0])] + cmd_and_args[1:],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    (stdout, stderr) = p.communicate()
    r = p.wait()
    if r != 0:
        raise Exception("Command failed: " + str(cmd_and_args))
    if stderr:
        raise Exception("stderr from command: %s\nOutput:\n%s\n" % (cmd_and_args, stderr))
    return stdout

def mkdirp(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def lndir(srcdir, dstdir):
    # Create symlinks for all files in src directory.
    # Not all developers might have lndir installed.
    # os.system('lndir -silent {0} {1}'.format(srcdir, dstdir))
    for filename in os.listdir(srcdir):
        src = os.path.join(srcdir, filename)
        dst = os.path.join(dstdir, filename)
        if os.path.isfile(src):
            link_or_copy_file(src, dst)
        else:
            os.mkdir(dst)
            lndir(src, dst)


# This function exists here for legacy reasons but spiritually belongs in perf_notes.py
#
# Returns a list of tests; each test is a dict of the form
#
# { 'test_env' : 'val',   'test'    : 'val',   'way'     : 'val',
#   'metric'   : 'val',   'value'   : 'val',   'commit'  : 'val', }
#
# It allows one to read in git notes from the commandline
# and then breaks it into a list of dictionaries that can be parsed
# later on in the testing functions.
# Returns an empty string if the note is not found.
def parse_git_notes(namespace, commit='HEAD'):
    logFields = ['test_env','test','way','metric','value','commit']

    try:
        log = subprocess.check_output(['git', 'notes', '--ref=' + namespace, 'show', commit], stderr=subprocess.STDOUT).decode('utf-8')
    except subprocess.CalledProcessError:
        return []

    log = log.strip('\n').split('\n')
    log = list(filter(None, log))
    log = [line.strip('\t').split('\t') for line in log]
    [x.append(commit) for x in log]
    log = [dict(zip(logFields, field)) for field in log]
    return log


# On Windows, os.symlink is not defined with Python 2.7, but is in Python 3
# when using msys2, as GHC does. Unfortunately, only Administrative users have
# the privileges necessary to create symbolic links by default. Consequently we
# are forced to just copy instead.
#
# We define the following function to make this magic more
# explicit/discoverable. You are enouraged to use it instead of os.symlink.
if platform.system() == 'Windows':
    link_or_copy_file = shutil.copyfile
else:
    link_or_copy_file = os.symlink

class Watcher(object):
    global pool
    global evt
    global sync_lock

    def __init__(self, count):
        self.pool = count
        self.evt = threading.Event()
        self.sync_lock = threading.Lock()
        if count <= 0:
            self.evt.set()

    def wait(self):
        self.evt.wait()

    def notify(self):
        self.sync_lock.acquire()
        self.pool -= 1
        if self.pool <= 0:
            self.evt.set()
        self.sync_lock.release()
