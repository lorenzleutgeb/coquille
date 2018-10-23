function! coquille#ShowPanels()
    " open the Goals & Infos panels before going back to the main window
    let l:winnb = winnr()
    let g:new_coquille = w:coquille_running
    rightbelow vnew
        setlocal buftype=nofile
        setlocal filetype=coq-goals
        setlocal noswapfile
        execute 'file ' . 'Goals ' . g:new_coquille
        let w:coquille_running=g:new_coquille
        let g:new_goal_buf = bufnr("%")
    rightbelow new
        setlocal buftype=nofile
        setlocal filetype=coq-infos
        setlocal noswapfile
        execute 'file ' . 'Infos ' . g:new_coquille
        let w:coquille_running=g:new_coquille
        let g:new_info_buf = bufnr("%")
    execute l:winnb . 'winc w'
    autocmd InsertChange <buffer> call CoqModify()
    autocmd TextChanged <buffer> call CoqModify()
    autocmd TextChangedI <buffer> call CoqModify()
endfunction

function! coquille#Register()
    hi default CheckedByCoq ctermbg=17 guibg=LightGreen
    hi default SentToCoq ctermbg=60 guibg=LimeGreen
    hi link CoqError Error
endfunction

function! coquille#KillSession()
    setlocal ei=InsertEnter
endfunction

function! coquille#FNMapping()
    "" --- Function keys bindings
    "" Works under all tested config.
    map <silent> <F2> :call CoqUndo()<CR>
    map <silent> <F3> :call CoqNext()<CR>
    map <silent> <F4> :call CoqToCursor()<CR>

    imap <silent> <F2> <C-\><C-o>:call CoqUndo()<CR>
    imap <silent> <F3> <C-\><C-o>:call CoqNext()<CR>
    imap <silent> <F4> <C-\><C-o>:call CoqToCursor()<CR>
endfunction

function! coquille#CoqideMapping()
    "" ---  CoqIde key bindings
    "" Unreliable: doesn't work with all terminals, doesn't work through tmux,
    ""  etc.
    map <silent> <C-A-Up>    :call CoqUndo()<CR>
    map <silent> <C-A-Left>  :call CoqToCursor()<CR>
    map <silent> <C-A-Down>  :call CoqNext()<CR>
    map <silent> <C-A-Right> :call CoqToCursor()<CR>

    imap <silent> <C-A-Up>    <C-\><C-o>:call CoqUndo()<CR>
    imap <silent> <C-A-Left>  <C-\><C-o>:call CoqToCursor()<CR>
    imap <silent> <C-A-Down>  <C-\><C-o>:call CoqNext()<CR>
    imap <silent> <C-A-Right> <C-\><C-o>:call CoqToCursor()<CR>
endfunction

if !exists('coquille_auto_move')
  let g:coquille_auto_move="false"
endif

function! coquille#stop()
    if !exists('w:coquille_running')
        let w:coquille_running="false"
    else
        call CoqStop()
    endif
endfunction

autocmd VimLeavePre * call coquille#stop()
autocmd QuitPre * call coquille#stop()
autocmd BufReadPre * call coquille#stop()
