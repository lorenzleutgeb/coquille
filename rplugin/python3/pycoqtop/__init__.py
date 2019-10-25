import neovim

from .coqtop import new_coqtop
from .coqapi import Ok, Err
from .xmltype import *
from .projectparser import ProjectParser
from .coqc import coqbuild
from threading import Event, Lock, Thread
from .parser import Parser

import os
import re
import subprocess
import time
import uuid

def recolor(obj):
    obj.redraw()
def regoal(obj, msg):
    obj.showGoal(msg)
def reerror(obj, pos, start, end):
    obj.showError(pos, start, end)
def step(obj):
    obj.next()
def cursor(obj):
    obj.cursor()
def undo(obj):
    obj.undo()
def goto_last_dot(obj):
    obj.goto_last_dot()

@neovim.plugin
class Main(object):
    def __init__(self, vim):
        self.actionners = {}
        self.info_wins = {}
        self.goal_wins = {}
        self.vim = vim
        self.vim.command("let w:coquille_running='false'")

    def diditdieyet(self):
        "Checks whether the actionner thread died and re-raise its exception."
        for name in self.actionners:
            actionner = self.actionners[name]
            if not actionner.isAlive():
                raise actionner.exception

    @neovim.function('CoqLaunch', sync=True)
    def launch(self, args=[]):
        self.vim.call("coquille#define_running")
        if self.vim.eval("w:coquille_running") != 'false':
            self.vim.command('echo "Coquille is already running in this window!"')
            return
        random_name = str(uuid.uuid4())
        try:
            self.actionners[random_name] = Actionner(self.vim)
            self.currentVersion = self.actionners[random_name].version(args)
        except:
            self.vim.command('echo "Coq could not be found!"')
            return

        if not self.currentVersion.is_allowed():
            self.actionners[random_name].stop()
            self.actionners[random_name].join()
            self.vim.command('echo "Unsupported version {} (currently supported: >=8.6, <9)"'\
                .format(self.currentVersion))
            return
        self.vim.command("let w:coquille_running='"+random_name+"'")
        if self.actionners[random_name].restart():
            self.vim.call('coquille#Register')
            self.vim.call('coquille#ShowPanels')
            self.info_wins[random_name] = self.vim.eval("g:new_info_buf")
            self.goal_wins[random_name] = self.vim.eval("g:new_goal_buf")
            self.actionners[random_name].goal_buf = self.vim.eval("g:new_goal_buf")
            self.actionners[random_name].info_buf = self.vim.eval("g:new_info_buf")
            self.actionners[random_name].start()
        else:
            self.vim.command('echo "Coq could not be launched!"')
            self.vim.command("let w:coquille_running='false'")

    @neovim.function('CoqVersion', sync=True)
    def version(self, args=[]):
        if self.vim.eval("w:coquille_running") != 'false':
            self.vim.command('echo "Coq {}"'.format(self.currentVersion))
        else:
            try:
                a = Actionner(self.vim)
                version = a.version(args)
                self.vim.command('echo "Coq {}"'.format(version))
            except:
                self.vim.command('echo "Coq could not be found!"')

    @neovim.function('CoqStop', sync=True)
    def stop(self, args=[]):
        name = self.vim.eval("w:coquille_running")
        if name == 'false':
            return
        actionner = self.actionners[name]
        self.vim.command("let w:coquille_running='false'")
        actionner.stop()
        self.vim.call('coquille#KillSession')
        self.vim.command('bdelete '+str(self.info_wins[name]))
        self.vim.command('bdelete '+str(self.goal_wins[name]))
        self.vim.command("let w:coquille_running='false'")
        self.vim.command("au! * <buffer>")
        actionner.join()
        del self.actionners[name]
        del self.goal_wins[name]
        del self.info_wins[name]

    @neovim.function('CoqModify', sync=True)
    def modify(self, args=[]):
        name = self.vim.eval("w:coquille_running")
        if name == 'false':
            return
        actionner = self.actionners[name]
        self.diditdieyet()
        actionner.add_action('modified')

    @neovim.function('CoqNext', sync=True)
    def next(self, args=[]):
        name = self.vim.eval("w:coquille_running")
        if name == 'false':
            return
        actionner = self.actionners[name]
        self.diditdieyet()
        actionner.add_action('next')

    @neovim.function('CoqUndo', sync=False)
    def undo(self, args = []):
        name = self.vim.eval("w:coquille_running")
        if name == 'false':
            return
        actionner = self.actionners[name]
        self.diditdieyet()
        actionner.add_action('undo')

    @neovim.function('CoqToCursor', sync=False)
    def stepToCursor(self, args=[]):
        name = self.vim.eval("w:coquille_running")
        if name == 'false':
            return
        actionner = self.actionners[name]
        self.diditdieyet()
        actionner.add_action('cursor')

    @neovim.function('CoqCancel')
    def cancel(self, args=[]):
        name = self.vim.eval("w:coquille_running")
        if name == 'false':
            return
        actionner = self.actionners[name]
        self.diditdieyet()
        actionner.add_action('cancel')

    @neovim.function('CoqSearch', sync=True)
    def search(self, args=[]):
        name = self.vim.eval("w:coquille_running")
        if name == 'false':
            return
        actionner = self.actionners[name]
        self.diditdieyet()
        actionner.add_action('search', args)

    @neovim.function('CoqCheck', sync=True)
    def check(self, args=[]):
        name = self.vim.eval("w:coquille_running")
        if name == 'false':
            return
        actionner = self.actionners[name]
        self.diditdieyet()
        actionner.add_action('check', args)

    @neovim.function('CoqSearchAbout', sync=True)
    def searchabout(self, args=[]):
        name = self.vim.eval("w:coquille_running")
        if name == 'false':
            return
        actionner = self.actionners[name]
        self.diditdieyet()
        actionner.add_action('searchabout', args)

    @neovim.function('CoqLocate', sync=True)
    def locate(self, args=[]):
        name = self.vim.eval("w:coquille_running")
        if name == 'false':
            return
        actionner = self.actionners[name]
        self.diditdieyet()
        actionner.add_action('locate', args)

    @neovim.function('CoqPrint', sync=True)
    def doprint(self, args=[]):
        name = self.vim.eval("w:coquille_running")
        if name == 'false':
            return
        actionner = self.actionners[name]
        self.diditdieyet()
        actionner.add_action('print', args)

    @neovim.function('CoqQuery', sync=True)
    def query(self, args=[]):
        name = self.vim.eval("w:coquille_running")
        if name == 'false':
            return
        actionner = self.actionners[name]
        self.diditdieyet()
        actionner.add_action('query', args)

    @neovim.function('CoqRedraw', sync=True)
    def redraw(self, args=[]):
        name = self.vim.eval("w:coquille_running")
        if name == 'false':
            return
        actionner = self.actionners[name]
        self.diditdieyet()
        actionner.redraw(args)

    @neovim.function('CoqDebug', sync=True)
    def debug(self, args=[]):
        name = self.vim.eval("w:coquille_running")
        actionner = self.actionners[name]
        actionner.debug_wanted = True
        self.vim.command('echo "running: ' + str(actionner.running_dots) + '"')
        self.vim.command('echo "valid: ' + str(actionner.valid_dots) + '"')
        self.vim.command('echo "state: ' + str(actionner.ct.state_id) + '"')
        self.vim.command('echo "debug: '+str(actionner.flush_debug()).replace("\"", "\\\"")+'"')

    @neovim.function('CoqErrorAt', sync=True)
    def showError(self, pos, start, end):
        name = self.vim.eval("w:coquille_running")
        if name == 'false':
            return
        actionner = self.actionners[name]
        self.diditdieyet()
        actionner.showError(pos, start, end)

    @neovim.function('CoqRedrawInfo', sync=True)
    def showInfo(self, info):
        name = self.vim.eval("w:coquille_running")
        if name == 'false':
            return
        actionner = self.actionners[name]
        self.diditdieyet()
        actionner.showInfo(info)

    @neovim.function('CoqRedrawGoal', sync=True)
    def showGoal(self, goal):
        name = self.vim.eval("w:coquille_running")
        if name == 'false':
            return
        actionner = self.actionners[name]
        self.diditdieyet()
        actionner.showGoal(goal)

    @neovim.function('CoqBuild', sync=False)
    def build(self, args):
        name = self.vim.eval("w:coquille_running")
        if name != 'false':
            actionner = self.actionners[name]
            self.diditdieyet()
            actionner.build()
        else:
            try:
                a = Actionner(self.vim)
                a.build()
            except:
                self.vim.command('echo "Coq could not be found!"')


