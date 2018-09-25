import neovim

from .coqtop import CoqTop, Version
from .coqapi import Ok, Err
from .xmltype import *
from .projectparser import ProjectParser
from threading import Lock, RLock, Thread

import os
import re
import subprocess
import time
import uuid

def recolor(obj):
    obj.redraw()
def reinfo(obj, msg):
    obj.showInfo(msg)
def regoal(obj, msg):
    obj.showGoal(msg)
def reerror(obj, pos):
    obj.showError(pos)
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
        if self.vim.eval("w:coquille_running") != 'false':
            self.vim.command('echo "Coquille is already running in this window!"')
            return
        random_name = str(uuid.uuid4())
        self.actionners[random_name] = Actionner(self.vim)
        self.currentVersion = self.actionners[random_name].version(args)
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
        self.vim.command('echo "Wins: ' + str(self.goal_wins) + '"')
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
        self.vim.command('echo "'+name+'"')
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
    def showError(self, pos):
        name = self.vim.eval("w:coquille_running")
        if name == 'false':
            return
        actionner = self.actionners[name]
        self.diditdieyet()
        actionner.showError(pos)

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
        self.haveResult = False

    def setResult(self, result):
        self.result = result
        self.haveResult = True

    def waitResult(self):
        while not self.haveResult:
            time.sleep(0.001)
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
        res['running'] = (eline, ecol + 1)
        res["message"] = self.obj._between(step['start'], step['stop'])
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
                if res['step']['stop'] <= (self.cline-1, self.ccol):
                    self.obj.running_dots.insert(0, res['running'])
                    self.obj.ct.advance(res['message'], encoding)
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
        self.setResult(self.buf[self.line])

