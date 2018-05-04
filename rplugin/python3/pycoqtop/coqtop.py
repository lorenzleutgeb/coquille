import os
import subprocess
import xml.etree.ElementTree as ET
import signal
import time
from threading import Thread, Lock

from pycoqtop.coqapi import API, Ok, Err
from pycoqtop.xmltype import *

class Messenger(Thread):
    def __init__(self, coqtop):
        Thread.__init__(self)
        self.coqtop = coqtop
        self.messages = []
        self.lock = Lock()
        self.cont = True
        self.exception = Exception('No information')

    def stop(self):
        self.cont = False
        self.join()

    def add_message(self, msg):
        if not (self.isAlive()):
            raise self.exception
        with self.lock:
            self.messages.insert(0, msg)

    def interupt(self):
        with self.lock:
            self.messages = []
    
    def is_empty(self):
        with self.lock:
            return self.messages == []

    def run(self):
        try:
            i = 0
            while self.cont:
                with self.lock:
                    sleep = self.messages == []
                    if not sleep:
                        message = self.messages.pop()
                        self.coqtop.send_cmd(message.get_string())

                if sleep:
                    time.sleep(0.2)
                    continue

                ans = self.coqtop.get_answer()
                self.coqtop.remove_answer(ans, message.type)
            with self.lock:
                self.messages = []
        except BaseException as e:
            self.exception = e

class Add:
    def __init__(self, coqtop, instr):
        self.coqtop = coqtop
        self.instr = instr
        self.type = "add"

    def get_string(self):
        a = API()
        return a.get_call_msg('Add', ((self.instr, -1), (self.coqtop.state_id, True)))

class CoqQuery:
    def __init__(self, coqtop, instr):
        self.coqtop = coqtop
        self.instr = instr
        self.type = "query"

    def get_string(self):
        a = API()
        return a.get_call_msg('Query', (RouteId(0), (self.instr, self.coqtop.state_id)))

class CoqGoal:
    def __init__(self, coqtop, advance = False):
        self.coqtop = coqtop
        if advance:
            self.type = "addgoal"
        else:
            self.type = "goal"

    def get_string(self):
        a = API()
        return a.get_call_msg('Goal', ())

def ignore_sigint():
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def escape(data):
    return data.decode('utf-8') \
               .replace("&nbsp;", ' ') \
               .replace("&apos;", '\'') \
               .replace("&#40;", '(') \
               .replace("&#41;", ')')

class CoqTop:
    def __init__(self, printer, binary, R):
        self.write_lock = Lock()
        self.interupted = False
        self.printer = printer
        self.coqtop = None
        self.states = []
        self.state_id = None
        self.root_state = None
        self.messenger = None
        self.coqtopbin = binary
        self.R = R

    def running(self):
        return self.coqtop is None

    def start(self):
        self.restart()

    def restart(self, *args):
        if self.coqtop:
            self.kill()
        self.messenger = Messenger(self)
        options = [ self.coqtopbin, '-ideslave', '-main-channel', 'stdfds',
            '-async-proofs', 'on',
            # prevent stupid behavior where "admit"s are added when errors
            # should occur. This "error resilience" non sense make coqc and
            # coqtop act differently, and the user wouldn't expect that.
            '-async-proofs-tactic-error-resilience', 'off']
        for r in self.R:
            options.append('-R')
            options.append(r[0])
            options.append(r[1])
        try:
            if os.name == 'nt':
                self.coqtop = subprocess.Popen(options + list(args),
                    stdin = subprocess.PIPE, stdout = subprocess.PIPE,
                    stderr = subprocess.STDOUT)
            else:
                self.coqtop = subprocess.Popen(options + list(args),
                    stdin = subprocess.PIPE, stdout = subprocess.PIPE,
                    preexec_fn = ignore_sigint)
            self.messenger.start()
            r = self.init()
            assert isinstance(r, Ok)
            self.root_state = r.val
            self.state_id = r.val
        except OSError:
            return False
        return True

    def kill(self):
        if self.coqtop:
            try:
                self.coqtop.terminate()
                self.coqtop.communicate()
            except OSError:
                pass
            self.coqtop = None
            self.messenger.stop()

    def init(self):
        a = API()
        message = a.get_init_msg()
        self.send_cmd(message)
        return self.get_answer()

    def goals(self, advance = False):
        self.messenger.add_message(CoqGoal(self, advance))

    def advance(self, instr, encoding = 'utf8'):
        self.messenger.add_message(Add(self, instr))

    def check(self, terms):
        self.messenger.add_message(CoqQuery(self, "Check ({}).".format(terms)))

    def dolocate(self, terms):
        if " " in terms:
            self.messenger.add_message(CoqQuery(self, "Locate ({}).".format(terms)))
        else:
            self.messenger.add_message(CoqQuery(self, "Locate {}.".format(terms)))

    def doprint(self, terms):
        if " " in terms:
            self.messenger.add_message(CoqQuery(self, "Print ({}).".format(terms)))
        else:
            self.messenger.add_message(CoqQuery(self, "Print {}.".format(terms)))

    def search(self, terms):
        self.messenger.add_message(CoqQuery(self, "Search ({}).".format(terms)))

    def searchabout(self, terms):
        self.messenger.add_message(CoqQuery(self, "SearchAbout {}.".format(terms)))

    def query(self, terms):
        self.messenger.add_message(CoqQuery(self, terms))

    def rewind(self, step = 1):
        assert self.messenger.is_empty()
        assert step <= len(self.states)
        with self.messenger.lock:
            idx = len(self.states) - step
            self.state_id = self.states[idx]
            self.states = self.states[0:idx]
            a = API()
            message = a.get_call_msg('Edit_at', self.state_id)
            self.send_cmd(message)
            ans = self.get_answer()
            self.remove_answer(ans, "undo")

    def interupt(self):
        self.messenger.interupt()
        self.interupted = True
        a = API()
        message = a.get_call_msg('StopWorker', "0")
        self.send_cmd(message)
        self.get_answer()

    def silent_interupt(self):
        self.messenger.interupt()

    def send_async_cmd(self, msg):
        if self.coqtop is None:
            return
        self.message.append(Message (msg=msg) (getter=getter(self)))

    def send_cmd(self, msg):
        if self.coqtop is None:
            return
        with self.write_lock:
            self.printer.debug(">>>" + str(msg) + "\n")
            self.coqtop.stdin.write(msg)
            self.coqtop.stdin.flush()

    def get_answer(self):
        if self.coqtop is None:
            return
        fd = self.coqtop.stdout.fileno()
        data = b''
        a = API()
        shouldWait = True
        elt = None
        while shouldWait:
            try:
                time.sleep(0.01)
                if self.interupted:
                    self.interupted = False
                    return None
                data += os.read(fd, 0x4000)
                try:
                    elt = ET.fromstring('<coqtoproot>' + escape(data) + '</coqtoproot>')
                    shouldWait = a.response_end(elt)
                except ET.ParseError:
                    continue
            except OSError:
                return None
        self.printer.debug("<<<" + str(data) + "\n")
        return a.parse_response(elt)

    def remove_answer(self, r, msgtype):
        self.printer.parseMessage(r, msgtype)
        if isinstance(r, Err) and msgtype == 'addgoal':
            self.rewind()
            return
        if not hasattr(r, 'val'):
            return
        for c in list(r.val):
            if isinstance(c, StateId):
                self.states.append(self.state_id)
                self.state_id = c
                break