# Start a request from a thread
def request(vim, requester):
    vim.async_call(run_request, requester)
    return requester.waitResult()

# Execute the request from nvim thread
def run_request(requester):
    requester.request()

class Requester:
    def __init__(self):
        self.result = None
        self.waiter = Event()
        self.waiter.clear()

    def setResult(self, result):
        self.result = result
        self.waiter.set()

    def waitResult(self):
        self.waiter.wait()
        return self.result

class StepRequester(Requester):
    def __init__(self, obj):
        Requester.__init__(self)
        self.obj = obj

    def request(self):
        self.setResult(self.obj.findNextStep())

class FullstepRequester(Requester):
    def __init__(self, obj):
        Requester.__init__(self)
        self.obj = obj
    
    def request(self):
        encoding = 'utf-8'
        step = self.obj.findNextStep()
        res = {'step': step}
        if step is None:
            self.setResult(res)
            return
        (eline, ecol) = step['stop']
        line = (self.obj.buf[eline])[:ecol]
        ecol += len(bytes(line, encoding)) - len(line)
        res['running'] = (eline, ecol + 1, step['content'])
        res["message"] = step['content']
        res["type"] = step['type']
        self.setResult(res)

class FullstepsRequester(FullstepRequester):
    def __init__(self, obj, cline, ccol):
        FullstepRequester.__init__(self, obj)
        self.cline = cline
        self.ccol = ccol

    def request(self):
        steps = []
        with self.obj.running_lock:
            while True:
                encoding = 'utf-8'
                FullstepRequester.request(self)
                res = self.waitResult()
                if res['step'] == None:
                    break
                if res['step']['stop'] <= (self.cline, self.ccol):
                    self.obj.running_dots.insert(0, res['running'])
                    self.obj.ct.advance(res['message'], res['type'], encoding)
                    self.obj.ct.goals(True)
                else:
                    break
        self.setResult(steps)

