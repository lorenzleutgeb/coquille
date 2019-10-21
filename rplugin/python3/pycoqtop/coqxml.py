import xml.etree.ElementTree as ET
import time
import select

from io import StringIO
from threading import Thread, Event, Lock
from os import read
from .coqapi import Ok, Err
from .xmltype import *

class CoqHandler:
    def __init__(self, state_manager, printer):
        self.printer = printer
        self.state_manager = state_manager
        self.currentContent = ""
        self.oldProcess = None
        self.currentProcess = None
        self.messageLevel = None
        self.val = None
        self.state_id = None
        self.nextFlush = True

        self.goals = None
        self.goals_fg = []
        self.goals_bg = 0
        self.goals_shelved = 0
        self.goals_given_up = 0

        self.goal_id = None
        self.goal_hyps = []
        self.goal_ccl = None

    # Call when an element starts
    def start(self, tag, attributes):
        if tag == 'value':
            self.currentProcess = 'value'
            self.val = attributes['val']
            self.loc_s = None if not 'loc_s' in attributes else attributes['loc_s']
            self.loc_e = None if not 'loc_e' in attributes else attributes['loc_e']
        if tag == 'option' and attributes['val'] == 'none' and self.currentProcess == 'value':
            self.printer.addGoal(None)
        elif tag == 'goals' and self.currentProcess == 'value':
            self.currentProcess = 'goals_fg'
        elif tag == 'list' and self.currentProcess == 'goals_fg':
            self.currentProcess = 'fg'
        elif tag == 'goal' and self.currentProcess == 'fg':
            self.currentProcess = 'goal'
        elif tag == 'pair' and self.currentProcess == 'goals_bg':
            self.currentProcess = 'goals_bg_in'
        elif tag == 'goal' and self.currentProcess == 'goals_bg_in':
            self.goals_bg += 1
        # TODO
        elif tag == 'goal' and self.currentProcess == 'goals_shelved':
            self.goals_shelved += 1
        # TODO
        elif tag == 'goal' and self.currentProcess == 'goals_given_up':
            self.goals_given_up += 1
        elif tag == 'string' and self.currentProcess == 'goal':
            self.currentProcess = 'goal_id'
        elif tag == 'list' and self.currentProcess == 'goal':
            self.currentProcess = 'goal_hyps'
        elif tag == 'state_id' and self.currentProcess == 'value':
            self.state_id = attributes['val']
        elif tag == 'feedback_content' and attributes['val'] == 'message':
            self.currentProcess = 'waitmessage'
        elif tag == 'feedback_content' and attributes['val'] == 'processingin':
            self.currentProcess = 'waitworker'
        elif self.currentProcess == 'message' and tag == 'message_level':
            self.messageLevel = attributes['val']
        elif tag == 'message':
            # older coq (8.6) use a message tag at top-level, newer ones use a
            # message tag inside a feedback_content one.
            # Since there might be more than one message, we want to track when
            # we came from a 'waitmessage' (newer coq).
            self.oldProcess = self.currentProcess
            self.currentProcess = 'message'

    # Call when an element ends
    def end(self, tag):
        if tag == "value":
            if self.nextFlush:
                self.printer.flushInfo()
            self.nextFlush = True
            if self.val == 'good':
                self.state_manager.pull_event(Ok(self.state_id))
            else:
                self.state_manager.pull_event(
                        Err(None, False if not hasattr(self, "loc_s") or self.loc_s is None else int(self.loc_s),
                            False if not hasattr(self, "loc_e") or self.loc_e is None else int(self.loc_e)))
                self.printer.addInfo(self.currentContent)
                self.currentContent = ''
                self.nextFlush = False
            self.state_id = None
            self.val = None
            self.currentProcess = None
        elif tag == 'goals':
            self.printer.debug("Goals: " + str(self.goals_fg) + "\n;; " + str(self.goals_bg) + "\n;; " + str(self.goals_shelved) + "\n;; " + str(self.goals_given_up) + "\n")
            self.printer.addGoal(Goals(self.goals_fg, self.goals_bg, self.goals_shelved, self.goals_given_up))
            self.goals_fg = []
            self.goals_bg = 0
            self.goals_shelved = 0
            self.goals_given_up = 0
            self.currentProcess = 'value'
        elif tag == 'string' and self.currentProcess == 'goal_id':
            self.goal_id = self.currentContent
            self.currentProcess = 'goal'
            self.currentContent = ''
        elif tag == 'goal' and self.currentProcess == 'goal':
            self.goals_fg.append(Goal(self.goal_id, self.goal_hyps, self.currentContent))
            self.goal_hyps = []
            self.currentContent = ''
            self.currentProcess = 'fg'
        elif tag == 'richpp' and self.currentProcess == 'goal_hyps':
            self.goal_hyps.append(self.currentContent)
            self.currentContent = ''
        elif tag == 'list' and self.currentProcess == 'goal_hyps':
            self.currentContent = ''
            self.currentProcess = 'goal'
        elif tag == 'list' and self.currentProcess == 'fg':
            self.currentContent = ''
            self.currentProcess = 'goals_bg'
        elif tag == 'pair' and self.currentProcess == 'goals_bg_in':
            self.currentContent = ''
            self.currentProcess = 'goals_bg'
        elif tag == 'feedback_content' and self.currentProcess == 'waitmessage':
            self.currentProcess = None
            self.oldProcess = None
            self.messageLevel = None
            self.currentContent = ''
        elif tag == 'feedback_content' and self.currentProcess == 'waitworker':
            self.state_manager.setWorker(self.currentContent)
            self.currentContent = ''
        elif tag == 'message' and self.currentProcess == 'message':
            self.currentProcess = 'waitmessage'
            self.printer.debug(self.messageLevel + ": " + str(self.currentContent) + "\n\n")
            self.printer.addInfo(self.currentContent)
            self.currentProcess = self.oldProcess
            self.messageLevel = None
            self.currentContent = ''
     
    # Call when a character is read
    def data(self, content):
        if self.currentProcess == 'message' or self.currentProcess == 'value' or \
                self.currentProcess == 'goal_id' or self.currentProcess == 'goal' or \
                self.currentProcess == 'waitworker' or self.currentProcess == 'goal_hyps':
            self.currentContent += content

class CoqParser(Thread):
    def __init__(self, process, state_manager, printer):
        Thread.__init__(self)
        self.cont = True
        self.process = process
        self.printer = printer
        self.target = CoqHandler(state_manager, printer)
        self.parser = ET.XMLParser(target=self.target)
        self.parser.feed("""
<!DOCTYPE coq [
  <!-- we replace non-breakable spaces with normal spaces, because it would
        make copy-pasting harder -->
  <!ENTITY nbsp \" \">
  <!ENTITY gt \">\">
  <!ENTITY lt \"<\">
  <!ENTITY apos \"'\">
]>
<Root>
        """)

    def run(self):
        self.printer.debug("Running parser...\n")
        try:
            f = self.process.stdout
            while self.cont:
                r, w, e = select.select([ f ], [], [], 0.1)
                if f in r:
                    content = read(f.fileno(), 0x400)
                    self.printer.debug("<< " + str(content) + "\n")
                    self.parser.feed(content)
        except Exception as e:
            self.printer.debug("WHOOPS!\n")
            self.printer.debug("WHOOPS! " + str(e) + "\n")
            self.printer.debug("WHOOPS! " + str(traceback.format_exc()) + "\n")
        try:
            self.parser.feed("</Root>")
        except:
            pass
        self.printer.debug("END OF PARSING\n")

    def stop(self):
        self.cont = False
