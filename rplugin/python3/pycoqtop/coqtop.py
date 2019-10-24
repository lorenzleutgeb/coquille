import os
import subprocess
import xml.etree.ElementTree as ET
import signal
import time
from threading import Thread, Lock, Event

from .coqapi import API, Ok, Err
from .coqxml import CoqParser
from .xmltype import *


class Messenger(Thread):
    def __init__(self, coqtop):
        Thread.__init__(self)
        self.coqtop = coqtop
        self.printer = self.coqtop.printer
        self.messages = []
        self.lock = Lock()
        self.cont = True
        self.waiting = False
        self.interupted = False
        self.silent_interupted = False
        self.canInteruptHere = True
        self.exception = Exception('No information')

    def stop(self):
        self.cont = False

    def add_message(self, msg):
        if not (self.isAlive()):
            raise self.exception
        self.printer.debug(">< ADDING MESSAGE " +str(msg)+ " ><\n")
        with self.lock:
            self.messages.insert(0, msg)

    def silent_interupt(self):
        with self.lock:
            self.silent_interupted = True

    def interupt(self):
        with self.lock:
            self.interupted = True
    
    def is_empty(self):
        with self.lock:
            return self.messages == []

    def guarded_interupt(self, mtype):
        with self.lock:
            if self.canInteruptHere and self.interupted and self.waiting:
                self.coqtop.printer.debug("\nINTERRUPTED!!\n")
                self.coqtop.coqtop.send_signal(signal.SIGINT)
                self.messages = []
                self.messages.insert(0, CoqGoal(self.coqtop))
                self.interupted = False
            elif self.canInteruptHere and self.interupted:
                self.coqtop.printer.debug("\nINTERRUPTED 2!!\n")
                self.messages = []
                self.interupted = False
            elif self.canInteruptHere and self.silent_interupted:
                self.coqtop.printer.debug("\nINTERRUPTED 3!!\n")
                self.messages = []
                self.silent_interupted = False

    def run(self):
        try:
            i = 0
            while self.cont:
                mtype = None
                sleep = True

                with self.lock:
                    sleep = self.messages == []
                    if not sleep:
                        self.printer.debug(">< SENDING NEXT MESSAGE ><\n")
                        message = self.messages.pop()
                        mtype = message.type
                        addtype = None
                        if mtype == 'add':
                            addtype = message.addtype

                        with self.coqtop.waiting_lock:
                            if mtype == 'goal' or mtype == 'addgoal':
                                self.canInteruptHere = True
                                self.coqtop.parser.nextFlush = False
                            else:
                                self.canInteruptHere = False
                            if addtype is None or addtype is not 'comment':
                                self.coqtop.set_next_answer_type(mtype)
                                self.coqtop.send_cmd(message.get_string())
                                self.coqtop.answer_event.clear()
                            else:
                                # Fake answer from coqtop when we parse a comment
                                self.coqtop.remove_answer(Ok(self.coqtop.state_id), mtype)
                                continue
                        self.printer.debug(">< NEXT MESSAGE SENT ><\n")

                if sleep:
                    time.sleep(0.2)
                    continue

                if self.cont:
                    self.waiting = True
                    self.coqtop.wait_answer()
                    self.waiting = False
                    self.guarded_interupt(mtype)

            with self.lock:
                self.messages = []
        except BaseException as e:
            self.exception = e

class Add:
    def __init__(self, coqtop, instr, typ):
        self.coqtop = coqtop
        self.instr = instr
        self.type = "add"
        self.addtype = typ

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

class CoqQuery86(CoqQuery):
    def __init__(self, coqtop, instr):
        CoqQuery.__init__(self, coqtop, instr)

    def get_string(self):
        a = API()
        return a.get_call_msg('Query', (self.instr, self.coqtop.state_id))

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

def new_coqtop(printer, parser):
    if parser.version().is86():
        return CoqTop86(printer, parser)
    if parser.version().isatleast89():
        return CoqTop89(printer, parser)
    return CoqTop(printer, parser)