class BetweenRequester(Requester):
    def __init__(self, obj, start, stop):
        Requester.__init__(self)
        self.obj = obj
        self.start = start
        self.stop = stop

    def request(self):
        self.setResult(self.obj._between(self.start, self.stop))

class CursorRequester(Requester):
    def __init__(self, vim, buf):
        Requester.__init__(self)
        self.vim = vim
        self.buf = buf

    def request(self):
        if self.buf.name != self.vim.current.buffer.name:
            self.setResult(None)
        else:
            self.setResult(self.vim.current.window.cursor)

class LineRequester(Requester):
    def __init__(self, buf, line):
        Requester.__init__(self)
        self.buf = buf
        self.line = line

    def request(self):
        self.setResult(self.buf[self.line] + '\n')

class GoalRequester(Requester):
    def __init__(self, printer, goals):
        Requester.__init__(self)
        self.printer = printer
        self.goals = goals

    def request(self):
        self.printer.showGoal(self.goals)
        self.setResult(0)

class InfoRequester(Requester):
    def __init__(self, printer, info):
        Requester.__init__(self)
        self.printer = printer
        self.info = info

    def request(self):
        self.printer.showInfo(self.info)
        self.setResult(0)

class RemoveInfoRequester(Requester):
    def __init__(self, printer):
        Requester.__init__(self)
        self.printer = printer

    def request(self):
        self.printer.removeInfo()
        self.setResult(0)