class Actionner(Thread):
    def __init__(self, vim):
        Thread.__init__(self)

        coqproject = self.findCoqProject(os.getcwd())
        parser = ProjectParser(coqproject)
        self.ct = CoqTop(self, parser)
        self.coqtopbin = parser.getCoqtop()
        self.vim = vim
        self.buf = self.vim.current.buffer

        self.must_stop = False
        self.running_lock = Lock()
        self.valid_dots = []
        self.running_dots = []
        self.actions = []
        self.redrawing = False
        self.redraw_asked = False
        self.error_shown = False
        self.debug_msg = ""
        self.debug_wanted = False
        self.exception = Exception('No information')
        self.hl_error_src = None
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

    def debug(self, msg):
        if self.debug_wanted:
            self.debug_msg += msg

    def version(self, args=[]):
        options = [self.coqtopbin, '--print-version']
        if os.name == 'nt':
            coqtop = subprocess.Popen(options + list(args),
                stdin = subprocess.PIPE, stdout = subprocess.PIPE,
                stderr = subprocess.STDOUT)
        else:
            coqtop = subprocess.Popen(options + list(args),
                stdin = subprocess.PIPE, stdout = subprocess.PIPE)
        fd = coqtop.stdout.fileno()
        data = os.read(fd, 0x4000).decode("utf-8")
        version = data.split(' ')[0]
        self.currentVersion = Version(version.split('.'))
        self.ct.currentVersion = self.currentVersion
        return self.currentVersion

    def flush_debug(self):
        m = self.debug_msg
        self.debug_msg = ""
        return m

    def ask_redraw(self):
        with self.running_lock:
            if self.redrawing:
                self.redraw_asked = True
                return
            self.redrawing = True
        self.vim.async_call(recolor, self)

    def check_modification(self):
        if self.error_shown:
            self.error_shown = False
            self.ask_redraw()
        ans = request(self.vim, CursorRequester(self.vim, self.buf))
        if ans == None:
            return
        (cline, ccol) = ans
        (line, col)  = self.valid_dots[-1] if self.valid_dots and self.valid_dots != [] else (0,0)
        if cline <= line or (cline == line + 1 and ccol <= col):
            self.cursor()

    def next(self):
        encoding = 'utf-8'
        with self.running_lock:
            res = request(self.vim, FullstepRequester(self))
            step = res['step']
            if step is None: return
            message = res['message']
            self.running_dots.insert(0, res['running'])
            self.ct.advance(res['message'], encoding)
            self.ct.goals(True)
        self.ask_redraw()

    def undo(self, args = []):
        steps = args[0] if len(args) > 0 else  1
        if steps < 1 or self.valid_dots == []:
            return
        with self.running_lock:
            self.ct.rewind(steps)
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
        (line, col)  = self.valid_dots[-1] if self.valid_dots and self.valid_dots != [] else (0,0)
        if cline <= line or (cline == line + 1 and ccol <= col):
            predicate = lambda x: x <= (cline - 1, ccol)
            lst = list(filter(predicate, self.valid_dots))
            steps = len(self.valid_dots) - len(lst)
            self.undo([steps])
        else:
            res = request(self.vim, FullstepsRequester(self, cline, ccol))
            self.ask_redraw()

    def goto_last_dot(self):
        if self.vim.eval("g:coquille_auto_move") == 'true':
            (line, col) = (0,1) if self.valid_dots == [] else self.valid_dots[-1]
            (line, col) = (line,col) if self.running_dots == [] else self.running_dots[-1]
            if self.buf.name == self.vim.current.buffer.name:
                self.vim.current.window.cursor = (line+1, col)

    def cancel(self, args=[]):
        with self.running_lock:
            self.ct.interupt()
            self.running_dots = []
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
        if self.hl_ok_src != None:
            self.buf.clear_highlight(self.hl_ok_src)
            self.hl_ok_src = None
        if self.hl_progress_src != None:
            self.buf.clear_highlight(self.hl_progress_src)
            self.hl_progress_src = None
        if self.hl_error_src != None:
            self.buf.clear_highlight(self.hl_error_src)
            self.hl_error_src = None

    def parseMessage(self, msg, msgtype):
        if isinstance(msg, Ok):
            if msgtype == "addgoal":
                self.vim.async_call(regoal, self, msg.val)
                with self.running_lock:
                    if self.running_dots != []:
                        dot = self.running_dots.pop()
                        self.valid_dots.append(dot)
                self.vim.async_call(goto_last_dot, self)
                self.ask_redraw()
                self.vim.async_call(reinfo, self, msg.msg)
            if msgtype == "goal":
                self.vim.async_call(regoal, self, msg.val)
            if msgtype == "query":
                self.vim.async_call(reinfo, self, msg.msg)
        elif msgtype == "goal":
            pass
        elif msgtype == "query":
            self.vim.async_call(reinfo, self, msg.err)
        else:
            if isinstance(msg, Err):
                with self.running_lock:
                    self.vim.async_call(reinfo, self, msg.err)
                    self.vim.async_call(reerror, self, self.running_dots.pop())
                    self.ct.silent_interupt()
                    self.running_dots = []

    def showError(self, pos):
        if self.valid_dots == []:
            (line, col) = (0, 0)
        else:
            (line, col) = self.valid_dots[-1]
        (eline, ecol) = pos
        self.error_shown = True
        self.hl_error_src = self.vim.new_highlight_source()
        self.buf.add_highlight("CoqError", line, col, ecol if line == eline else -1,
                src_id=self.hl_error_src)
        if self.hl_progress_src != None:
            self.buf.clear_highlight(self.hl_progress_src)
            self.hl_progress_src = None
        for i in range(line+1, eline):
            self.buf.add_highlight("CoqError", i, 0, -1, src_id=self.hl_error_src)
        if line != eline:
            self.buf.add_highlight("CoqError", eline, 0, ecol, src_id=self.hl_error_src)

    def showInfo(self, info):
        buf = self.find_buf(self.info_buf)
        del buf[:]
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

    def focused(self, goals):
        if goals == []:
            return 0
        if isinstance(goals, Goal):
            return 1
        s = 0
        for g in goals:
            s += self.focused(g)
        return s

    def showGoal(self, goal):
        buf = self.find_buf(self.goal_buf)
        blines = []
        if goal is None:
            del buf[:]
            return
        if (not hasattr(goal, 'val')) and (isinstance(goal, tuple) or isinstance(goal, list)):
            for g in goal:
                return self.showGoal(g)
            return
        if goal.val is None:
            blines.append('No goals.')
        else:
            goals = goal.val
            sub_goals = goals.fg
            unfocused_goals = goals.bg

            nb_unfocused = self.focused(unfocused_goals)
            nb_subgoals = len(sub_goals)
            plural_opt = '' if nb_subgoals == 1 else 's'
            blines.append('%d subgoal%s (%d unfocused)' % (nb_subgoals, plural_opt, nb_unfocused))
            blines.append('')

            for idx, sub_goal in enumerate(sub_goals):
                _id = sub_goal.id
                hyps = sub_goal.hyp
                ccl = sub_goal.ccl
                if isinstance(ccl, RichPP):
                    try:
                        ccl.parts.remove(None)
                    except:
                        pass
                    ccl = ''.join(ccl.parts)
                if idx == 0:
                    # we print the environment only for the current subgoal
                    for hyp in hyps:
                        if isinstance(hyp, RichPP):
                            hyp = hyp.parts
                            try:
                                hyp.remove(None)
                            except:
                                pass
                            hyp = ''.join(hyp)
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
        if self.hl_error_src != None:
            self.buf.clear_highlight(self.hl_error_src)
            self.hl_error_src = None
        if self.valid_dots != []:
            (eline, ecol) = self.valid_dots[-1]
        else:
            (eline, ecol) = (0, 0)

        if self.running_dots != []:
            (line, col) = self.running_dots[0]
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
            (line, col)  = self.running_dots[0] if self.running_dots else (0,0)
        else:
            (line, col)  = self.valid_dots[-1] if self.valid_dots and self.valid_dots != [] else (0,0)
        return self._get_message_range((line, col))

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
            acc += str[start:stop] + '\n'
        return acc

    def _get_message_range(self, after):
        """ See [_find_next_chunk] """
        (line, col) = after
        end_pos = self._find_next_chunk(line, col)
        return { 'start':after , 'stop':end_pos } if end_pos is not None else None
    
    def _find_next_chunk(self, line, col, encoding='utf-8'):
        """
        Returns the position of the next chunk dot after a certain position.
        That can either be a bullet if we are in a proof, or "a string" terminated
        by a dot (outside of a comment, and not denoting a path).
        """
        blen = len(self.buf)
        bullets = ['{', '}', '-', '+', '*']
        # We start by striping all whitespaces (including \n) from the beginning of
        # the chunk.
        while line < blen and self.buf[line][col:].strip() == '':
            line += 1
            col = 0
    
        if line >= blen: return
    
        while self.buf[line][col] == ' ' or self.buf[line][col] == '\t': # FIXME: keeping the stripped line would be
            col += 1                                             #   more efficient.
    
        # Then we check if the first character of the chunk is a bullet.
        # Intially I did that only when I was sure to be in a proof (by looking in
        # [encountered_dots] whether I was after a "collapsable" chunk or not), but
        #   1/ that didn't play well with coq_to_cursor (as the "collapsable chunk"
        #      might not have been sent/detected yet).
        #   2/ The bullet chars can never be used at the *beginning* of a chunk
        #      outside of a proof. So the check was unecessary.
        if self.buf[line][col] in bullets:
            return (line, col + 1)
    
        # We might have a commentary before the bullet, we should be skiping it and
        # keep on looking.
        tail_len = len(self.buf[line]) - col
        if (tail_len - 1 > 0) and self.buf[line][col] == '(' and self.buf[line][col + 1] == '*':
            com_end = self._skip_comment(line, col + 2, 1)
            if not com_end: return
            (line, col) = com_end
            return self._find_next_chunk(line, col)
    
    
        # If the chunk doesn't start with a bullet, we look for a dot.
        return self._find_dot_after(line, col, encoding)

    def _find_dot_after(self, line, col, encoding='utf-8'):
        """
        Returns the position of the next "valid" dot after a certain position.
        Valid here means: recognized by Coq as terminating an input, so dots in
        comments, strings or ident paths are not valid.
        """
        if line >= len(self.buf): return
        s = self.buf[line][col:]
        dot_pos = s.find('.')
        com_pos = s.find('(*')
        str_pos = s.find('"')
        if com_pos == -1 and dot_pos == -1 and str_pos == -1:
            # Nothing on this line
            return self._find_dot_after(line + 1, 0)
        elif dot_pos == -1 or (com_pos > - 1 and dot_pos > com_pos) or (str_pos > - 1 and dot_pos > str_pos):
            if str_pos == -1 or (com_pos > -1 and str_pos > com_pos):
                # We see a comment opening before the next dot
                com_end = self._skip_comment(line, com_pos + 2 + col, 1)
                if not com_end: return
                (line, col) = com_end
                return self._find_dot_after(line, col)
            else:
                # We see a string starting before the next dot
                str_end = self._skip_str(line, str_pos + col + 1)
                if not str_end: return
                (line, col) = str_end
                return self._find_dot_after(line, col)
        elif dot_pos < len(s) - 1 and s[dot_pos + 1] != ' ' and s[dot_pos + 1] != '\t':
            # Sometimes dot are used to access module fields, we don't want to stop
            # just after the module name.
            # Example: [Require Import Coq.Arith]
            return self._find_dot_after(line, col + dot_pos + 1)
        elif dot_pos + col > 0 and self.buf[line][col + dot_pos - 1] == '.':
            # FIXME? There might be a cleaner way to express this.
            # We don't want to capture ".."
            if dot_pos + col > 1 and self.buf[line][col + dot_pos - 2] == '.':
                # But we want to capture "..."
                return (line, dot_pos + col)
            else:
                return self._find_dot_after(line, col + dot_pos + 1)
        else:
            return (line, dot_pos + col)

    def _skip_str(self, line, col):
        """
        Used when we encountered the start of a string before a valid dot (see
        [_find_dot_after]).
        Returns the position of the end of the string.
        """
        if line >= len(self.buf): return
        s = self.buf[line][col:]
        str_end = s.find('"')
        if str_end > -1:
            return (line, col + str_end + 1)
        else:
            return self._skip_str(line + 1, 0)
    
    def _skip_comment(self, line, col, nb_left):
        """
        Used when we encountered the start of a comment before a valid dot (see
        [_find_dot_after]).
        Returns the position of the end of the comment.
        """
        if nb_left == 0:
            return (line, col)
    
        if line >= len(self.buf): return
        s = self.buf[line][col:]
        com_start = s.find('(*')
        com_end = s.find('*)')
        if com_end > -1 and (com_end < com_start or com_start == -1):
            return self._skip_comment(line, col + com_end + 2, nb_left - 1)
        elif com_start > -1:
            return self._skip_comment(line, col + com_start + 2, nb_left + 1)
        else:
            return self._skip_comment(line + 1, 0, nb_left)
