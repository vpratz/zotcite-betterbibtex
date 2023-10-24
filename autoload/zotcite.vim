
function zotcite#warning(wmsg)
    if v:vim_did_enter == 0
        exe 'autocmd VimEnter * call zotcite#warning("' . escape(a:wmsg, '"') . '")'
        return
    endif
    echohl WarningMsg
    echomsg a:wmsg
    echohl None
endfunction

function zotcite#info()
    if exists('g:zotcite_failed')
        call zotcite#warning(g:zotcite_failed)
        return
    endif
    if s:zrunning
        let info = py3eval('ZotCite.Info()')
        echohl Statement
        echo 'Information from the Python module:'
        for key in keys(info)
            echohl Title
            echo '  ' . key . repeat(' ', 18 - len(key))
            echohl None
            echon ': ' .info[key]
        endfor
    endif
    if s:log != [] || (&omnifunc != '' && &omnifunc != 'zotcite#CompleteBib')
        if s:zrunning
            echo " "
            echohl Statement
            echo 'Additional messages:'
            echohl None
        endif
        if &omnifunc != 'zotcite#CompleteBib'
            echo 'There is another omnifunc enabled: ' . &omnifunc
            if &filetype == "rmd"
                if len(glob(expand("%:p:h") . '/*.bib', 0, 1)) > 0
                    echo "There is a .bib file in this directory. Omni completion might not work."
                endif
            endif
        endif
        for line in s:log
            echo line
        endfor
    endif
endfunction

function zotcite#CompleteBib(findstart, base)
    if a:findstart
        let line = getline(".")
        let cpos = getpos(".")
        let idx = cpos[2] -2
        while idx > 0
            if line[idx] =~ '\w'
                let idx -= 1
            elseif idx > 1 && line[idx-1] >= "\xc2" && line[idx-1] <= "\xdf" && line[idx] >= "\x80" && line[idx] <= "\xbf"
                " UTF-8 character (two bytes)
                let idx -= 2
            elseif idx > 2 && line[idx-2] >= "\xe0" && line[idx-2] <= "\xef" && line[idx-1] >= "\x80" && line[idx-1] <= "\xbf" && line[idx] >= "\x80" && line[idx] <= "\xbf"
                " UTF-8 character (three bytes)
                let idx -= 3
            else
                break
            endif
        endwhile
        if line[idx] == '@'
            let s:compl_type = 1
            return idx + 1
        elseif b:non_z_omnifunc != ''
            let s:compl_type = 2
            let Ofun = function(b:non_z_omnifunc)
            return Ofun(a:findstart, a:base)
        else
            let s:compl_type = 3
            return idx + 1
        endif
    else
        if s:compl_type == 2
            let Ofun = function(b:non_z_omnifunc)
            return Ofun(a:findstart, a:base)
        endif
        if s:compl_type == 3
            return []
        endif
        let citeptrn = substitute(a:base, '^@', '', '')
        let resp = []
        let itms = py3eval('ZotCite.GetMatch("'. citeptrn .'", "'. escape(expand("%:p"), '\\') .'")')
        for it in itms
            call add(resp, {'word': it[0], 'abbr': it[1], 'menu': it[2]})
        endfor
        return resp
    endif
endfunction

function zotcite#getmach(key)
    let citeptrn = substitute(a:key, ' .*', '', '')
    let refs = py3eval('ZotCite.GetMatch("'. citeptrn .'", "'. escape(expand("%:p"), '\\') .'")')
    let resp = []
    for ref in refs
        let item = {'key': substitute(ref[0], '#.*', '', ''), 'author': ref[1]}
        if ref[2] =~ '^([0-9][0-9][0-9][0-9]) '
            let item['year'] = substitute(ref[2], '^(\([0-9][0-9][0-9][0-9]\)) .*', '\1', '')
            let item['ttl'] = substitute(ref[2], '^([0-9][0-9][0-9][0-9]) ', '', '')
        elseif ref[2] =~ '^() '
            let item['year'] = ''
            let item['ttl'] = substitute(ref[2], '^() ', '', '')
        else
            let item['year'] = ''
            let item['ttl'] = ref[2]
        endif
        call add(resp, item)
    endfor
    if len(resp) == 0
        echo 'No matches found.'
    endif
    return resp
endfunction