class Printer(Thread):
    def __init__(self, printer):
        Thread.__init__(self)

        self.printer = printer
        self.info = []
        self.goal = []
        self.event = Event()
        self.event.clear()
        self.cont = True
        self.lock = Lock()
        self.info_modified = False
        self.goal_modified = False
        self.flushing = False

    def addGoal(self, goal):
        with self.lock:
            self.goal.append(goal);
            self.goal_modified = True
            self.event.set()

    def addInfo(self, info):
        with self.lock:
            if self.flushing:
                request(self.printer.vim, RemoveInfoRequester(self.printer))
                self.flushing = False
                self.info = []
            self.info.append(info);
            self.info_modified = True
            self.event.set()

    def flushInfo(self):
        with self.lock:
            self.printer.debug("Flushing\n")
            self.flushing = True
            if not self.info_modified:
                self.info = []

    def stop(self):
        self.cont = False

    def run(self):
        try:
            while self.cont:
                self.event.wait(0.1)
                with self.lock:
                    self.event.clear()
                    canFlush = False
                    if self.info_modified and self.info != []:
                        request(self.printer.vim, InfoRequester(self.printer, self.info))
                        self.info = []
                        self.info_modified = False
                        if self.flushing:
                            canFlush = True
                    if self.goal_modified and self.goal != []:
                        request(self.printer.vim, GoalRequester(self.printer, self.goal.pop()))
                        self.goal_modified = False
        except e:
            self.printer.debug(str(e))

