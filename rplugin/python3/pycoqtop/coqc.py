import shlex
import subprocess
from pathlib import Path

def coqc(coqfile, coqcargs, vim):
    #vim.async_call(vim.command, 'echo "building {}..."'.format(coqfile))
    vim.command('echo "building {}..."'.format(coqfile))
    args = coqcargs
    args.append(coqfile)
    return subprocess.call(args)

def coqbuild(coqfile, vim, coqcbin, coqdepbin, args):
    todo = computedeps(coqfile, [coqdepbin]+args)
    todo = pickgreendeps(greenify(todo))

    for ff in todo:
        coqc(ff, [coqcbin]+args, vim)
    vim.command('echo "done!"')

def computedeps(coqfile, coqdepargs):
    assert coqfile[-1] == 'v'

    args = coqdepargs
    args.append(coqfile)
    dep=subprocess.check_output(args).decode('utf-8')

    alldeps = dep.split('\n')
    fdeps = []
    for dep in alldeps:
        deps = dep.split(':')
        if len(deps) == 2:
            deps[0] = shlex.split(deps[0])
            deps[1] = shlex.split(deps[1])
            fdeps.append(deps)
    
    vmtime = Path(coqfile).stat().st_mtime
    vomtime = Path(coqfile+'o').stat().st_mtime
    todo = {'green': vomtime < vmtime, 'file': coqfile, 'deps': []}

    for deps in fdeps:
        for f in deps[0]:
            if f == coqfile+'o':
                for ff in deps[1]:
                    if ff.endswith('vo'):
                        todo['deps'].append(computedeps(ff[:-1], coqdepargs))
                break

    return todo

def greenify(tree):
    tree['deps'] = [greenify(branch) for branch in tree['deps']]
    green = tree['green']
    for branch in tree['deps']:
        green = green or branch['green']
    tree['green'] = green
    return tree

def pickgreendeps(tree):
    deps = []
    if tree['green']:
        for dep in tree['deps']:
            required = pickgreendeps(dep)
            for r in required:
                if not r in deps:
                    deps.append(r)
        deps.append(tree['file'])
    return deps
