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

    let b:checked = -1
    let b:sent    = -1
    let b:errors  = -1
endfunction

function! coquille#KillSession()
    execute 'bdelete' . s:goal_buf
    execute 'bdelete' . s:info_buf

    setlocal ei=InsertEnter
endfunction

autocmd VimLeavePre * call CoqStop()
autocmd InsertChange * call CoqModify()
autocmd TextChanged * call CoqModify()
autocmd TextChangedI * call CoqModify()
