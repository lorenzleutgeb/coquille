function! coquille#ShowPanels()
    " open the Goals & Infos panels before going back to the main window
    let l:winnb = winnr()
    let g:new_coquille = w:coquille_running
    rightbelow vnew Goals
        setlocal buftype=nofile
        setlocal filetype=coq-goals
        setlocal noswapfile
        let w:coquille_running=g:new_coquille
        let g:new_goal_buf = bufnr("%")
    rightbelow new Infos
        setlocal buftype=nofile
        setlocal filetype=coq-infos
        setlocal noswapfile
        let w:coquille_running=g:new_coquille
        let g:new_info_buf = bufnr("%")
    execute l:winnb . 'winc w'
    let w:info_buf = g:new_info_buf
    let w:goal_buf = g:new_goal_buf
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
    execute 'bdelete' . w:goal_buf
    execute 'bdelete' . w:info_buf

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
