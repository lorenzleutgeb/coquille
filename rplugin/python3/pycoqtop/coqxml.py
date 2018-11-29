import xml.etree.ElementTree as ET
import time

from io import StringIO
from threading import Thread, Event
from os import read
from .coqapi import Ok, Err
from .xmltype import *

class CoqHandler:
    def __init__(self, printer):
        self.printer = printer
        self.currentContent = ""
        self.currentProcess = None
        self.messageLevel = None
        self.reply = None
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

        self.event_read = Event()
        self.event_cont = Event()
        self.event_cont.set()

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
        elif tag == 'goal' and self.currentProcess == 'goals_bg':
            self.goals_bg += 1
        elif tag == 'goal' and self.currentProcess == 'goals_shelved':
            self.goals_shelved += 1
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
        elif self.currentProcess == 'message' and tag == 'message_level':
            self.messageLevel = attributes['val']
        elif tag == 'message' and self.currentProcess == 'waitmessage':
            self.currentProcess = 'message'

    # Call when an element ends
    def end(self, tag):
        if tag == "value":
            if self.val == 'good':
                self.reply = Ok(self.state_id)
            else:
                self.reply = Err(None, False if not hasattr(self, "loc_s") else int(self.loc_s), False if not hasattr(self, "loc_e") else int(self.loc_e))
                self.printer.addInfo(self.currentContent)
                self.currentContent = ''
                self.nextFlush = False
            self.printer.debug("Process returned: " + str(self.reply))
            self.event_cont.clear()
            self.event_read.set()
            self.event_cont.wait()
            self.printer.debug("Continuing to parse things...\n")
            self.state_id = None
            self.val = None
            self.currentProcess = None
        elif tag == 'goals':
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
        elif tag == 'list' and self.currentProcess == 'goal_hyps':
            self.goal_hyps = [] # TODO
            self.currentContent = ''
            self.currentProcess = 'goal'
        elif tag == 'goal' and self.currentProcess == 'goal':
            self.goals_fg.append(Goal(self.goal_id, self.goal_hyps, self.currentContent))
            self.currentContent = ''
            self.currentProcess = 'fg'
        elif tag == 'list' and self.currentProcess == 'goals_fg':
            self.currentProcess = 'goals_bg'
        elif tag == 'list' and self.currentProcess == 'goals_bg':
            self.currentProcess = 'goals_shelved'
        elif tag == 'list' and self.currentProcess == 'goals_shelved':
            self.currentProcess = 'goals_given_up'
        elif tag == 'feedback_content' and self.currentProcess == 'waitmessage':
            self.printer.debug(self.messageLevel + ": " + self.currentContent)
            self.printer.addInfo(self.currentContent)
            self.currentProcess = None
            self.messageLevel = None
            self.currentContent = ''
        elif tag == 'message' and self.currentProcess == 'message':
            self.currentProcess = 'waitmessage'
     
    # Call when a character is read
    def data(self, content):
        if self.currentProcess == 'message' or self.currentProcess == 'value' or self.currentProcess == 'goal_id' or self.currentProcess == 'goal':
            self.currentContent += content

    def nextAnswer(self):
        self.event_read.wait(2)
        self.event_read.clear()
        r = self.reply
        self.reply = None
        if self.nextFlush:
            self.printer.flushInfo()
        self.nextFlush = True
        self.event_cont.set()
        return r

class CoqParser(Thread):
    def __init__(self, process, printer):
        Thread.__init__(self)
        self.cont = True
        self.process = process
        self.printer = printer
        self.target = CoqHandler(printer)
        self.parser = ET.XMLParser(target=self.target)
        self.parser.feed("""
<!DOCTYPE coq [
  <!ENTITY nbsp \"&#xA0;\">
  <!ENTITY gt \">\">
  <!ENTITY lt \"<\">
  <!ENTITY apos \"'\">
]>
<Root>
        """)

    def run(self):
        try:
            while self.cont:
                r = read(self.process.stdout.fileno(), 0x400)
                self.printer.debug("<< " + str(r) + "\n")
                if r == b'':
                    time.sleep(1)
                else:
                    self.parser.feed(r)
        except Exception as e:
            self.printer.debug("WHOOPS!\n")
            self.printer.debug("WHOOPS! " + str(e))
        try:
            self.parser.feed("</Root>")
        except:
            pass
        self.printer.debug("END OF PARSING\n")

    def nextAnswer(self):
        if not self.isAlive():
            self.printer.debug("DEAD :/\n")
            return None
        return self.target.nextAnswer()
    
    def stop(self):
        self.cont = False
        self.join()
