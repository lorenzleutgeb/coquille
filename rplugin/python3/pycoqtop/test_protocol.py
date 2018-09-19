from . import Actionner
from .coqtop import CoqTop, Version
from .projectparser import ProjectParser

class FakeCurrent:
    def __init__(self):
        self.buffer = None

class FakePrinter:
    def __init__(self):
        pass

    def debug(self, msg):
        pass

    def parseMessage(self, msg):
        pass

class FakeVim:
    def __init__(self):
        self.current = FakeCurrent()

    def command(self, cmd):
        pass

def test_version():
    actionner = Actionner(FakeVim())
    assert actionner.version().is_allowed()

def test_init():
    printer = FakePrinter()
    CoqTop(printer, ProjectParser("test_data/emptyCoqProject"))
