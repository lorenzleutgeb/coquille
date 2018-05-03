from .coqtop import CoqTop
from .coqapi import Ok, Err
from .xmltype import *
from threading import Lock, RLock, Thread


import neovim

import os
import re
import subprocess
import time

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

def getlines(vim, start=1, end='$'):
    if end == '$':
        end = len(vim.current.buffer)
    max = 5000
    lines = []
    current = start
    while current <= end:
        lines += vim.call('getline', current, current + max)
        current += max + 1
    return lines

@neovim.plugin
class Main(object):
    def __init__(self, vim):
        self.vim = vim
        self.actionner = Actionner(self)
        self.ct = CoqTop(self.actionner)
        self.actionner.ct = self.ct
        self.running = False

    def diditdieyet(self):
        "Checks whether the actionner thread died and re-raise its exception."
        if not self.actionner.isAlive():
            raise self.actionner.exception

    @neovim.function('CoqVersion', sync=True)
    def version(self, args=[]):
        options = ['coqtop', '-print-version']
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
        self.currentVersion = version
        self.vim.command('echo "Running with coq {}"'.format(version))

    @neovim.function('CoqLaunch', sync=True)
    def launch(self, args=[]):
        if self.running:
            #self.vim.err_write("Coquille is already running!")
            return
        self.version()
        currVer = self.currentVersion.split('.')
        if currVer[0] != "8" or int(currVer[1]) < 6:
            raise Exception("Unsupported version {} (currently supported: >=8.6, <9)"\
                .format(self.currentVersion))
        self.running = True
        if self.ct.restart():
            #*self.vim.eval("map(copy(a:000),'expand(v:val)')")):
            self.vim.call('coquille#Register')
            self.vim.call('coquille#ShowPanels')
            self.actionner.start()
        else:
            self.vim.command('echo "Coq could not be launched!"')
            self.running = False

    @neovim.function('CoqStop', sync=True)
    def stop(self, args=[]):
        if not self.running:
            self.vim.err_write('Coquille is already stopped!')
            return
        self.running = False
        self.actionner.stop()
        self.ct.kill()
        self.vim.call('coquille#KillSession')
        self.actionner.join()

    @neovim.function('CoqModify', sync=True)
    def modify(self, args=[]):
        if not self.running:
            return
        self.diditdieyet()
        self.actionner.add_action('modified')

    @neovim.function('CoqNext', sync=True)
    def next(self, args=[]):
        if not self.running:
            return
        self.diditdieyet()
        self.actionner.add_action('next')

    @neovim.function('CoqUndo', sync=False)
    def undo(self, args = []):
        if not self.running:
            return
        self.diditdieyet()
        self.actionner.add_action('undo')

    @neovim.function('CoqToCursor', sync=False)
    def stepToCursor(self, args=[]):
        if not self.running:
            return
        self.diditdieyet()
        self.actionner.add_action('cursor')

    @neovim.function('CoqCancel')
    def cancel(self, args=[]):
        self.diditdieyet()
        self.actionner.add_action('cancel')

    @neovim.function('CoqSearch', sync=True)
    def search(self, args=[]):
        if not self.running:
            return
        self.diditdieyet()
        self.actionner.add_action('search', args)

    @neovim.function('CoqCheck', sync=True)
    def check(self, args=[]):
        if not self.running:
            return
        self.diditdieyet()
        self.actionner.add_action('check', args)

    @neovim.function('CoqSearchAbout', sync=True)
    def searchabout(self, args=[]):
        if not self.running:
            return
        self.diditdieyet()
        self.actionner.add_action('searchabout', args)

    @neovim.function('CoqLocate', sync=True)
    def locate(self, args=[]):
        if not self.running:
            return
        self.diditdieyet()
        self.actionner.add_action('locate', args)

    @neovim.function('CoqPrint', sync=True)
    def doprint(self, args=[]):
        if not self.running:
            return
        self.diditdieyet()
        self.actionner.add_action('print', args)

    @neovim.function('CoqQuery', sync=True)
    def query(self, args=[]):
        if not self.running:
            return
        self.diditdieyet()
        self.actionner.add_action('query', args)

    @neovim.function('CoqRedraw', sync=True)
    def redraw(self, args=[]):
        self.diditdieyet()
        self.actionner.redraw(args)

    @neovim.function('CoqDebug', sync=True)
    def debug(self, args=[]):
        self.actionner.debug_wanted = True
        self.vim.command('echo "running: ' + str(self.actionner.running_dots) + '"')
        self.vim.command('echo "valid: ' + str(self.actionner.valid_dots) + '"')
        self.vim.command('echo "state: ' + str(self.actionner.ct.state_id) + '"')
        self.vim.command('echo "debug: '+str(self.actionner.flush_debug()).replace("\"", "\\\"")+'"')

    @neovim.function('CoqErrorAt', sync=True)
    def showError(self, pos):
        self.diditdieyet()
        self.actionner.showError(pos)

    @neovim.function('CoqRedrawInfo', sync=True)
    def showInfo(self, info):
        self.diditdieyet()
        self.actionner.showInfo(info)

    @neovim.function('CoqRedrawGoal', sync=True)
    def showGoal(self, goal):
        self.diditdieyet()
        self.actionner.showGoal(goal)


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
            time.sleep(0.01)
        return self.result

