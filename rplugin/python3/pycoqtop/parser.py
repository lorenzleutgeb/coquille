class Parser:
    """
    Parser for coq sentences.
    WS: (" " | "\\n" | "\\t")*
    unit: WS (comment | bullet | command)
    comment: "(*" (comment | [^*] | "*" not followed by ")")* "*)"
    bullet: (bullet-selector? WS "{") | "-"+ | "+"+ | "*"+ | "}"
    bullet-selector: ([0-9]+ | "[" WS ident WS "]") WS ":"
    command: (comment | string | [^\\.] | "." not followed by WS)* "."
    string: "\\"" [^\\"]* "\\""
    """
    def __init__(self, buf):
        self.buf = buf
        self.line = 0
        self.col = 0
        self.content = ""
        self.type = None

    def getUnit(self, line, col, encoding='utf-8'):
        """ Return a list of the line, column, content and type of unit that was
            matched, starting a line and col. """
        self.line = line
        self.col = col
        self.content = ""
        self.parseUnit()
        return [self.line, self.col, self.content, self.type]

    def peekNext(self):
        """ Return the next character, but do not advance """
        line = self.buf[self.line]
        if len(line) > self.col:
            return line[self.col]
        elif len(self.buf) > self.line:
            return '\n'
        else:
            raise Exception('No more data')
    
    def getNext(self):
        """ Return the next character, and advance """
        line = self.buf[self.line]
        if len(line) > self.col:
            char = line[self.col]
            self.col += 1
        elif len(self.buf) > self.line:
            self.col = 0
            self.line += 1
            char = '\n'
        else:
            raise Exception('No more data')

        self.content += char
        return char

    def withBacktrack(self, fun, args=None):
        """ Run fun, a function with args (or no argument by default).  Save the
            current state (line, col and content) and restore it if the function
            fails with an exception. """
        state = [self.line, self.col, self.content]
        try:
            if args is None:
                fun()
            else:
                fun(*args)
            return True
        except:
            self.line = state[0]
            self.col = state[1]
            self.content = state[2]
        return False
    
    def parseUnit(self):
        """ unit: WS (comment | bullet | command) """
        self.parseWS()
        if self.peekNext() == '(' and self.withBacktrack(self.parseComment):
            return
        if self.withBacktrack(self.parseBullet):
            return
        return self.parseCommand()

    def parseWS(self):
        """ WS: (" " | "\\n" | "\\t")* """
        char = self.peekNext()
        if char in [' ', '\n', '\t']:
            self.getNext()
            self.parseWS()

    def parseComment(self, gotParenthesis = 0):
        """ comment: "(*" (comment | [^*] | "*" not followed by ")")* "*)" """
        if ((gotParenthesis > 0) or self.getNext() == '(') and \
                ((gotParenthesis > 1) or self.getNext() == '*'):
            while self.parseCommentInside():
                continue
        else:
            raise Exception('Not a comment')
        self.type = 'comment'

    def parseCommentInside(self):
        nextchr = self.getborring(['(', '*'])
        if nextchr == '(' and self.withBacktrack(self.parseComment, [1]):
            return True
        if nextchr != '*':
            return True
        if self.peekNext() == ')':
            self.getNext()
            return False
        return True
    
    def parseBullet(self):
        """ bullet: (bullet-selector? WS "{") | "-"+ | "+"+ | "*"+ | "}" """
        if self.withBacktrack(self.parseBrace):
            self.type = 'bullet'
            return
        num = 0
        while self.peekNext() == '-':
            num += 1
            self.getNext()
        if num > 0:
            self.type = 'bullet'
            return
        while self.peekNext() == '+':
            num += 1
            self.getNext()
        if num > 0:
            self.type = 'bullet'
            return
        while self.peekNext() == '*':
            num += 1
            self.getNext()
        if num > 0:
            self.type = 'bullet'
            return
        if self.getNext() == '}':
            self.type = 'bullet'
            return
        raise Exception('Not a bullet')
    
    def parseBrace(self):
        self.withBacktrack(self.parseBulletSelector)
        self.parseWS()
        if self.getNext() == '{':
            return
        raise Exception('No opening curly brace')

    def parseBulletSelector(self):
        """ bullet-selector: ([0-9]+ | "[" WS ident WS "]") WS ":" """
        if self.withBacktrack(self.parseBulletSelectorNum):
            self.parseWS()
            if self.getNext() == ':':
                return
            else:
                raise Exception('not a numeric goal selector')
        if self.getNext() == '[':
            self.parseWS()
            self.parseIdent()
            self.parseWS()
            if self.getNext() == ']':
                self.parseWS()
                if self.getNext() == ':':
                    return
            raise Exception('not a named goal selector')
        raise Exception('not a goal selector at all')

    def parseBulletSelectorNum(self):
        n = False
        while self.peekNext() in ['0','1','2','3','4','5','6','7','8','9']:
            self.getNext()
            n = True
        if not n:
            raise Exception('not a numeric goal selector')

    def parseIdent(self):
        """
        first_letter      ::=  a..z ∣ A..Z ∣ _ ∣ unicode-letter
        subsequent_letter ::=  a..z ∣ A..Z ∣ 0..9 ∣ _ ∣ ' ∣ unicode-letter ∣ unicode-id-part
        ident             ::=  first_letter[subsequent_letter…subsequent_letter]
        """
        nextchr = self.getNext()
        if nextchr == '_' or ord(nextchr) > 127 or \
                (ord(nextchr) >= ord('a') and ord(nextchr) <= ord('z')) or \
                (ord(nextchr) >= ord('A') and ord(nextchr) <= ord('Z')):
            while True:
                nextchr = self.peekNext()
                if nextchr == '_' or nextchr == "'" or ord(nextchr) > 127 or \
                        (ord(nextchr) >= ord('0') and ord(nextchr) <= ord('9')) or \
                        (ord(nextchr) >= ord('a') and ord(nextchr) <= ord('z')) or \
                        (ord(nextchr) >= ord('A') and ord(nextchr) <= ord('Z')):
                    self.getNext()
                    continue
                return
        raise Exception('not an ident')

    def parseCommand(self):
        """ command: (comment | string | [^\\.] | "." not followed by WS)* "." """
        while True:
            nextchr = self.getborring(['(*', '.', '"'])
            if nextchr == '*':
                self.parseComment(2)
                continue
            if nextchr == '"':
                while self.getborring(['"']) != '"':
                    continue
                continue
            if nextchr != '.':
                continue
            if self.peekNext() in [' ', '\t', '\n']:
                break
        self.type = 'command'

    def parseStringRest(self):
        while self.getborring(['"']) != '"':
            continue
        return True

    def getborring(self, interestings):
        """ Traverse a line until the first interesting character, from interestings,
            a list of characters. When the firt interesting character is found,
            return it and advance to it, as if it were read with getNext. """
        line = self.buf[self.line][self.col:]
        col = len(line)

        for i in map((lambda x: (line.find(x), len(x))), interestings):
            (pos, sz) = i
            if pos < col and pos >= 0:
                col = pos + sz - 1

        if col >= len(line):
            self.col = 0
            self.line += 1
            self.content += line + '\n'
            return '\n'
        else:
            self.col += col+1
            self.content += line[:col+1]
            return line[col]