class Actionner(Thread):
    def __init__(self, vim):
        Thread.__init__(self)

        # Find current filename or use current working directory if there is
        # no open file.
        filename = vim.current.buffer.name
        if filename != "" and filename[0] == '/':
            filename = os.path.dirname(filename)
        else:
            filename = os.getcwd()

        # Then find a _CoqProject inside that directory or any parent directory.
        coqproject = self.findCoqProject(filename)
        self.parser = ProjectParser(coqproject)
        self.ct = new_coqtop(self, self.parser)
        self.coqtopbin = self.parser.getCoqtop()
        self.vim = vim
        self.buf = self.vim.current.buffer
        self.printer = Printer(self)
        self.printer.start()

        self.info = []
        self.must_stop = False
        self.running_lock = Lock()
        self.running_dots = []
        self.valid_dots = []
        self.actions = []
        self.redrawing = False
        self.redraw_asked = False
        self.error_shown = False
        self.debug_msg = ""
        self.debug_wanted = False
        self.exception = Exception('No information')
        self.hl_error_src = None
        self.hl_error_command_src = None
        self.hl_ok_src = None
        self.hl_progress_src = None

    def findCoqProject(self, directory):
        if '_CoqProject' in os.listdir(directory):
            return directory + '/_CoqProject'
        if len(directory.split('/')) > 2:
            return self.findCoqProject('/'.join(directory.split('/')[:-1]))
        return None

    def restart(self):
        self.buf = self.vim.current.buffer
        return self.ct.restart()

    def stop(self):
        self.must_stop = True
        self.ct.kill()
        self.printer.stop()
        self.printer.join()

    def join(self):
        if self.hl_error_src != None:
            self.buf.clear_highlight(self.hl_error_src)
        if self.hl_error_command_src != None:
            self.buf.clear_highlight(self.hl_error_command_src)
        if self.hl_progress_src != None:
            self.buf.clear_highlight(self.hl_progress_src)
        if self.hl_ok_src != None:
            self.buf.clear_highlight(self.hl_ok_src)
        Thread.join(self)

    def debug(self, msg):
        if self.debug_wanted:
            self.debug_msg += msg

    def version(self, args=[]):
        return self.parser.version()

    def build(self):
        filename = self.buf.name
        if filename != "" and filename[0] == '/':
            coqbuild(filename, self.vim, self.parser.getCoqc(), self.parser.getCoqdep(),
                    self.parser.getArgs())

    def flush_debug(self):
        m = self.debug_msg
        self.debug_msg = ""
        return m

    def ask_redraw(self):
        quit = False
        with self.running_lock:
            if self.redrawing:
                self.redraw_asked = True
                quit = True
            self.redrawing = True
        if quit:
            return
        self.vim.async_call(recolor, self)

    def check_modification(self):
        if self.error_shown:
            self.error_shown = False
            self.ask_redraw()
        # It would be too long to check everything, but incorect to simply
        # revert anything after the current position of the cursor, since it is
        # the position *after* the modification, not the position of the modification.
        # We cannot get the position of the modification, so look for the cursor
        # position and check everything from at most 3 lines above, just to be
        # sure we don't forget anything.
        ans = request(self.vim, CursorRequester(self.vim, self.buf))
        (line, col) = (0,0)
        predicate = lambda x: x <= (line-3, 0)
        valid = list(filter(predicate, self.valid_dots))
        if valid and len(valid) > 0:
            (line, col, msg) = valid[-1]
        n = len(valid)
        for v in self.valid_dots[n:]:
            (vline, vcol, vmsg) = v
            cmsg = request(self.vim, BetweenRequester(self, (line, col), (vline, vcol-2)))
            self.debug("`{}` :: `{}`".format(cmsg, vmsg))
            if cmsg != vmsg:
                self.undo([len(self.valid_dots) - n])
                break
            (line, col) = (vline, vcol)
            n += 1

    def next(self):
        encoding = 'utf-8'
        with self.running_lock:
            res = request(self.vim, FullstepRequester(self))
            step = res['step']
            if step is not None:
                message = res['message']
                self.running_dots.insert(0, res['running'])
                self.ct.advance(res['message'], res['type'], encoding)
                self.ct.goals(True)
        self.ask_redraw()

    def undo(self, args = []):
        steps = args[0] if len(args) > 0 else  1

        should_stop = False
        with self.running_lock:
            should_stop = self.running_dots != []
        if should_stop:
            self.cancel()

        if steps < 1 or self.valid_dots == []:
            return

        self.ct.rewind(steps)
        with self.running_lock:
            self.valid_dots = self.valid_dots[:len(self.valid_dots) - steps]
            self.ct.goals()
        if len(args) == 0:
            self.vim.async_call(goto_last_dot, self)
        self.ask_redraw()

    def cursor(self, args=[]):
        encoding = 'utf-8'

        ans = request(self.vim, CursorRequester(self.vim, self.buf))
        if ans == None:
            return
        (cline, ccol) = ans
        cline -= 1
        (line, col, msg)  = self.valid_dots[-1] if self.valid_dots and self.valid_dots != [] else (0,0,"")
        if cline <= line or (cline == line and ccol <= col):
            predicate = lambda x: x <= (cline, ccol+2)
            lst = list(filter(predicate, self.valid_dots))
            steps = len(self.valid_dots) - len(lst)
            (line, col, msg)  = lst[-1] if lst and lst != [] else (0,0,"")
            self.undo([steps])
        else:
            res = request(self.vim, FullstepsRequester(self, cline, ccol))
            self.ask_redraw()

    def goto_last_dot(self):
        if self.vim.eval("g:coquille_auto_move") == 'true':
            (line, col, msg) = (0,1,"") if self.valid_dots == [] else self.valid_dots[-1]
            (line, col, msg) = (line,col,"") if self.running_dots == [] else self.running_dots[-1]
            if self.buf.name == self.vim.current.buffer.name:
                self.vim.current.window.cursor = (line+1, col)

    def cancel(self, args=[]):
        with self.running_lock:
            if self.running_dots != []:
                self.ct.interupt()
        self.ask_redraw()

    def check(self, terms):
        with self.running_lock:
            self.ct.check(terms)

    def doprint(self, terms):
        with self.running_lock:
            self.ct.doprint(terms)

    def locate(self, terms):
        with self.running_lock:
            self.ct.dolocate(terms)

    def search(self, terms):
        with self.running_lock:
            self.ct.search(terms)

    def query(self, terms):
        with self.running_lock:
            self.ct.query(terms)

    def searchabout(self, terms):
        with self.running_lock:
            self.ct.searchabout(terms)

    def add_action(self, typ, args=[]):
        self.actions.append((typ, args))

    def run(self):
        try:
            while not self.must_stop:
                if self.actions == []:
                    time.sleep(0.01)
                    continue
                (typ, args) = self.actions[0]
                if typ == 'next':
                    self.next()
                if typ == 'cursor':
                    self.cursor()
                if typ == 'undo':
                    self.undo()
                if typ == 'cancel':
                    self.cancel()
                if typ == 'modified':
                    self.check_modification()
                if typ == 'check':
                    self.check(args[0])
                if typ == 'print':
                    self.doprint(args[0])
                if typ == 'locate':
                    self.locate(args[0])
                if typ == 'searchabout':
                    self.searchabout(args[0])
                if typ == 'search':
                    self.search(args[0])
                if typ == 'query':
                    self.query(args[0])
                self.actions = self.actions[1:]
        except BaseException as e:
            self.exception = e

    def parseMessage(self, msg, msgtype):
        if isinstance(msg, Ok):
            if msgtype == "addgoal":
                with self.running_lock:
                    if self.running_dots != []:
                        dot = self.running_dots.pop()
                        self.valid_dots.append(dot)
                self.vim.async_call(goto_last_dot, self)
            self.ask_redraw()
        elif msgtype == "goal":
            with self.running_lock:
                self.running_dots = []
            self.ask_redraw()
        else:
            if isinstance(msg, Err):
                with self.running_lock:
                    self.printer.flushInfo()
                    self.printer.addInfo(msg.err)
                    if self.running_dots != []:
                        self.vim.async_call(reerror, self, self.running_dots.pop(), msg.loc_s, msg.loc_e)
                    self.ct.silent_interupt()
                    self.running_dots = []
                self.ask_redraw()

    def addInfo(self, info):
        self.printer.addInfo(info)

    def flushInfo(self):
        self.printer.flushInfo()

    def addGoal(self, goals):
        self.printer.addGoal(goals)

    def showError(self, pos, start, end):
        """Show error by highlighting the area. POS is the position of the next dot,
START is the begining of the actual error, in number of characters from the
previous dot. END is the end of the actual error, in number of characters from
the previous dot."""
        if self.valid_dots == []:
            (line, col) = (0, 0)
        else:
            (line, col, msg) = self.valid_dots[-1]
        (eline, ecol, msg) = pos
        self.error_shown = True

        # Show the yellow background
        self.hl_error_command_src = self.vim.new_highlight_source()
        self.buf.add_highlight("CoqErrorCommand", line, col, ecol if line == eline else -1,
                src_id=self.hl_error_command_src)
        if self.hl_progress_src != None:
            self.buf.clear_highlight(self.hl_progress_src)
            self.hl_progress_src = None
        for i in range(line+1, eline):
            self.buf.add_highlight("CoqErrorCommand", i, 0, -1, src_id=self.hl_error_command_src)
        if line != eline:
            self.buf.add_highlight("CoqErrorCommand", eline, 0, ecol, src_id=self.hl_error_command_src)

        # Show the red background
        self.hl_error_src = self.vim.new_highlight_source()
        while len(self.buf[line]) - col < start:
            diff = len(self.buf[line]) - col + 1
            line = line+1
            col = 0
            start = start - diff
            end = end - diff
        ecol = col
        col = col + start
        eline = line
        while len(self.buf[eline]) - ecol < end:
            diff = len(self.buf[eline]) - ecol
            eline = eline+1
            ecol = 0
            end = end - diff
        ecol = ecol + end
        self.buf.add_highlight("CoqError", line, col, ecol if line == eline else -1,
                src_id=self.hl_error_src)
        for i in range(line+1, eline):
            self.buf.add_highlight("CoqError", i, 0, -1, src_id=self.hl_error_src)
        if line != eline:
            self.buf.add_highlight("CoqError", eline, 0, ecol, src_id=self.hl_error_src)

    def removeInfo(self):
        if not hasattr(self, 'info_buf'):
            return
        buf = self.find_buf(self.info_buf)
        del buf[:]

    def showInfo(self, info):
        if not hasattr(self, 'info_buf'):
            return
        buf = self.find_buf(self.info_buf)
        self.debug("Print info: " + str(info) + "\n")
        if isinstance(info, list):
            for i in info:
                self.showOneInfo(buf, i)
        else:
            self.showOneInfo(buf, info)

    def showOneInfo(self, buf, info):
        if info is None:
            return
        if isinstance(info, list):
            for i in info:
                self.showOneInfo(buf, i)
            return
        if isinstance(info, RichPP):
            info = info.parts
            try:
                info.remove(None)
            except:
                pass
            info = ''.join(info)
        lst = map(lambda s: s.encode('utf-8'), info.split('\n'))
        for l in lst:
            buf.append(l)

    def showGoal(self, goals):
        if not hasattr(self, 'goal_buf'):
            return
        buf = self.find_buf(self.goal_buf)
        blines = []
        if goals is None:
            blines.append('No goals.')
        else:
            sub_goals = goals.fg
            nb_unfocused = goals.bg
            nb_subgoals = len(sub_goals)

            plural_opt = '' if nb_subgoals == 1 else 's'
            blines.append('%d subgoal%s (%d unfocused)' % (nb_subgoals, plural_opt, nb_unfocused))
            blines.append('')

            for idx, sub_goal in enumerate(sub_goals):
                _id = sub_goal.id
                hyps = sub_goal.hyp
                ccl = sub_goal.ccl
                if idx == 0:
                    # we print the environment only for the current subgoal
                    for hyp in hyps:
                        lst = map(lambda s: s.encode('utf-8'), hyp.split('\n'))
                        for line in lst:
                            blines.append(line)
                blines.append('')
                blines.append('======================== ( %d / %d )' % (idx+1 , nb_subgoals))
                lines = map(lambda s: s.encode('utf-8'), ccl.split('\n'))
                for line in lines:
                    blines.append(line)
                blines.append('')
        del buf[:]
        buf.append(blines)

    def redraw(self, args=[]):
        old_hl_ok_src = self.hl_ok_src
        old_hl_progress_src = self.hl_progress_src
        self.hl_ok_src = None
        self.hl_progress_src = None

        # Color again
        if self.hl_error_src != None and not self.error_shown:
            self.buf.clear_highlight(self.hl_error_src)
            self.hl_error_src = None
        if self.hl_error_command_src != None and not self.error_shown:
            self.buf.clear_highlight(self.hl_error_command_src)
            self.hl_error_command_src = None
        if self.valid_dots != []:
            (eline, ecol, msg) = self.valid_dots[-1]
        else:
            (eline, ecol) = (0, 0)

        if self.running_dots != []:
            (line, col, msg) = self.running_dots[0]
            self.hl_progress_src = self.vim.new_highlight_source()
            self.buf.add_highlight("SentToCoq", eline, ecol, col if eline == line else -1, src_id=self.hl_progress_src)
            for i in range(eline+1, line):
                self.buf.add_highlight("SentToCoq", i, 0, -1, src_id=self.hl_progress_src)
            if line != eline:
                self.buf.add_highlight("SentToCoq", line, 0, col, src_id=self.hl_progress_src)

        if self.valid_dots != []:
            self.hl_ok_src = self.vim.new_highlight_source()
            for i in range(0, eline):
                self.buf.add_highlight("CheckedByCoq", i, 0, -1, src_id=self.hl_ok_src)
            self.buf.add_highlight("CheckedByCoq", eline, 0, ecol, src_id=self.hl_ok_src)

        if old_hl_ok_src:
            self.buf.clear_highlight(old_hl_ok_src)
        if old_hl_progress_src:
            self.buf.clear_highlight(old_hl_progress_src)

        # If a redraw was requested during the evaluation of this one, redraw
        # again.
        if self.redraw_asked:
            self.redraw_asked = False
            self.redraw(args)
        self.redrawing = False

    def findNextStep(self):
        (line, col) = (0,0)
        if self.running_dots != []:
            (line, col, msg)  = self.running_dots[0] if self.running_dots else (0,0,"")
        else:
            (line, col, msg)  = self.valid_dots[-1] if self.valid_dots and self.valid_dots != [] else (0,0,"")
        p = Parser(self.buf)
        try:
            unit = p.getUnit(line, col)
        except:
            return None
        return { 'start':(line,col) , 'stop':(unit[0], unit[1]), 'content': unit[2],
                'type': unit[3] }

    def find_buf(self, num):
        for b in self.vim.buffers:
            if num == b.number:
                return b
        return None

    def _between(self, begin, end):
        """
        Returns a string corresponding to the portion of the buffer between the
        [begin] and [end] positions.
        """
        (bline, bcol) = begin
        (eline, ecol) = end
        acc = ""
        for line, str in enumerate(self.buf[bline:eline + 1]):
            start = bcol if line == 0 else 0
            stop  = ecol + 1 if line == eline - bline else len(str)
            stopchr = '' if line == eline - bline else '\n'
            acc += str[start:stop] + stopchr
        return acc