function zotcite#printmatches(mtchs, prefix)
    let idx = 0
    for mt in a:mtchs
        let idx += 1
        let room = &columns - len(mt['year']) - len(mt['author']) - 3
        if a:prefix
            echo idx . ': '
            echohl Identifier
            echon mt['author'] . ' '
            let room = room - len(idx) - 2
        else
            echohl Identifier
            echo mt['author'] . ' '
        endif
        if len(mt['ttl']) > room
            let mt['ttl'] = substitute(mt['ttl'], '^\(.\{'.room.'}\).*', '\1', '')
        endif
        echohl Number
        echon  mt['year'] . ' '
        echohl Title
        echon mt['ttl']
        echohl None
    endfor
endfunction

function zotcite#Seek(key)
    let mtchs = zotcite#getmach(a:key)
    call zotcite#printmatches(mtchs, 0)
endfunction

function zotcite#GetAnnotations(ko)
    let argmt = split(a:ko)
    let zotkey = zotcite#FindCitationKey(argmt[0])
    if zotkey != ''
        let offset = 0
        if len(argmt) == 2
            let offset = str2nr(argmt[1])
        endif
        let repl = py3eval('ZotCite.GetAnnotations("' . zotkey . '", ' . offset . ')')
        if repl == []
            redraw
            call zotcite#warning('No annotation found.')
        else
            call append('.', repl)
        endif
    endif
endfunction

function zotcite#GetNote(key)
    let zotkey = zotcite#FindCitationKey(a:key)
    if zotkey != ''
        let repl = py3eval('ZotCite.GetNotes("' . zotkey . '")')
        if repl == ''
            redraw
            echo 'No note found.'
        else
            call append('.', split(repl, "\n"))
        endif
    endif
endfunction

function zotcite#GetCitationKey()
    let oldisk = &iskeyword
    set iskeyword=@,48-57,_,192-255,@-@,#
    let wrd = expand('<cword>')
    exe 'set iskeyword=' . oldisk
    if wrd =~ '^@'
        let wrd = substitute(wrd, '^@', '', '')
        let wrd = substitute(wrd, '#.*', '', '')
        return wrd
    endif
    return ''
endfunction

function zotcite#GetReferenceData(type)
    let wrd = zotcite#GetCitationKey()
    if wrd != ''
        let repl = py3eval('ZotCite.GetRefData("' . wrd . '")')
        if len(repl) == 0
            call zotcite#warning('Citation key not found')
            return
        endif
        if a:type == 'raw'
            for key in keys(repl)
                echohl Title
                echo key
                echohl None
                if type(repl[key]) == v:t_string
                    echon ': ' . repl[key]
                else
                    echon ': ' . string(repl[key])
                endif
            endfor
        else
            if has_key(repl, 'alastnm')
                echohl Identifier
                echon repl['alastnm'] . ' '
            endif
            echohl Number
            echon repl['year'] . ' '
            if has_key(repl, 'title')
                echohl Title
                echon repl['title']
                echohl None
            endif
        endif
    endif
endfunction

function zotcite#TranslateZPath(strg, zotero_uri = 0)
    let fpath = a:strg

    if a:zotero_uri && a:strg =~? '\.pdf$'
        let id = substitute(fpath, ':.*', '', '')
        return 'zotero://open-pdf/library/items/' . id
    endif

    if a:strg =~ ':attachments:'
	" The user has set Edit / Preferences / Files and Folders / Base directory for linked attachments
	if g:zotcite_attach_dir == ''
	    call zotcite#warning('Attachments dir is not defined')
        else
            let fpath = substitute(a:strg, '.*:attachments:', '/' . g:zotcite_attach_dir . '/', '')
	endif
    elseif a:strg =~ ':/'
	" Absolute file path
	let fpath = substitute(a:strg, '.*:/', '/', '')
    elseif a:strg =~ ':storage:'
	" Default path
	let fpath = g:zotcite_data_dir . substitute(a:strg, '\(.*\):storage:', '/storage/\1/', '')
    endif
    if !filereadable(fpath)
        call zotcite#warning('Could not find "' . fpath . '"')
        let fpath = ''
    endif
    return fpath
endfunction

