from .parser import Parser

fakebuffer = [
"Ltac name_goal name :=  (* test. *) refine ?[name].",
"(* A simple test :) *)",
"Goal forall n, n + 0 = n.",
"Proof.",
"induction n; [ name_goal base | name_goal step ].",
"  [   step",
" ]",
" : ",
" { simpl. f_equal. auto. }"
        ]

def test_parser():
    p = Parser(fakebuffer)
    assert p.getUnit(0,0) == [0, len(fakebuffer[0]), fakebuffer[0], 'command']
    assert p.getUnit(1,0) == [1, len(fakebuffer[1]), fakebuffer[1], 'comment']
    assert p.getUnit(2,0) == [2, len(fakebuffer[2]), fakebuffer[2], 'command']
    assert p.getUnit(3,0) == [3, 6, fakebuffer[3], 'command']
    assert p.getUnit(4,0) == [4, len(fakebuffer[4]), fakebuffer[4], 'command']
    assert p.getUnit(5,0) == [8, 2, fakebuffer[5] + "\n" + fakebuffer[6] + "\n" + \
            fakebuffer[7] + "\n {", 'bullet']
    assert p.getUnit(8, 2) == [8, 9, " simpl.", 'command']

def test_bullet():
    assert_bullet('-')
    assert_bullet('+')
    assert_bullet('*')
    assert_bullet('+++')
    assert_bullet('--')
    assert_bullet('{')
    print("--------------------")
    assert_bullet('3: {')
    assert_bullet('[step]: {')
    assert_bullet('[\nstep\n]\n:\n \n{')

def assert_bullet(bullet):
    p = Parser([bullet + " a."])
    assert p.getUnit(0,0) == [0,len(bullet), bullet, 'bullet']

def assert_command(cmd):
    p = Parser([cmd + " a."])
    assert p.getUnit(0,0) == [0,len(cmd), cmd, 'command']

def test_command():
    assert_command("Variable (ex: Execution).")
    assert_command("unfold test in *.")

def test_str():
    assert_command("Definition a := \"abc. def. \".")