class StepRequester(Requester):
    def __init__(self, obj):
        Requester.__init__(self)
        self.obj = obj

    def request(self):
        self.setResult(self.obj.findNextStep())

class BetweenRequester(Requester):
    def __init__(self, obj, start, stop):
        Requester.__init__(self)
        self.obj = obj
        self.start = start
        self.stop = stop

    def request(self):
        self.setResult(self.obj._between(self.start, self.stop))

class CursorRequester(Requester):
    def __init__(self, vim):
        Requester.__init__(self)
        self.vim = vim

    def request(self):
        self.setResult(self.vim.current.window.cursor)

class LineRequester(Requester):
    def __init__(self, vim, line):
        Requester.__init__(self)
        self.vim = vim
        self.line = line

    def request(self):
        buff = self.vim.current.buffer
        self.setResult(buff[self.line])

class Actionner(Thread):
    def __init__(self, main):
        Thread.__init__(self)
        self.ct = None
        self.must_stop = False
        self.vim = main.vim
        self.main = main
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

    def stop(self):
        self.must_stop = True

    def debug(self, msg):
        if self.debug_wanted:
            self.debug_msg += msg

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
        (cline, ccol) = request(self.vim, CursorRequester(self.vim))
        (line, col)  = self.valid_dots[-1] if self.valid_dots and self.valid_dots != [] else (0,0)
        if cline <= line or (cline == line + 1 and ccol <= col):
            self.cursor()

    def next(self):
        #encoding = self.vim.eval("&encoding") or 'utf-8'
        encoding = 'utf-8'
        with self.running_lock:
            step = request(self.vim, StepRequester(self))
            if step is None: return
            message = request(self.vim, BetweenRequester(self, step['start'], step['stop']))
            (eline, ecol) = step['stop']
            line = request(self.vim, LineRequester(self.vim, eline))[:ecol]
            ecol += len(bytes(line, encoding)) - len(line)
            self.running_dots.insert(0, (eline, ecol + 1))
            self.ct.advance(message, encoding)
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
        self.ask_redraw()

    def cursor(self, args=[]):
        #encoding = self.vim.eval("&encoding") or 'utf-8'
        encoding = 'utf-8'

        (cline, ccol) = request(self.vim, CursorRequester(self.vim))
        (line, col)  = self.valid_dots[-1] if self.valid_dots and self.valid_dots != [] else (0,0)
        if cline <= line or (cline == line + 1 and ccol <= col):
            predicate = lambda x: x <= (cline - 1, ccol)
            lst = list(filter(predicate, self.valid_dots))
            steps = len(self.valid_dots) - len(lst)
            self.undo([steps])
        else:
            with self.running_lock:
                while True:
                    step = request(self.vim, StepRequester(self))
                    if step is None: break
                    if step['stop'] <= (cline - 1, ccol):
                        (eline, ecol) = step['stop']
                        line = request(self.vim, LineRequester(self.vim, eline))[:ecol]
                        ecol += len(bytes(line, encoding)) - len(line)
                        self.running_dots.insert(0, (eline, ecol + 1))
                        message = request(self.vim, BetweenRequester(self, step['start'], step['stop']))
                        self.ct.advance(message, encoding)
                        self.ct.goals(True)
                    else:
                        break
            self.ask_redraw()

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
            self.ct.locate(terms)

    def search(self, terms):
        with self.running_lock:
            self.ct.search(terms)

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
                self.vim.async_call(regoal, self, msg.val)
                with self.running_lock:
                    if self.running_dots != []:
                        dot = self.running_dots.pop()
                        self.valid_dots.append(dot)
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
        start = { 'line': line + 1, 'col': col }
        (line, col) = pos
        stop = { 'line': line + 1, 'col': col }
        zone = self._make_matcher(start, stop)
        self.error_shown = True
        self.vim.command("let b:errors = matchadd('CoqError', '%s')" % zone)

    def showInfo(self, info):
        #self.vim.command('echo "' + str(info).replace("\"", "\\\"") + '"')
        buf = self.find_buf("Infos")
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
        #self.vim.command('echo "' + str(info).replace("\"", "\\\"") + '"')
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
        buf = self.find_buf("Goals")
        del buf[:]
        if goal is None:
            return
        if (not hasattr(goal, 'val')) and (isinstance(goal, tuple) or isinstance(goal, list)):
            for g in goal:
                return self.showGoal(g)
            return
        if goal.val is None:
            buf.append('No goals.')
        else:
            goals = goal.val
            sub_goals = goals.fg
            unfocused_goals = goals.bg

            nb_unfocused = self.focused(unfocused_goals)
            nb_subgoals = len(sub_goals)
            plural_opt = '' if nb_subgoals == 1 else 's'
            buf.append(['%d subgoal%s (%d unfocused)' % (nb_subgoals, plural_opt, nb_unfocused), ''])

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
                            buf.append(line)
                buf.append('')
                buf.append('======================== ( %d / %d )' % (idx+1 , nb_subgoals))
                lines = map(lambda s: s.encode('utf-8'), ccl.split('\n'))
                for line in lines:
                    buf.append(line)
                buf.append('')

    def redraw(self, args=[]):
        # Clear current coloring (dirty)
        if int(self.vim.eval('b:checked')) != -1:
            self.vim.command('call matchdelete(b:checked)')
            self.vim.command('let b:checked = -1')
        if int(self.vim.eval('b:sent')) != -1:
            self.vim.command('call matchdelete(b:sent)')
            self.vim.command('let b:sent = -1')
        if int(self.vim.eval('b:errors')) != -1:
            self.vim.command('call matchdelete(b:errors)')
            self.vim.command('let b:errors = -1')
        stop = { 'line': 0 , 'col': 0 }
        if self.valid_dots != []:
            (line, col) = self.valid_dots[-1]
            start = { 'line': 0 , 'col': 0 }
            stop  = { 'line': line + 1, 'col': col }
            zone = self._make_matcher(start, stop)
            self.vim.command("let b:checked = matchadd('CheckedByCoq', '%s')" % zone)
        if self.running_dots != []:
            (line, col) = self.running_dots[0]
            rstop = { 'line': line + 1, 'col': col }
            zone = self._make_matcher(stop, rstop)
            self.vim.command("let b:sent = matchadd('SentToCoq', '%s')" % zone)
        time.sleep(0.01)
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

    def find_buf(self, name):
        buff = None
        for b in self.vim.buffers:
            if re.match(".*"+name+"$", b.name):
                return b
        return None

    def _between(self, begin, end):
        """
        Returns a string corresponding to the portion of the buffer between the
        [begin] and [end] positions.
        """
        (bline, bcol) = begin
        (eline, ecol) = end
        buf = self.vim.current.buffer
        acc = ""
        for line, str in enumerate(buf[bline:eline + 1]):
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
        buff = self.vim.current.buffer
        blen = len(buff)
        bullets = ['{', '}', '-', '+', '*']
        # We start by striping all whitespaces (including \n) from the beginning of
        # the chunk.
        while line < blen and buff[line][col:].strip() == '':
            line += 1
            col = 0
    
        if line >= blen: return
    
        while buff[line][col] == ' ' or buff[line][col] == '\t': # FIXME: keeping the stripped line would be
            col += 1                                             #   more efficient.
    
        # Then we check if the first character of the chunk is a bullet.
        # Intially I did that only when I was sure to be in a proof (by looking in
        # [encountered_dots] whether I was after a "collapsable" chunk or not), but
        #   1/ that didn't play well with coq_to_cursor (as the "collapsable chunk"
        #      might not have been sent/detected yet).
        #   2/ The bullet chars can never be used at the *beginning* of a chunk
        #      outside of a proof. So the check was unecessary.
        if buff[line][col] in bullets:
            return (line, col + 1)
    
        # We might have a commentary before the bullet, we should be skiping it and
        # keep on looking.
        tail_len = len(buff[line]) - col
        if (tail_len - 1 > 0) and buff[line][col] == '(' and buff[line][col + 1] == '*':
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
        b = self.vim.current.buffer
        if line >= len(b): return
        s = b[line][col:]
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
        elif dot_pos + col > 0 and b[line][col + dot_pos - 1] == '.':
            # FIXME? There might be a cleaner way to express this.
            # We don't want to capture ".."
            if dot_pos + col > 1 and b[line][col + dot_pos - 2] == '.':
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
        b = self.vim.current.buffer
        if line >= len(b): return
        s = b[line][col:]
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
    
        b = self.vim.current.buffer
        if line >= len(b): return
        s = b[line][col:]
        com_start = s.find('(*')
        com_end = s.find('*)')
        if com_end > -1 and (com_end < com_start or com_start == -1):
            return self._skip_comment(line, col + com_end + 2, nb_left - 1)
        elif com_start > -1:
            return self._skip_comment(line, col + com_start + 2, nb_left + 1)
        else:
            return self._skip_comment(line + 1, 0, nb_left)

    def _make_matcher(self, start, stop):
        if start['line'] == stop['line']:
            return self._easy_matcher(start, stop)
        else:
            return self._hard_matcher(start, stop)
    
    def _easy_matcher(self, start, stop):
        startl = ""
        startc = ""
        if start['line'] > 0:
            startl = "\%>{0}l".format(start['line'] - 1)
        if start['col'] > 0:
            startc = "\%>{0}c".format(start['col'])
        return '{0}{1}\%<{2}l\%<{3}c'.format(startl, startc, stop['line'] + 1, stop['col'] + 1)
    
    def _hard_matcher(self, start, stop):
        first_start = {'line' : start['line'], 'col' : start['col']}
        first_stop =  {'line' : start['line'], 'col' : 4242}
        first_line = self._easy_matcher(first_start, first_stop)
        mid_start = {'line' : start['line']+1, 'col' : 0}
        mid_stop =  {'line' : stop['line']-1 , 'col' : 4242}
        middle = self._easy_matcher(mid_start, mid_stop)
        last_start = {'line' : stop['line'], 'col' : 0}
        last_stop =  {'line' : stop['line'], 'col' : stop['col']}
        last_line = self._easy_matcher(last_start, last_stop)
        return "{0}\|{1}\|{2}".format(first_line, middle, last_line)
