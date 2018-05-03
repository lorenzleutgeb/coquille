Coquille
========

Coquille is a vim plugin aiming to bring the interactivity of CoqIDE into your
favorite editor.

This repository contains a port of coquille to neovim, with full asynchronous
support, and to the latest coq version.

Installation
------------

This repository is meant to be used as a [pathogen][1] bundle. If you don't
already use pathogen, I strongly recommend that you start right now.

Installing Coquille is just as simple as doing:

    cd ~/.config/nvim/bundle
    git clone https://framagit.org/tyreunom/coquille.git

Note that by default, coquille ships Vincent Aravantinos [syntax][2] and
[indent][3] scripts for Coq, as well as an ftdetect script. If you already have
those in your neovim config, then just switch to the master branch.

Getting started
---------------

Coquille uses the plugin facility of neovim, so if you run coquille for the
first time, and after each upgrade of the plugin, you will need to run the
`:UpdateRemotePlugins` command for coquille to be fully operational.

Coquille currently supports coq version >=8.6. To check what version of coq
will be run with coquille, you can run `:call CoqVersion()`. The version is
checked at startup and coquille will refuse to run if you do not have the
required version.

To launch Coquille on your Coq file, run `:call CoqLaunch()` which will make the
functions:

- CoqNext()
- CoqToCursor()
- CoqUndo()
- CoqStop()
- CoqCancel()

available to you.

By default Coquille forces no mapping for these commands, however two sets of
mapping are already defined and you can activate them by adding:

    " Maps Coquille commands to CoqIDE default key bindings
    au FileType coq call coquille#CoqideMapping()

or

    " Maps Coquille commands to <F2> (Undo), <F3> (Next), <F4> (ToCursor)
    au FileType coq call coquille#FNMapping()

to your `init.vim`.

Alternatively you can, of course, define your own.

Running query commands
----------------------

You can run an arbitrary query command (that is `Check`, `Print`, etc.) by
calling `:call CoqQuery("MyCommand foo bar baz").` and the result will be
displayed in the Infos panel.

Alternatively, some commands are directly callable. The following functions are
available:

 - CoqCheck()
 - CoqLocate()
 - CoqPrint()
 - CoqQuery()
 - CoqSearch()
 - CoqSearchAbout()

For instance, `:call CoqCheck("3+3")` is the same as
`:call CoqQuery("Check 3+3.")`.

Configuration
-------------

Note that the color of the "lock zone" is hard coded and might not be pretty in
your specific setup (depending on your terminal, colorscheme, etc).
To change it, you can overwrite the `CheckedByCoq` and `SentToCoq` highlight
groups (`:h hi` and `:h highlight-groups`) to colors that works better for you.
See [coquille.vim][4] for an example.

For instance, you can put this in your ~/.config/nvim/init.vim:

```vim
hi default CheckedByCoq ctermbg=10 guibg=LightGreen
hi default SentToCoq ctermbg=12 guibg=LimeGreen
```

You can run `coquille#Commands()` to make some commands available.  By putting
a call in your init.vim, you can make them always available.  As they may
conflict with other coq-related extensions, they are disabled by default.  The
following commands are available:

 - CoqLaunch
 - CoqStop
 - CoqNext
 - CoqCancel
 - CoqToCursor
 - CoqUndo
 - CoqQuery
 - CoqCheck
 - CoqLocate
 - CoqPrint
 - CoqSearch
 - CoqSearchAbout

They work similarly to their functional counterpart, except that their arguments
don't need to be wrapped in quotes.

(TODO)

You can set the following variable to modify Coquille's behavior:

    g:coquille_auto_move            Set it to 'true' if you want Coquille to
        (default = 'false')         move your cursor to the end of the lock zone
                                    after calls to CoqNext or CoqUndo

Screenshoots
------------

Because pictures are always the best sellers:

![Coquille at use](http://the-lambda-church.github.io/coquille/coquille.png)

[1]: https://github.com/tpope/vim-pathogen
[2]: http://www.vim.org/scripts/script.php?script_id=2063 "coq syntax on vim.org"
[3]: http://www.vim.org/scripts/script.php?script_id=2079 "coq indent on vim.org"
[4]: https://github.com/the-lambda-church/coquille/blob/master/autoload/coquille.vim#L103
