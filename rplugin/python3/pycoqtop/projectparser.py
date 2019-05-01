import os
import subprocess

class Version:
    def __init__(self, version):
        self.currentVersion = version

    def is86(self):
        return self.currentVersion[0] == '8' and self.currentVersion[1] == '6'

    def isatleast89(self):
        return self.currentVersion[0] == '8' and self.currentVersion[1] >= '9'

    def is_allowed(self):
        return (self.currentVersion[0] == '8') and (int(self.currentVersion[1]) >= 6)

    def __str__(self):
        return '.'.join(self.currentVersion)

class ProjectParser():
    def __init__(self, filename):
        self.R = []
        self.Q = []
        self.I = []
        self.coqtop = 'coqtop'
        self.variables = {}

        if filename == None:
            self.R = [('.', '')]
            return

        lines = []
        with open(filename) as f:
            line = f.readline()
            while line:
                if (len(line.strip()) != 0) and (not line.strip()[0] == '#'):
                    lines.append(line.strip())
                line = f.readline()
        for line in lines:
            sline = line.split()
            self.parseLine(sline)

        if 'COQBIN' in self.variables:
            self.coqtop = self.variables['COQBIN'] + '/coqtop'

        try:
            self.version()
        except:
            pass

    def parseLine(self, sline):
        if len(sline) < 2:
            return
        if sline[0] == '-R':
            self.R.append((sline[1].strip("\"'"), sline[2].strip("\"'")))
            self.parseLine(sline[3:])
        if sline[0] == '-Q':
            self.Q.append((sline[1].strip("\"'"), sline[2].strip("\"'")))
            self.parseLine(sline[3:])
        if sline[0] == '-I':
            self.I.append(sline[1].strip("\"'"))
            self.parseLine(sline[2:])
        if sline[1] == "=":
            self.variables[sline[0]] = ' '.join(sline[2:]).strip('"\'')

    def getI(self):
        return self.I

    def getQ(self):
        return self.Q

    def getR(self):
        return self.R

    def getCoqtop(self):
        return self.coqtop

    def version(self):
        options = [self.coqtop, '--print-version']
        if os.name == 'nt':
            coqtop = subprocess.Popen(options,
                stdin = subprocess.PIPE, stdout = subprocess.PIPE,
                stderr = subprocess.STDOUT)
        else:
            coqtop = subprocess.Popen(options,
                stdin = subprocess.PIPE, stdout = subprocess.PIPE)
        fd = coqtop.stdout.fileno()
        data = os.read(fd, 0x4000).decode("utf-8")
        version = data.split(' ')[0]
        version = Version(version.split('.'))
        if version.isatleast89():
            self.coqtop = 'coqidetop'
            if 'COQBIN' in self.variables:
                self.coqtop = self.variables['COQBIN'] + '/coqidetop'
        return version
