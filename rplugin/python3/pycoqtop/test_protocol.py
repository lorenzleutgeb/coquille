from . import Actionner
from .coqtop import CoqTop
from .projectparser import ProjectParser

class FakeCurrent:
    def __init__(self):
        self.buffer = None

class FakeVim:
    def __init__(self):
        self.current = FakeCurrent()

    def command(self, cmd):
        pass

class FakePrinter:
    def __init__(self):
        self.vim = FakeVim()
        pass

    def debug(self, msg):
        pass

    def parseMessage(self, msg):
        pass

def test_version():
    actionner = Actionner(FakeVim())
    assert actionner.version().is_allowed()

def test_init():
    printer = FakePrinter()
    ct = CoqTop(printer, ProjectParser("test_data/emptyCoqProject"))
    assert ct.restart()
    ct.kill()