function zotcite#GetPDFPath(zotkey, zotero_uri = 0)
    let repl = py3eval('ZotCite.GetAttachment("' . a:zotkey . '")')
    if len(repl) == 0
        call zotcite#warning('Got empty list')
        return
    endif
    if repl[0] == 'nOaTtAChMeNt'
        redraw
        call zotcite#warning('Attachment not found')
    elseif repl[0] == 'nOcItEkEy'
        redraw
        call zotcite#warning('Citation key not found')
    else
        if len(repl) == 1
            return zotcite#TranslateZPath(repl[0], a:zotero_uri)
        else
            let idx = 1
            for at in repl
                echohl Number
                echo idx
                echohl None
                echon  '. ' . substitute(zotcite#TranslateZPath(at), '.*storage:', '', '')
                let idx += 1
            endfor
            let idx = input('Your choice: ')
            if idx != '' && idx >= 1 && idx <= len(repl)
                return zotcite#TranslateZPath(repl[idx - 1], a:zotero_uri)
            endif
        endif
    endif
    return ''
endfunction

function zotcite#FindCitationKey(str)
    let mtchs = zotcite#getmach(a:str)
    if len(mtchs) == 0
        return ''
    endif
    call zotcite#printmatches(mtchs, 1)
    let idx = input('Your choice: ')
    if idx == "" || idx <= 0 || idx > len(mtchs)
        return ''
    endif
    return mtchs[idx - 1]['key']
endfunction

function zotcite#OpenAttachment()
    let zotkey = zotcite#GetCitationKey()
    let fpath = zotcite#GetPDFPath(zotkey, g:zotcite_open_in_zotero)
    if fpath != ''
        if g:zotcite_wait_attachment
            let out = system(s:open_cmd . ' "' . fpath . '"')
            if v:shell_error
                call zotcite#warning(substitute(out, '\n', ' ', 'g'))
            endif
        else
            call system(s:open_cmd . ' "' . fpath . '" &')
        endif
    endif
endfunction

function zotcite#GetPDFNote(key)
    let zotkey = zotcite#FindCitationKey(a:key)
    if zotkey == ''
        return
    endif
    redraw
    let fpath = substitute(zotcite#GetPDFPath(zotkey), "'", "'\\\\''", "g")
    if fpath == ''
        return
    endif
    let repl = py3eval('ZotCite.GetRefData("' . zotkey . '")')
    let citekey = " '@" . zotkey . '#' . repl['citekey'] . "' "
    let pg = 1
    if has_key(repl, 'pages') && repl['pages'] =~ '[0-9]-'
        let pg = repl['pages']
    endif
    let notes = system("pdfnotes.py '" . fpath . "'" . citekey . pg)
    if v:shell_error == 0
        call append(line('.'), split(notes, '\n'))
    else
        redraw
        if v:shell_error == 33
            call zotcite#warning('Failed to load "' . fpath . '" as a valid PDF document.')
        elseif v:shell_error == 34
            call zotcite#warning("No annotations found.")
        else
            call zotcite#warning(notes)
        endif
    endif
endfunction

if has('nvim')
    function s:OnJobEvent(job_id, data, event)
        if a:event == 'stdout' || a:event == 'stderr'
            let s:quarto_output += a:data
        else
            let s:quarto_running = 0
            if a:data != 0
                call writefile(s:quarto_output, $Zotcite_tmpdir . '/joboutput')
                tabnew
                exe "terminal cat '" . $Zotcite_tmpdir . "/joboutput' && rm '" . $Zotcite_tmpdir . "/joboutput'"
            endif
        endif
    endfunction
else
    function s:OnJobEvent(job_id, msg)
        let s:quarto_output += [a:msg]
    endfunction
    function s:OnJobExit(job_id, stts)
        let s:quarto_running = 0
        if a:stts != 0
            call writefile(s:quarto_output, $Zotcite_tmpdir . '/joboutput')
            exe "terminal cat " . $Zotcite_tmpdir . "/joboutput && rm " . $Zotcite_tmpdir . "/joboutput"
        endif
    endfunction
endif

if has('nvim')
    let s:jobcb = {'on_stdout': function('s:OnJobEvent'),
                \ 'on_stderr': function('s:OnJobEvent'),
                \ 'on_exit': function('s:OnJobEvent')}
else
    let s:jobcb = {'out_cb': function('s:OnJobEvent'),
                \ 'err_cb': function('s:OnJobEvent'),
                \ 'exit_cb': function('s:OnJobExit')}
endif
let s:quarto_running = 0

let s:systole = v:false
function zotcite#Pulse(...)
    if s:quarto_running
        if s:systole
            echon "\r-"
        else
            echon "\r+"
        endif
        let s:systole = !s:systole
        call timer_start(500, 'zotcite#Pulse')
    else
        echon "\r "
    endif
endfunction

function zotcite#SetPath()
    if has("win32")
        let zpath = substitute(s:zotcite_home, '/', '\\', 'g')
        if stridx($PATH, zpath) == -1
            let $PATH = zpath . ';' . $PATH
        endif
    else
        if $PATH !~ s:zotcite_home
            let $PATH = s:zotcite_home . ':' . $PATH
        endif
    endif
endfunction

function zotcite#GlobalInit()
    if !has('python3')
        let g:zotcite_failed = 'zotcite requires python3'
        call zotcite#warning(g:zotcite_failed)
        return 0
    endif

    py3 import os

    " Start ZoteroEntries
    py3 from zotero import ZoteroEntries
    py3 ZotCite = ZoteroEntries()

    " Get information from ZoteroEntries and set environment variables for citeref
    try
        let info = py3eval('ZotCite.Info()')
    catch /*/
        let g:zotcite_failed = 'Failed to create ZoteroEntries object.'
        call zotcite#warning(g:zotcite_failed)
        let s:zrunning = 0
        return 0
    endtry
    let s:zrunning = 1

    let $Zotcite_tmpdir = expand(info['tmpdir'])
    let g:zotcite_data_dir = expand(info['data dir'])
    let g:zotcite_attach_dir = expand(info['attachments dir'])
    let g:zotcite_wait_attachment = get(g:, 'zotcite_wait_attachment', 0)
    let g:zotcite_open_in_zotero = get(g:, 'zotcite_open_in_zotero', 0)

    call zotcite#SetPath()
    let $RmdFile = expand("%:p")

    if filereadable($Zotcite_tmpdir . "/uname")
        let s:uname = readfile($Zotcite_tmpdir . "/uname")[0]
    else
        silent let s:uname = system("uname")
        call writefile([s:uname], $Zotcite_tmpdir . "/uname")
    endif

    if has('win32') || s:uname =~ "Darwin"
        let s:open_cmd = 'open'
    else
        let s:open_cmd = 'xdg-open'
    endif
    unlet s:uname

    command -nargs=1 Zseek call zotcite#Seek(<q-args>)
    command -nargs=1 Znote call zotcite#GetNote(<q-args>)
    command -nargs=+ Zannotations call zotcite#GetAnnotations(<q-args>)
    command -nargs=1 Zpdfnote call zotcite#GetPDFNote(<q-args>)
    return 1
endfunction

function zotcite#Init(...)
    let ok = 0
    for ft in g:zotcite_filetypes
        if &filetype == ft
            let ok = 1
            break
        endif
    endfor

    if ok == 0
        return
    endif

    " Do this only once
    if !exists('s:open_cmd')
        if zotcite#GlobalInit() == 0
            return
        endif
    endif

    " And repeat this for every buffer
    if !exists('b:zotref_did_buffer_cmds')
        let b:zotref_did_buffer_cmds = 1
        if hasmapto('<Plug>ZOpenAttachment', 'n')
            exec 'nnoremap <buffer><silent> <Plug>ZOpenAttachment :call zotcite#OpenAttachment()<cr>'
        else
            nnoremap <buffer><silent> <Leader>zo :call zotcite#OpenAttachment()<cr>
        endif
        if hasmapto('<Plug>ZCitationInfo', 'n')
            exec 'nnoremap <buffer><silent> <Plug>ZCitationInfo :call zotcite#GetReferenceData("ayt")<cr>'
        else
            nnoremap <buffer><silent> <Leader>zi :call zotcite#GetReferenceData("ayt")<cr>
        endif
        if hasmapto('<Plug>ZCitationCompleteInfo', 'n')
            exec 'nnoremap <buffer><silent> <Plug>ZCitationCompleteInfo :call zotcite#GetReferenceData("raw")<cr>'
        else
            nnoremap <buffer><silent> <Leader>za :call zotcite#GetReferenceData("raw")<cr>
        endif
        if exists('g:zotcite_conceallevel')
            exe 'set conceallevel=' . g:zotcite_conceallevel
        else
            set conceallevel=2
        endif
        if &omnifunc != 'zotcite#CompleteBib' && &omnifunc != 'RmdNonRCompletion'&& &omnifunc != 'CompleteR'
            let b:non_z_omnifunc = &omnifunc
        elseif exists('*pandoc#completion#Complete')
            let b:non_z_omnifunc = 'pandoc#completion#Complete'
        elseif exists('*htmlcomplete#CompleteTags')
            let b:non_z_omnifunc = 'htmlcomplete#CompleteTags'
        else
            let b:non_z_omnifunc = ''
        endif
        " Let Nvim-R control the omni completion (it will call zotcite#CompleteBib).
        if !exists('b:rplugin_non_r_omnifunc')
            setlocal omnifunc=zotcite#CompleteBib
        endif
    endif
endfunction

let s:zotcite_home = expand('<sfile>:h:h') . '/python3'
let s:log = []
let s:zrunning = 0
