""" Class ZoteroEntries """
import sys
import os
import re
import sqlite3
import subprocess

# A lot of code was either adapted or plainly copied from citation_vim,
# written by Rafael Schouten: https://github.com/rafaqz/citation.vim
# Code and/or ideas were also adapted from zotxt, pypandoc, and pandocfilters.

# To debug this code, create a /tmp/test.md file and do:
# pandoc testzotcite.md -t json | /full/path/to/zotcite/python3/zotref


class ZoteroEntries:
    """Create an object storing all references from ~/Zotero/zotero.sqlite"""

    _creators = [
        "editor",
        "seriesEditor",
        "translator",
        "reviewedAuthor",
        "artist",
        "performer",
        "composer",
        "director",
        "podcaster",
        "cartographer",
        "programmer",
        "presenter",
        "interviewee",
        "interviewer",
        "recipient",
        "sponsor",
        "inventor",
    ]

    def __init__(self):
        # Year-page separator
        if os.getenv("ZYearPageSep") is not None:
            self._ypsep = str(os.getenv("ZYearPageSep"))
        else:
            self._ypsep = ", p. "

        # Path to zotero.sqlite
        self._get_zotero_prefs()
        if os.getenv("ZoteroSQLpath") is None:
            if os.path.isfile(os.path.expanduser("~/Zotero/zotero.sqlite")):
                self._z = os.path.expanduser("~/Zotero/zotero.sqlite")
            elif os.getenv("USERPROFILE") is not None and os.path.isfile(
                str(os.getenv("USERPROFILE")) + "/Zotero/zotero.sqlite"
            ):
                self._z = str(os.getenv("USERPROFILE")) + "/Zotero/zotero.sqlite"
            else:
                self._errmsg(
                    "The file zotero.sqlite was not found. Please, define the environment variable ZoteroSQLpath."
                )
                return None
        else:
            if os.path.isfile(os.path.expanduser(str(os.getenv("ZoteroSQLpath")))):
                self._z = os.path.expanduser(str(os.getenv("ZoteroSQLpath")))
            else:
                self._errmsg(
                    'Please, check if $ZoteroSQLpath is correct: "'
                    + str(os.getenv("ZoteroSQLpath"))
                    + '" not found.'
                )
                return None

        # Path to better-bibtex-search.sqlite
        if os.getenv("BetterBibtexSQLpath") is None:
            if os.path.isfile(os.path.expanduser("~/Zotero/better-bibtex.sqlite")):
                self._b = os.path.expanduser("~/Zotero/better-bibtex.sqlite")
            elif os.getenv("USERPROFILE") is not None and os.path.isfile(
                str(os.getenv("USERPROFILE")) + "/Zotero/better-bibtex.sqlite"
            ):
                self._b = str(os.getenv("USERPROFILE")) + "/Zotero/better-bibtex.sqlite"
            else:
                self._errmsg(
                    "The file better-bibtex.sqlite was not found. Please, define the environment variable BetterBibtexSQLpath."
                )
                return None
        else:
            if os.path.isfile(
                os.path.expanduser(str(os.getenv("BetterBibtexSQLpath")))
            ):
                self._b = os.path.expanduser(str(os.getenv("BetterBibtexSQLpath")))
            else:
                self._errmsg(
                    'Please, check if $BetterBibtexSQLpath is correct: "'
                    + str(os.getenv("BetterBibtexSQLpath"))
                    + '" not found.'
                )
                return None

        # Temporary directory
        if os.getenv("Zotcite_tmpdir") is None:
            if os.getenv("XDG_CACHE_HOME") and os.path.isdir(
                str(os.getenv("XDG_CACHE_HOME"))
            ):
                self._tmpdir = str(os.getenv("XDG_CACHE_HOME")) + "/zotcite"
            elif os.getenv("APPDATA") and os.path.isdir(str(os.getenv("APPDATA"))):
                self._tmpdir = str(os.getenv("APPDATA")) + "/zotcite"
            elif os.path.isdir(os.path.expanduser("~/.cache")):
                self._tmpdir = os.path.expanduser("~/.cache/zotcite")
            elif os.path.isdir(os.path.expanduser("~/Library/Caches")):
                self._tmpdir = os.path.expanduser("~/Library/Caches/zotcite")
            else:
                self._tmpdir = "/tmp/.zotcite"
        else:
            self._tmpdir = os.path.expanduser(str(os.getenv("Zotcite_tmpdir")))
        if not os.path.isdir(self._tmpdir):
            try:
                os.mkdir(self._tmpdir)
            except:
                self._exception()
                return None
        if not os.access(self._tmpdir, os.W_OK):
            self._errmsg(
                'Please, either set or fix the value of $Zotcite_tmpdir: "'
                + self._tmpdir
                + '" is not writable.'
            )
            return None

        self._c = {}
        self._e = {}
        self._load_zotero_data()

        # List of collections for each markdown document
        self._d = {}

    def SetCollections(self, d, clist):
        """Define which Zotero collections each markdown document uses

        d   (string): The name of the markdown document
        clist (list): A list of collections to be searched for citation keys
                      when seeking references for the document 'd'.
        """

        self._d[d] = []
        if clist != [""]:
            for c in clist:
                if c in self._c:
                    self._d[d].append(c)
                else:
                    return 'Collection "' + c + '" not found in Zotero database.'
        return ""

    def _get_zotero_prefs(self):
        self._dd = ""
        self._ad = ""
        zp = None
        if os.path.isfile(os.path.expanduser("~/.zotero/zotero/profiles.ini")):
            zp = os.path.expanduser("~/.zotero/zotero/profiles.ini")
        else:
            if os.path.isfile(
                os.path.expanduser("~/Library/Application Support/Zotero/profiles.ini")
            ):
                zp = os.path.expanduser(
                    "~/Library/Application Support/Zotero/profiles.ini"
                )

        if zp:
            zotero_basedir = os.path.dirname(zp)
            with open(zp, "r") as f:
                lines = f.readlines()
            for line in lines:
                if line.find("Path=") == 0:
                    zprofile = line.replace("Path=", "").replace("\n", "")
                    zprefs = os.path.join(zotero_basedir, zprofile, "prefs.js")
                    if os.path.isfile(zprefs):
                        with open(zprefs, "r") as f:
                            prefs = f.readlines()
                        for pref in prefs:
                            if pref.find("extensions.zotero.baseAttachmentPath") > 0:
                                self._ad = re.sub('.*", "(.*)".*\n', "\\1", pref)
                            if (
                                os.getenv("ZoteroSQLpath") is None
                                and pref.find("extensions.zotero.dataDir") > 0
                            ):
                                self._dd = re.sub('.*", "(.*)".*\n', "\\1", pref)
                                if os.path.isfile(self._dd + "/zotero.sqlite"):
                                    os.environ["ZoteroSQLpath"] = (
                                        self._dd + "/zotero.sqlite"
                                    )
        # Workaround for Windows:
        if self._dd == "" and os.getenv("ZoteroSQLpath"):
            self._dd = os.path.dirname(os.environ["ZoteroSQLpath"])
        if self._dd == "" and os.path.isdir(os.path.expanduser("~/Zotero")):
            self._dd = os.path.expanduser("~/Zotero")

    def _copy_zotero_data(self):
        self._ztime = os.path.getmtime(self._z)
        zcopy = self._tmpdir + "/copy_of_zotero.sqlite"
        if os.path.isfile(zcopy):
            zcopy_time = os.path.getmtime(zcopy)
        else:
            zcopy_time = 0

        # Make a copy of zotero.sqlite to avoid locks
        if self._ztime > zcopy_time:
            with open(self._z, "rb") as f:
                b = f.read()
            with open(zcopy, "wb") as f:
                f.write(b)
        return zcopy

    def _copy_betterbibtex_data(self):
        self._btime = os.path.getmtime(self._b)
        bcopy = self._tmpdir + "/copy_of_better_bibtex.sqlite"
        if os.path.isfile(bcopy):
            bcopy_time = os.path.getmtime(bcopy)
        else:
            bcopy_time = 0

        # Make a copy of zotero.sqlite to avoid locks
        if self._btime > bcopy_time:
            with open(self._b, "rb") as f:
                b = f.read()
            with open(bcopy, "wb") as f:
                f.write(b)
        return bcopy

    def _load_zotero_data(self):
        # setup the database
        zcopy = self._copy_zotero_data()
        bcopy = self._copy_betterbibtex_data()
        conn = sqlite3.connect(zcopy)
        self._cur = conn.cursor()
        # attach BetterBibTeX database to Zotero database
        bbt_query = f'ATTACH DATABASE "{bcopy}" as betterbibtex'
        self._cur.execute(bbt_query)

        self._get_collections()
        self._add_most_fields()
        self._add_authors()
        self._add_type()
        self._add_attachments()
        self._add_year()
        self._delete_items()
        conn.close()

    def _get_collections(self):
        self._c = {}
        query = """
            SELECT collections.collectionName
            FROM collections
            """
        self._cur.execute(query)
        for (c,) in self._cur.fetchall():
            self._c[c] = []
        query = """
            SELECT items.itemID, collections.collectionName
            FROM items, collections, collectionItems
            WHERE
                items.itemID = collectionItems.itemID
                and collections.collectionID = collectionItems.collectionID
            ORDER by collections.collectionName != "To Read",
                collections.collectionName
            """
        self._cur.execute(query)
        for item_id, item_collection in self._cur.fetchall():
            self._c[item_collection].append(item_id)

    def _add_most_fields(self):
        query = """
            SELECT items.itemID, items.key, fields.fieldName, itemDataValues.value, betterbibtex.citationkey.citationKey
            FROM items, itemData, fields, itemDataValues, betterbibtex.citationkey
            WHERE
                items.itemID = itemData.itemID
                and itemData.fieldID = fields.fieldID
                and itemData.valueID = itemDataValues.valueID
                and betterbibtex.citationkey.itemKey = items.key
            """
        self._e = {}
        self._cur.execute(query)
        for item_id, item_key, field, value, citekey in self._cur.fetchall():
            if item_id not in self._e:
                self._e[item_id] = {
                    "zotkey": item_key,
                    "alastnm": "",
                    "citekey": citekey,
                }
            self._e[item_id][field] = value

        for k in self._e:
            if "title" not in self._e[k]:
                self._e[k]["title"] = ""

    def _add_authors(self):
        query = """
            SELECT items.itemID, creatorTypes.creatorType, creators.lastName, creators.firstName
            FROM items, itemCreators, creators, creatorTypes
            WHERE
                items.itemID = itemCreators.itemID
                and itemCreators.creatorID = creators.creatorID
                and creators.creatorID = creators.creatorID
                and itemCreators.creatorTypeID = creatorTypes.creatorTypeID
            ORDER by itemCreators.ORDERIndex
            """
        self._cur.execute(query)
        for item_id, ctype, lastname, firstname in self._cur.fetchall():
            if item_id in self._e:
                if ctype in self._e[item_id]:
                    self._e[item_id][ctype] += [[lastname, firstname]]
                else:
                    self._e[item_id][ctype] = [[lastname, firstname]]
                # Special field for citation seeking
                if ctype == "author":
                    self._e[item_id]["alastnm"] += ", " + lastname
                else:
                    sought = ["author"]
                    for c in self._creators:
                        if ctype == c:
                            flag = False
                            for s in sought:
                                if s in self._e[item_id]:
                                    flag = True
                                    break
                            if not flag:
                                self._e[item_id]["alastnm"] += ", " + lastname
                        sought.append(c)

    def _add_type(self):
        query = """
            SELECT items.itemID, itemTypes.typeName
            FROM items, itemTypes
            WHERE
                items.itemTypeID = itemTypes.itemTypeID
            """
        self._cur.execute(query)
        for item_id, item_type in self._cur.fetchall():
            if item_id in self._e:
                if item_type == "attachment":
                    del self._e[item_id]
                else:
                    self._e[item_id]["etype"] = item_type

    def _add_attachments(self):
        query = """
            SELECT items.key, itemAttachments.parentItemID, itemAttachments.path
            FROM items, itemAttachments
            WHERE items.itemID = itemAttachments.itemID
            """
        self._cur.execute(query)
        for pKey, pId, aPath in self._cur.fetchall():
            if pId in self._e and not pKey is None and not aPath is None:
                if "attachment" in self._e[pId]:
                    self._e[pId]["attachment"].append(pKey + ":" + aPath)
                else:
                    self._e[pId]["attachment"] = [pKey + ":" + aPath]

    def _add_year(self):
        for k in self._e:
            if "date" in self._e[k]:
                year = re.sub(" .*", "", self._e[k]["date"]).split("-")[0]
            else:
                if "issueDate" in self._e[k]:
                    year = re.sub(" .*", "", self._e[k]["issueDate"]).split("-")[0]
                else:
                    year = ""
            self._e[k]["year"] = year

    def _delete_items(self):
        self._cur.execute("SELECT itemID FROM deletedItems")
        for (item_id,) in self._cur.fetchall():
            if item_id in self._e:
                del self._e[item_id]
            for c in self._c:
                if item_id in self._c[c]:
                    self._c[c].remove(item_id)

        for k in self._e:
            self._e[k]["alastnm"] = re.sub("^, ", "", self._e[k]["alastnm"])

    @classmethod
    def _errmsg(cls, msg):
        sys.stderr.write(msg + "\n")
        sys.stderr.flush()

    def _exception(self):
        import traceback

        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        self._errmsg("Zotcite error: " + "".join(line for line in lines))

    # @classmethod
    def _get_compl_line(self, e):
        alastnm = e["alastnm"]
        key = e["citekey"]
        if alastnm == "":
            lst = [key, "", "(" + e["year"] + ") " + e["title"]]
        else:
            if len(alastnm) > 40:
                alastnm = alastnm[:40] + "…"
            lst = [key, alastnm, "(" + e["year"] + ") " + e["title"]]
        return lst

    @staticmethod
    def _sanitize_markdown(s):
        s = s.replace("[", "\\[")
        s = s.replace("]", "\\]")
        s = s.replace("@", "\\@")
        s = s.replace("*", "\\*")
        s = s.replace("_", "\\_")
        return s

    def GetMatch(self, ptrn, d):
        """Find citation key and save completion lines in temporary file

        ptrn (string): The pattern to search for, converted to lower case.
        d    (string): The name of the markdown document.
        """
        if os.path.getmtime(self._z) > self._ztime:
            self._load_zotero_data()

        if d in self._d and self._d[d]:
            collections = self._d[d]
            keys = []
            for c in collections:
                if c in self._c:
                    keys += self._c[c]
            if keys == []:
                keys = self._e.keys()
        else:
            keys = self._e.keys()

        # priority level
        p1 = []
        p2 = []
        p3 = []
        p4 = []
        p5 = []
        p6 = []
        ptrn = ptrn.lower()
        for k in keys:
            if self._e[k]["citekey"].lower().find(ptrn) == 0:
                p1.append(self._get_compl_line(self._e[k]))
            elif (
                self._e[k]["alastnm"]
                and self._e[k]["alastnm"][0][0].lower().find(ptrn) == 0
            ):
                p2.append(self._get_compl_line(self._e[k]))
            elif self._e[k]["title"].lower().find(ptrn) == 0:
                p3.append(self._get_compl_line(self._e[k]))
            elif self._e[k]["citekey"].lower().find(ptrn) > 0:
                p4.append(self._get_compl_line(self._e[k]))
            elif (
                self._e[k]["alastnm"]
                and self._e[k]["alastnm"][0][0].lower().find(ptrn) > 0
            ):
                p5.append(self._get_compl_line(self._e[k]))
            elif self._e[k]["title"].lower().find(ptrn) > 0:
                p6.append(self._get_compl_line(self._e[k]))
        resp = p1 + p2 + p3 + p4 + p5 + p6
        return resp

    def GetAttachment(self, zotkey):
        """Tell Vim what attachment is associated with the citation key

        zotkey  (string): The Zotero key as it appears in the markdown document.
        """

        for k in self._e:
            if zotkey in [self._e[k]["zotkey"], self._e[k]["citekey"]]:
                if "attachment" in self._e[k]:
                    return self._e[k]["attachment"]
                return ["nOaTtAChMeNt"]
        return ["nOcItEkEy"]

    def GetRefData(self, zotkey):
        """Return the key's dictionary.

        zotkey  (string): The Zotero key as it appears in the markdown document.
        """

        for k in self._e:
            if zotkey in [self._e[k]["zotkey"], self._e[k]["citekey"]]:
                return self._e[k]
        return {}

    def GetCitationById(self, Id):
        """Return the complete citation string.

        Id  (string): The item ID as stored by Zotero.
        """

        if Id in self._e.keys():
            return "@" + self._e[Id]["zotkey"] + "#" + self._e[Id]["citekey"]
        return "IdNotFound"

    def GetAnnotations(self, key, offset):
        """Return user annotations made using Zotero's PDF viewer.

        key (string): The Zotero key as it appears in the markdown document.
        """
        zcopy = self._copy_zotero_data()
        conn = sqlite3.connect(zcopy)
        cur = conn.cursor()

        query = (
            """
            SELECT items.key, itemAttachments.ItemID, itemAttachments.parentItemID, itemAnnotations.parentItemID, itemAnnotations.type, itemAnnotations.authorName, itemAnnotations.text, itemAnnotations.comment, itemAnnotations.pageLabel
            FROM items, itemAttachments, itemAnnotations
            WHERE items.key = '"""
            + key
            + """'
            and items.itemID = itemAttachments.parentItemID
            and itemAnnotations.parentItemID = itemAttachments.ItemID
            """
        )
        cur.execute(query)

        citekey = ""
        for k in self._e:
            if key in [self._e[k]["zotkey"], self._e[k]["citekey"]]:
                citekey = self._e[k]["citekey"]

        notes = []
        for i in cur.fetchall():
            mo = re.match("^[0-9]*$", i[8])
            if mo is not None and mo.string == i[8]:
                page = str(int(i[8]) + offset)
            else:
                page = i[8]
            if i[7]:  # Comment
                notes.append("")
                if i[7].find("\n") > -1:
                    ss = i[7].split("\n")
                    for s in ss:
                        notes.append(s)
                    notes.append(" [@" + key + "#" + citekey + self._ypsep + page + "]")
                else:
                    notes.append(
                        i[7] + " [@" + key + "#" + citekey + self._ypsep + page + "]"
                    )
            if i[6]:  # Highlighted text
                notes.append("")
                notes.append(
                    "> "
                    + self._sanitize_markdown(i[6])
                    + " [@"
                    + key
                    + "#"
                    + citekey
                    + self._ypsep
                    + page
                    + "]"
                )
        return notes

    def GetNotes(self, key):
        """Return user notes from a reference.

        key (string): The Zotero key as it appears in the markdown document.
        """
        zcopy = self._copy_zotero_data()
        conn = sqlite3.connect(zcopy)
        cur = conn.cursor()

        query = """
                SELECT items.itemID, items.key
                FROM items
                """
        cur.execute(query)

        key_id = ""
        for item_id, item_key in cur.fetchall():
            if item_key == key:
                key_id = item_id
                break

        cur.execute("SELECT itemID FROM deletedItems")
        zdel = []
        for (item_id,) in cur.fetchall():
            zdel.append(item_id)

        query = """
                SELECT itemNotes.itemID, itemNotes.parentItemID, itemNotes.note
                FROM itemNotes
                WHERE
                    itemNotes.parentItemID IS NOT NULL;
                """
        cur.execute(query)
        notes = ""
        for item_id, item_pId, item_note in cur.fetchall():
            if item_pId == key_id and not item_id in zdel:
                notes += item_note

        conn.close()

        if notes == "":
            return ""

        def key2ref(k):
            k = re.sub("\001", "", k)
            k = re.sub("\002", "", k)
            r = "NotFound"
            for i in self._e:
                if k in [self._e[i]["zotkey"], self._e[i]["citekey"]]:
                    r = self._e[i]["citekey"]
            return "\001" + k + "#" + r + "; "

        def item2ref(s):
            s = re.sub(".*?items%2F(........).*?", "\001\\1\002", s, flags=re.M)
            s = re.sub(
                "\001(........)\002", lambda k: key2ref(k.group()), s, flags=re.M
            )
            s = re.sub(
                "%22locator%22%3A%22(.*?)%22", self._ypsep + "\\1; %22", s, flags=re.M
            )
            s = re.sub("%22.*?" + self._ypsep, self._ypsep, s, flags=re.M)
            s = re.sub("%22.*", "", s, flags=re.M)
            s = re.sub("; " + self._ypsep, self._ypsep, s, flags=re.M)
            s = re.sub("; $", "", s, flags=re.M)
            return "\002" + s + "\003"

        notes = re.sub("<div .*?>", "", notes, flags=re.M)
        notes = re.sub("</div>", "", notes, flags=re.M)
        notes = re.sub(' rel="noopener noreferrer nofollow"', "", notes, flags=re.M)
        notes = re.sub(
            '\\(<span class="citation-item">.*?</span>\\)', "", notes, flags=re.M
        )
        notes = re.sub(
            '<span class="citation" data-citation=(.*?)</span>',
            lambda s: item2ref(s.group()),
            notes,
            flags=re.M,
        )

        p = subprocess.Popen(
            ["pandoc", "-f", "html", "-t", "markdown"],
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
        )
        notes = p.communicate(notes.encode("utf-8"))[0]
        notes = notes.decode()

        notes = re.sub("\001", "@", notes, flags=re.M)
        notes = re.sub("\002", "[", notes, flags=re.M)
        notes = re.sub("\003", "]", notes, flags=re.M)

        notes = re.sub("\\[(.*?)\\]\\{\\.underline\\}", "<u>\\1</u>", notes, flags=re.M)
        notes = re.sub(
            '\\[(.*?)\\]\\{style="text-decoration: line-through"\\}',
            "~~\\1~~",
            notes,
            flags=re.M,
        )
        notes = re.sub(
            "\\[(.*?)\\]\\{\\.highlight.*?\\}", "\\1", notes, flags=re.DOTALL
        )

        return notes + "\n"

    def Info(self):
        """Return information that might be useful for users of ZoteroEntries"""

        r = {
            "zotero.py": os.path.realpath(__file__),
            "data dir": self._dd,
            "attachments dir": self._ad,
            "zotero.sqlite": self._z,
            "better-bibtex.sqlite": self._b,
            "tmpdir": self._tmpdir,
            "references found": len(self._e.keys()),
            "docs": str(self._d) + "\n",
        }
        return r
