from .projectparser import ProjectParser
from .coqapi import API, Ok, Err
from .xmltype import *
import time
import signal
import os
import subprocess
import xml.etree.ElementTree as ET

class CoqTop:
    def __init__(self):
        self.api = API()
        pp = ProjectParser("test_data/emptyCoqProject")
        version = pp.version()
        args = [pp.getCoqtop()]
        if not version.isatleast89():
            args.append("-ideslave")
        args.append('-main-channel')
        args.append('stdfds')
        args.append('-async-proofs')
        args.append('on')
        for r in pp.getI():
            args.append('-I')
            args.append(r)
        for r in pp.getQ():
            args.append('-Q')
            args.append(r[0])
            args.append(r[1])
        for r in pp.getR():
            args.append('-R')
            args.append(r[0])
            args.append(r[1])
        if os.name == 'nt':
            self.coqtop = subprocess.Popen(args,
                stdin = subprocess.PIPE, stdout = subprocess.PIPE,
                stderr = subprocess.STDOUT)
        else:
            self.coqtop = subprocess.Popen(args,
                stdin = subprocess.PIPE, stdout = subprocess.PIPE,
                bufsize = 0)

    def interrupt(self):
        self.coqtop.send_signal(signal.SIGINT)

    def send(self, msg):
        self.coqtop.stdin.write(msg)
        self.coqtop.stdin.flush()

    def wait_result(self):
        time.sleep(0.01)
        assert(self.coqtop.poll() != 1)
        time.sleep(0.1)
        result = os.read(self.coqtop.stdout.fileno(), 0x4000)
        print(result)
        return result

    def wait_and_parse(self):
        r = self.wait_result().replace(b'&nbsp;', b' ')
        r = self.api.parse_response(ET.fromstring(b'<coq>' + r + b'</coq>'))
        return r

    def stop(self):
        time.sleep(0.1)
        self.coqtop.kill()

    def send_script(self, script, myid):
        for cmd in script:
            self.send(self.api.get_call_msg('Add', ((cmd, -1), (StateId(myid), True))))
            r = self.wait_and_parse()
            assert(isinstance(r, Ok))

            self.send(self.api.get_call_msg('Goal', ()))
            r = self.wait_and_parse()
            assert(isinstance(r, Ok))

            myid = myid + 1

def test_add_and_goal():
    ct = CoqTop()
    a = ct.api
    ct.send(a.get_init_msg())
    r = ct.wait_and_parse()
    assert(isinstance(r, Ok))
    ct.send(a.get_call_msg('Add', (("Lemma a: True.", -1), (StateId(1), True))))
    r = ct.wait_and_parse()
    assert(isinstance(r, Ok))
    ct.send(a.get_call_msg('Goal', ()))
    r = ct.wait_and_parse()
    assert(isinstance(r, Ok))
    ct.stop()

def test_add_and_fail_then_ok():
    ct = CoqTop()
    a = API()
    ct.send(a.get_init_msg())
    r = ct.wait_and_parse()
    assert(isinstance(r, Ok))
    ct.send(a.get_call_msg('Add', (("Lemma a.", -1), (StateId(1), True))))
    r = ct.wait_and_parse()
    assert(isinstance(r, Err))
    ct.send(a.get_call_msg('Add', (("Lemma a: True.", -1), (StateId(1), True))))
    r = ct.wait_and_parse()
    assert(isinstance(r, Ok))
    ct.send(a.get_call_msg('Goal', ()))
    r = ct.wait_and_parse()
    assert(isinstance(r, Ok))
    ct.stop()

def test_add_and_fail_then_bad_id():
    ct = CoqTop()
    a = API()
    ct.send(a.get_init_msg())
    r = ct.wait_and_parse()
    assert(isinstance(r, Ok))
    ct.send(a.get_call_msg('Add', (("Lemma a.", -1), (StateId(1), True))))
    r = ct.wait_and_parse()
    assert(isinstance(r, Err))
    ct.send(a.get_call_msg('Add', (("Lemma a: True.", -1), (StateId(2), True))))
    r = ct.wait_and_parse()
    assert(isinstance(r, Err))
    ct.stop()

def test_add_and_fail_then_goal():
    ct = CoqTop()
    a = API()
    ct.send(a.get_init_msg())
    r = ct.wait_and_parse()
    assert(isinstance(r, Ok))
    ct.send(a.get_call_msg('Add', (("Lemma a.", -1), (StateId(1), True))))
    r = ct.wait_and_parse()
    assert(isinstance(r, Err))
    ct.send(a.get_call_msg('Goal', ()))
    r = ct.wait_and_parse()
    assert(isinstance(r, Ok))
    ct.stop()

def test_interrupt_after_answer():
    ct = CoqTop()
    a = API()
    ct.send(a.get_init_msg())
    r = ct.wait_and_parse()
    assert(isinstance(r, Ok))
    ct.send(a.get_call_msg('Add', (("Ltac l := l.", -1), (StateId(1), True))))
    r = ct.wait_and_parse()
    assert(isinstance(r, Ok))
    ct.interrupt()
    # Never wait after interrupt!
    ct.send(a.get_call_msg('Goal', ()))
    r = ct.wait_and_parse()
    assert(isinstance(r, Err))

def test_interrupt_before_answer():
    ct = CoqTop()
    a = API()
    ct.send(a.get_init_msg())
    r = ct.wait_and_parse()
    assert(isinstance(r, Ok))
    ct.send_script(['Ltac l := l.', 'Lemma a: True.'], 1)
    ct.send(a.get_call_msg('Add', (("l.", -1), (StateId(3), True))))
    ct.interrupt()
    r = ct.wait_and_parse()
    assert(isinstance(r, Err))
    ct.send(a.get_call_msg('Goal', ()))
    r = ct.wait_and_parse()
    assert(isinstance(r, Ok))
