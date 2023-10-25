# Overview

Zotcite BetterBibTeX is a Vim plugin that provides integration with Zotero. For a description of its features, see [https://github.com/vpratz/zotcite-betterbibtex](https://github.com/vpratz/zotcite-betterbibtex)

_This documentation is incomplete, but incorporates the most important features_

# Usage
Zotcite can extract and insert into the markdown document (1) annotations that
you have made using Zotero's built-in PDF viewer, (2) notes that you have
attached to a Zotero entry, and (3) annotations inserted in a PDF by an
external PDF viewer.

To extract annotations made with Zotero's built-in PDF viewer, use the Vim
command `:Zannotations key` where `key` is a word with one or more letters of
authors' names or from a reference title. If the PDF has page labels, Zotero
will register them as the page numbers; otherwise, Zotero will consider the
first page of the PDF as page 1 which in most cases will be wrong. You can fix
this by passing an integer number as a second argument to `:Zannotations`. For
example, if page 1 of a book is page 11 of its PDF, you will get the correct
page numbers if you do:

    :Zannotations key -10

By default, the colon separating the year from the page is replaced by ", p.
". If you want to use the colon or any other string as the separator, set the
value of `$ZYearPageSep` in your vimrc (or init.vim). Example:

    let $ZYearPageSep = ':'

To extract notes from Zotero, use the Vim command `:Znote key`

Similarly, to extract annotations (notes and highlighted texts) that were
inserted into a PDF document by an external PDF viewer, use the Vim command
`:Zpdfnote`. The page numbers of the annotations might be wrong, so always
check them after the extraction. You have also to manually add italics and
other rich text formatting and put back hyphens incorrectly removed from the
end of the PDF lines.

To insert citation keys, in Insert mode, type the `@` letter and one or more
letters of either the last name of the first author or the reference title and
press \<c-X\>\<c-O\>. The matching of citation keys is case-insensitive.

In Vim's Normal mode, put the cursor over a citation key and press:

  - <Leader>zo to open the reference's attachment as registered in Zotero's
    database.

  - \<Leader\>zi to see in the status bar the last name of all authors, the
    year, and the title of the reference.

  - \<Leader\>za to see all fields of a reference as stored by Zotcite.

You can also use the command `:Zseek` to see what references have either a
last author's name or title matching the pattern that you are seeking for. The
references displayed in the command line at the bottom of the screen will be
the same that would be in an omni completion menu. Example:

    :Zseek marx

# Suggested workflow

1. Use Zotero's browser connector to download papers in PDF format.
2. Use Better BibTeX to export your bibliography with fixed citation keys (with automatic updating)
3. Use autocomplete (type @ and then \<c-X\>\<c-O\>) to insert citation keys
4. Use exported bibliography with the conversion tool of your choice (e.g. pandoc)

# Customization

## Open attachment in Zotero

If you want <Plug>ZOpenAttachment to open PDF attachments in Zotero (as
opposed to your system's default PDF viewer), put the following in your
|vimrc|:

    let zotcite_open_in_zotero = 1

Note that you'll need to have Zotero configured as the default app for
opening `zotero://` links. On Linux, assuming your Zotero installation
included a `zotero.desktop` file, you can do the following:

 xdg-mime default zotero.desktop x-scheme-handler/zotero


# Troubleshooting
If either the plugin does not work or you want easy access to the values of
some internal variables, do the following command:

    :Zinfo
