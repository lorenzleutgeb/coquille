class ProjectParser():
    def __init__(self, filename):
        self.R = [('.', '')]
        self.coqtop = 'coqtop'

        if filename == None:
            return

        lines = []
        with open(filename) as f:
            line = f.readline()
            while line:
                if (len(line.strip()) != 0) and (not line.strip()[0] == '#'):
                    lines.append(line.strip())
                line = f.readline()
        variables = {}
        for line in lines:
            sline = line.split()
            if len(sline) < 1:
                continue
            if len(sline) < 3:
                continue
            if sline[0] == '-R':
                self.R.append((sline[1].strip("\"'"), sline[2].strip("\"'")))
            if sline[1] == "=":
                variables[sline[0]] = ' '.join(sline[2:]).strip('"\'')

        if 'COQBIN' in variables:
            self.coqtop = variables['COQBIN'] + '/coqtop'

    def getR(self):
        return self.R

    def getCoqtop(self):
        return self.coqtop
