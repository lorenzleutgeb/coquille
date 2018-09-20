function! coquille#ShowPanels()
    " open the Goals & Infos panels before going back to the main window
    let l:winnb = winnr()
    rightbelow vnew Goals
        setlocal buftype=nofile
        setlocal filetype=coq-goals
        setlocal noswapfile
        let s:goal_buf = bufnr("%")
    rightbelow new Infos
        setlocal buftype=nofile
        setlocal filetype=coq-infos
        setlocal noswapfile
        let s:info_buf = bufnr("%")
    execute l:winnb . 'winc w'
endfunction

function! coquille#Register()
    hi default CheckedByCoq ctermbg=17 guibg=LightGreen
    hi default SentToCoq ctermbg=60 guibg=LimeGreen
    hi link CoqError Error

    let t:checked = -1
    let t:sent    = -1
    let t:errors  = -1
endfunction

function! coquille#KillSession()
    execute 'bdelete' . s:goal_buf
    execute 'bdelete' . s:info_buf

    setlocal ei=InsertEnter
endfunction

function! coquille#FNMapping()
    "" --- Function keys bindings
    "" Works under all tested config.
    map <buffer> <silent> <F2> :call CoqUndo()<CR>
    map <buffer> <silent> <F3> :call CoqNext()<CR>
    map <buffer> <silent> <F4> :call CoqToCursor()<CR>

    imap <buffer> <silent> <F2> <C-\><C-o>:call CoqUndo()<CR>
    imap <buffer> <silent> <F3> <C-\><C-o>:call CoqNext()<CR>
    imap <buffer> <silent> <F4> <C-\><C-o>:call CoqToCursor()<CR>
endfunction

function! coquille#CoqideMapping()
    "" ---  CoqIde key bindings
    "" Unreliable: doesn't work with all terminals, doesn't work through tmux,
    ""  etc.
    map <buffer> <silent> <C-A-Up>    :call CoqUndo()<CR>
    map <buffer> <silent> <C-A-Left>  :call CoqToCursor()<CR>
    map <buffer> <silent> <C-A-Down>  :call CoqNext()<CR>
    map <buffer> <silent> <C-A-Right> :call CoqToCursor()<CR>

    imap <buffer> <silent> <C-A-Up>    <C-\><C-o>:call CoqUndo()<CR>
    imap <buffer> <silent> <C-A-Left>  <C-\><C-o>:call CoqToCursor()<CR>
    imap <buffer> <silent> <C-A-Down>  <C-\><C-o>:call CoqNext()<CR>
    imap <buffer> <silent> <C-A-Right> <C-\><C-o>:call CoqToCursor()<CR>
endfunction

function! coquille#Commands()
    command CoqLaunch call CoqLaunch()
    command CoqNext call CoqNext()
    command CoqUndo call CoqUndo()
    command CoqToCursor call CoqToCursor()
    command CoqStop call CoqStop()
    command CoqCancel call CoqCancel()
    command CoqDebug call CoqDebug()
    command -nargs=1 CoqQuery call CoqQuery(<f-args>)
    command -nargs=1 CoqCheck call CoqCheck(<f-args>)
    command -nargs=1 CoqLocate call CoqLocate(<f-args>)
    command -nargs=1 CoqPrint call CoqPrint(<f-args>)
    command -nargs=1 CoqSearch call CoqSearch(<f-args>)
    command -nargs=1 CoqSearchAbout call CoqSearchAbout(<f-args>)
endfunction

if !exists('coquille_auto_move')
  let g:coquille_auto_move="false"
endif

function! coquille#stop()
    if !exists('coquille_running')
        let w:coquille_running="false"
    else
        call CoqStop()
    endif
endfunction

autocmd VimLeavePre * call CoqStop()
autocmd BufReadPre * call coquille#stop()
autocmd InsertChange * call CoqModify()
autocmd TextChanged * call CoqModify()
autocmd TextChangedI * call CoqModify()