class CoqTop:
    def __init__(self, printer, parser):
        self.write_lock = Lock()
        self.waiting_lock = Lock()
        self.answer_event = Event()
        self.answer_event.clear()
        self.printer = printer
        self.coqtop = None
        self.states = []
        self.state_id = None
        self.root_state = None
        self.messenger = None
        self.calltype = "init"
        self.shouldRewind = False
        self.coqtopbin = parser.getCoqtop()
        self.args = parser.getArgs()
        self.worker = 'master'

    def setWorker(self, worker):
        self.worker = worker

    def setPrinter(self, printer):
        self.printer = printer

    def running(self):
        return self.coqtop is None

    def start(self):
        self.restart()

    def getDefaultOptions(self):
        return [ self.coqtopbin, '-ideslave', '-main-channel', 'stdfds',
            '-async-proofs', 'on',
            # prevent stupid behavior where "admit"s are added when errors
            # should occur. This "error resilience" non sense make coqc and
            # coqtop act differently, and the user wouldn't expect that.
            '-async-proofs-tactic-error-resilience', 'off']

    def restart(self, *args):
        if self.coqtop:
            self.kill()
        self.messenger = Messenger(self)
        options = self.getDefaultOptions()
        options += self.args
        try:
            if os.name == 'nt':
                self.coqtop = subprocess.Popen(options + list(args),
                    stdin = subprocess.PIPE, stdout = subprocess.PIPE,
                    stderr = subprocess.STDOUT)
            else:
                self.coqtop = subprocess.Popen(options + list(args),
                    stdin = subprocess.PIPE, stdout = subprocess.PIPE)#,
                    #preexec_fn = ignore_sigint)
            r = self.init()
            self.printer.debug("\n>< INIT DONE ><\n")
            assert isinstance(r, Ok)
            self.messenger.start()
            self.root_state = r.state_id
            # Probably wrong:
            self.state_id = r.state_id
        except OSError:
            return False
        return True

    def kill(self):
        if self.coqtop:
            self.messenger.stop()
            self.parser.stop()
            self.parser.join()
            self.messenger.join()
            try:
                self.coqtop.terminate()
                self.coqtop.communicate()
            except OSError:
                pass
            self.coqtop = None

    def init(self):
        a = API()
        message = a.get_init_msg()
        self.send_cmd(message)
        self.parser = CoqParser(self.coqtop, self, self.printer)
        self.parser.start()
        return Ok(1)

    def set_next_answer_type(self, calltype):
        self.calltype = calltype

    def wait_answer(self):
        while not self.answer_event.isSet() and self.messenger.cont:
            self.answer_event.wait(0.1)
            self.messenger.guarded_interupt(self.calltype)
        if self.shouldRewind and self.messenger.cont:
            self.rewind()

    def wait_answer_uninterrupted(self):
        while not self.answer_event.isSet() and self.messenger.cont:
            self.answer_event.wait(0.1)
        if self.shouldRewind:
            self.rewind()

    def pull_event(self, event):
        self.shouldRewind = self.remove_answer(event, self.calltype)
        self.printer.debug("\nEnd of remove_answer\n")
        self.calltype = None
        with self.waiting_lock:
            self.answer_event.set()

    def goals(self, advance = False):
        self.messenger.add_message(CoqGoal(self, advance))

    def advance(self, instr, typ, encoding = 'utf8'):
        self.messenger.add_message(Add(self, instr, typ))

    def check(self, terms):
        self.query("Check ({}).".format(terms))

    def dolocate(self, terms):
        if " " in terms:
            self.query("Locate ({}).".format(terms))
        else:
            self.query("Locate {}.".format(terms))

    def doprint(self, terms):
        if " " in terms:
            self.query("Print ({}).".format(terms))
        else:
            self.query("Print {}.".format(terms))

    def search(self, terms):
        self.query("Search ({}).".format(terms))

    def searchabout(self, terms):
        self.query("SearchAbout {}.".format(terms))

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
            with self.waiting_lock:
                self.set_next_answer_type("undo")
                self.send_cmd(message)
                self.answer_event.clear()
            self.wait_answer_uninterrupted()

    def interupt(self):
        self.messenger.interupt()
        a = API()

    def silent_interupt(self):
        self.messenger.silent_interupt()

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

    def remove_answer(self, r, msgtype):
        self.printer.parseMessage(r, msgtype)
        if isinstance(r, Err) and msgtype == 'addgoal':
            return True
        if isinstance(r, Ok) and not r.state_id is None:
            self.states.append(self.state_id)
            self.state_id = r.state_id
        return False

class CoqTop86(CoqTop):
    def __init__(self, printer, parser):
        CoqTop.__init__(self, printer, parser)

    def query(self, terms):
        self.messenger.add_message(CoqQuery86(self, terms))

class CoqTop89(CoqTop):
    def __init__(self, printer, parser):
        CoqTop.__init__(self, printer, parser)

    def getDefaultOptions(self):
        return [ self.coqtopbin, '-main-channel', 'stdfds',
            '-async-proofs', 'on',
            '-async-proofs-tactic-error-resilience', 'off']
