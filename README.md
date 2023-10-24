# Zotcite BetterBibTeX

_Zotcite BetterBibTeX_ is a Vim plugin that provides integration with Zotero. You can:

  - Do omni completion of Better BibTeX citation keys from Zotero database in
    Markdown, RMarkdown and Quarto documents.

  - Quickly see on the status bar information on the reference under the cursor.

  - Open the PDF attachment of the reference associated with the citation key
    under the cursor.

  - Extract highlighted text and text notes from PDF attachments of
    references.

  - Extract Zotero notes from Zotero database.

_Zotcite BetterBibTeX_ is being developed and tested on Linux and should work flawlessly on
other Unix systems, such as Mac OS X. It may require additional configuration
on Windows.


## Installation

Requirements:

  - [Zotero](https://www.zotero.org/) >= 5

  - [Better BibTeX for Zotero](https://github.com/retorquere/zotero-better-bibtex) >= 6.7

  - Python 3

  - Python 3 module Neovim:

    `pip install neovim`

  - Python modules PyQt5 and popplerqt5 (only if you are going to extract
    annotations from PDF documents). On Debian based Linux distributions, you
    can install them with the command:

    `sudo apt install python3-pyqt5 python3-poppler-qt5`

Zotcite BetterBibTeX can be installed as any Vim plugin.

The Python module `zotero` does not import the `vim` module. Hence, its code
could easily be adapted to other text editors such as Emacs.

## Usage

The workflow is designed to enable the use of a bibliography created using
Better BibTeX (e.g. using the _Automatic export_ option). It's main purpose
is to offer autocompletion of citation keys and providing information about
the corresponding citations. To do so, it directly queries the corresponding
databases `zotero.sqlite` and `better-bibtex.sqlite` in your Zotero folder,
therfore no further plugins for the communication with Zotero are needed.

Please, read the plugin's
[documentation](doc/zotcite.txt)
for further instructions.

## Acknowledgment
Zotcite BetterBibTex is an adaptation of [Zotcite](https://github.com/jalvesaq/zotcite),
but not affiliated with the original plugin.

Zotcite's Python code was based on the
[citation.vim](https://github.com/rafaqz/citation.vim) project.
