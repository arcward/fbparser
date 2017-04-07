import argparse
import csv
import json
import os
import unicodedata
import configparser
from collections import defaultdict
from datetime import datetime
from xml.etree.cElementTree import iterparse
from dateutil import parser as date_parser


class MessageArchive:
    def __init__(self, archive_path, my_uid=None, my_name=None,
                 my_aliases=None, replacement_names=None, encoding='utf-8',
                 sanitize_xml=False):
        """Init MessageArchive
        
        :param archive_path: Path to *messages.htm* file
        :param my_uid: Your Facebook UID, in original format 
            (ex: *12345@facebook.com*) or just the digits (*12345*). Will be 
            excluded from export filenames. If *my_name* is passed, that will 
            replace this UID as well.
        :param my_name: Your Facebook display name. This will replace *my_uid* 
            and anything in *my_aliases* if those are passed. (Useful if 
            you've changed your display name before)
        :param my_aliases: A list of aliases that are also "you." These will 
            be replaced with *my_name*. If no value is provided for *my_name*, 
            the first name in this list will take its place.
        :param replacement_names: A dict where each key is a preferred 
            display name for a person, with a list of names they may appear 
            under in the message archive. This is useful when a friend has 
            changed their display name, has had >1 account, or is showing 
            up under their UID.
            Ex: ``{"John Smith": ["John H Smith", "7890@facebook.com"]}``.
        :param encoding: File encoding (default: *UTF-8*)
        :param sanitize_xml: *True* to 'sanitize' the archive file, *False* to 
            leave as-is. (Default: *False*).
        """
        self.archive_path = archive_path  #: Path to archive file
        self.encoding = encoding  #: Encoding to use for all files
        self._threads = None
        self._backup_archive = None  #: Path to backup archive, if sanitized

        if replacement_names is None:
            replacement_names = defaultdict(list)
        else:
            replacement_names = defaultdict(list, replacement_names)

        #: Names to replace if found. Keys: Names as seen in the archive,
        #: values: name to write in its place
        self.replacement_names = replacement_names
        #: Facebook UID (ex: *12345@facebook.com*, or just *12345*)
        self.my_uid = my_uid
        #: Your preferred display name
        self.my_name = my_name
        #: A list of aliases, or names that are also 'you'
        self.my_aliases = my_aliases
        self.aliases()

        # *my_name*=None defaults to first item in *my_aliases*
        if my_name is None and len(self.my_aliases) > 0:
            self.my_name = self.my_aliases[0]

        if sanitize_xml:
            self._sanitize_archive()

    def aliases(self):
        """Adds *my_name* and *my_uid* to *my_aliases*, then adds them 
        to the *replacement_names* dict"""
        if not self.my_aliases:
            self.my_aliases = []

        # Set *my_name* to the first item in *my_aliases*
        if self.my_name is None and len(self.my_aliases) > 0:
            self.my_name = self.my_aliases[0]

        # Reformat *my_uid* if *@facebook.com* wasn't included (this is
        # how it shows up in *messages.htm*)
        if self.my_uid is not None and self.my_uid.isdigit():
            self.my_uid = "{}@facebook.com".format(self.my_uid)

        if self.my_uid not in self.my_aliases:
            self.my_aliases.append(self.my_uid)

        # We're now in the replacement dict
        for alias in self.my_aliases:
            self.replacement_names[self.my_name].append(alias)

    def _sanitize_archive(self):
        """Backup and strip invalid characters from *messages.htm*. 
        
        Copies the original *messages.htm* to *messages.htm.bak*, then strips 
        invalid XML characters from the new *messages.htm*.
        
        Invalid characters can be handled more gracefully with other parsers, 
        however, they're also substantially slower than 
        ``xml.etree.cElementTree.iterparse`` on large files.
        
        :return: Path to the backup archive
        """
        original_path = self.archive_path
        tmp_path = "{}.tmp".format(original_path)
        bak_path = "{}.bak".format(original_path)

        # Open *messages.htm*, create *messages.htm.tmp*, copy to tmp file
        # while stripping invalid characters. Rename *messages.htm* to
        # *messages.htm.bak*, and rename *messages.htm.tmp* to *messages.htm*
        with open(original_path, 'r', encoding=self.encoding) as orig_file, \
                open(tmp_path, 'w', encoding=self.encoding) as tmp_file:
            for line in orig_file:
                tmp_file.write(self.__strip_control_characters(line))

        os.rename(original_path, bak_path)
        os.rename(tmp_path, original_path)
        self._backup_archive = bak_path

    @staticmethod
    def __strip_control_characters(s):
        """Strips control characters from *s*
        
        :param s: String
        :return: *s*, sans control characters
        """
        return "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")

    def reparse(self):
        """Re-parses the archive file (or for the first time, if it hasn't 
        been done yet).
        
        :return: List of threads
        """
        self._threads = None
        return self.threads

    @property
    def threads(self):
        """List of threads in the archive.
        
        Parses the archive file if it hasn't already been done. If it's 
        already been parsed, returns the same list. To parse again, use 
        ``reparse()``.
        
        Structure of a thread in *messages.htm* looks like:
        
        .. code-block:: html
            <div class="thread">['From' person], ['To' person]
            <div class="message">
                <div class="message_header">
                    <span class="user">[Person sending message]</span>
                    <span class="meta">Monday, August 10, 2015 at 10:40pm EDT</span>
                </div>
            </div>
            <p>[actual message content]</p>
            </div>
        
        :return: List of threads
        """
        if self._threads is not None:
            return self._threads

        # Read in threads 'as-is'
        self._threads = []
        for event, elem in iterparse(self.archive_path):
            if elem.get('class') == 'thread':
                fb_thread = Thread(elem)
                self._threads.append(fb_thread)
        # Reformat (replace names, aliases, UIDs, etc)
        self._reformat_threads()
        # After replacing names, merge threads containing the same people
        self._merge_threads()
        self._threads = sorted(self._threads, key=lambda k: k.title)
        return self._threads

    def _merge_threads(self):
        """Merges multiple threads with the same participants into one thread.
        
        The message archive awkwardly breaks up threads into pieces, making 
        it difficult to follow your messages in a single chat over time. It's 
        made more difficult by display names changing over time.
        
        This is run after *_reformat_threads()*, which replaces UIDs/names 
        we've provided, and removes our own name from thread titles.
        
        :return: List of threads consolidated by participant names
        """

        # Consolidate threads, using thread title as the dict key and
        # adding any threads matching that title into its value.
        merged_threads = defaultdict(list)
        for thr in self._threads:
            merged_threads[thr.title].append(thr)

        # For each list of threads with the same thread title, sort the
        # threads (not the messages) by the earliest timestamp.
        # DO NOT SORT BY MESSAGE TIMESTAMP, as Facebook doesn't include
        # seconds in the archive, making it important to retain the
        # original message order (only reversing). This way, the threads
        # are in the correct order and we don't risk losing track of messages
        sorted_threads = []
        for title, threads in merged_threads.items():
            thread = Thread()
            thread.title = title
            threads.sort(key=lambda t: t.messages[0].timestamp)
            thread._messages = [m for msgs in threads for m in msgs.messages]
            sorted_threads.append(thread)
        self._threads = sorted_threads

    def _reformat_threads(self):
        """Reformat threads
        
        * Replaces names found in each thread/message with those in 
            *replacement_names*
        * Creates a list of participants from the thread title
        * Removes our own name(s) from the title
        
        This is done before merging threads, otherwise each display name 
        would be considered a separate person/thread.
        
        :return: 
        """
        # Reverse replacements so each name we want to replace is a key,
        # and its replacement the value
        to_replace = {}
        for key, val in self.replacement_names.items():
            for v in val:
                to_replace[v] = key

        # Split thread title for participants (sometimes there's only one...)
        for thread in self.threads:
            if ', ' in thread.title:
                title_names = thread.title.split(', ')
            else:
                title_names = [thread.title]

            # Replace names in titles, while deleting our own
            my_names = self.my_aliases + [self.my_name]
            for index, person in enumerate(title_names):
                if person in to_replace:
                    title_names[index] = to_replace[person]
                # Check length for the rare occurrence that someone has
                # sent themselves a message
                if title_names[index] in my_names and len(title_names) > 1:
                    del title_names[index]
            title_names = list(set(title_names))

            # Reset to new title
            if len(title_names) == 1:
                thread.title = title_names[0]
            elif len(title_names) > 1:
                thread.title = ','.join(title_names)
            else:
                raise ValueError("Ran out of names?")

            # Replace names in thread messages
            for msg in thread.messages:
                if msg.user in to_replace:
                    msg.user = to_replace[msg.user]

    def write(self, directory='fbparser_out', export_format='csv'):
        """Write all threads to *directory* in either CSV, TXT, or JSON format.
        
        :param directory: Directory to output files. Will be created if it 
            doesn't exist.
        :param export_format: CSV, TXT, or JSON
        :return: 
        """
        if not os.path.exists(directory):
            os.makedirs(directory)

        export_format = export_format.upper()
        if export_format not in ['CSV', 'TXT', 'JSON']:
            raise ValueError("Unsupported export format")

        for t in self.threads:
            if self.my_name in t.participants:
                t.participants = t.participants.remove(self.my_name)
            if export_format == 'CSV':
                t.export_csv(directory=directory)
            elif export_format == 'TXT':
                t.export_txt(directory=directory)
            elif export_format == 'JSON':
                t.export_json(directory=directory)

    @staticmethod
    def _metadata(message_tree):
        """Read message metadata
        
        HTML looks like::
            <div class="message_header">
                    <span class="user">Sender's name</span>
                    <span class="meta">Monday, August 10, 2015 at 10:40pm EDT</span>
            </div>
        
        :param message_tree: 
        :return: 
        """
        meta = {}
        for data in message_tree.iter():
            if data.get('class') == 'message_header':
                for node in data.iter():
                    node_class = node.get('class')
                    if node_class == 'user':
                        meta['user'] = node.text
                    elif node_class == 'meta':
                        meta['timestamp'] = node.text
        return meta

    @staticmethod
    def _text(message_tree):
        message_text = {'text': ''}
        if message_tree.text is not None:
            message_text['text'] = message_tree.text
        return message_text


class Thread:
    """Thread of messages"""
    def __init__(self, xml_tree=None):
        """
        
        :param xml_tree: XML tree to parse
        """
        self.title = None
        self._participants = None
        self._messages = []

        if xml_tree is not None:
            self.title = xml_tree.text
            self.messages = xml_tree

    def export_csv(self, directory=None, encoding='utf-8'):
        """Export thread to CSV
        
        :param directory: Output directory
        :param encoding: Encoding (default: *UTF-8*)
        :return:  
        """
        path = self.__file_path('csv', directory)
        with open(path, self.__mode(path), encoding=encoding) as csv_file:
            # lineterminator='\n' avoids Windows skipping every other row
            cwriter = csv.writer(csv_file,
                                 delimiter=',',
                                 quotechar="\"",
                                 quoting=csv.QUOTE_MINIMAL,
                                 lineterminator='\n')
            for m in self.messages:
                cwriter.writerow([m.timestamp, m.user, m.text])

    def export_txt(self, directory=None, encoding='utf-8'):
        """Export thread to TXT
        
        :param directory: Output directory
        :param encoding: Encoding (default: *UTF-8*)
        :return: 
        """
        path = self.__file_path('txt', directory)
        header = "Thread: {}\nParticipants: {}\n{}"
        border = ''.join(["-" for r in range(0, 80)])
        with open(path, self.__mode(path), encoding=encoding) as txt_file:
            txt_file.write(
                header.format(self.title, ', '.join(self.participants), border)
            )
            for m in self.messages:
                txt_file.write(str(m) + "\n")

    def export_json(self, directory=None, encoding='utf-8'):
        """Export thread to JSON
        
        :param directory: Output directory
        :param encoding: Encoding (default: *UTF-8*)
        :return: 
        """
        path = self.__file_path('json', directory)
        with open(path, self.__mode(path), encoding=encoding) as json_file:
            json_file.write(self.json())

    def export_stdout(self):
        """Print thread to console
        
        :return: 
        """
        border = ''.join(["-" for r in range(0, 80)])
        print(border)
        print("Thread:       {}\n"
              "Participants: {}\n\n"
              .format(self.title, ", ".join(self.participants)))
        for m in self.messages:
            try:
                print(m)
            # Windows console doesn't enjoy non-ASCII characters
            except UnicodeEncodeError:
                print(str(m).encode('utf-8'))
        print("\n\n{}".format(border))

    @staticmethod
    def __mode(path):
        """Determine write mode. If file exists, will be appended
        
        :param path: Path to file
        :return: 'a' (append) if file exists, 'w' if not
        """
        if os.path.exists(path):
            return 'a'
        else:
            return 'w'

    def __file_path(self, extension, directory=None):
        """Generate file path+file name
        
        :param extension: Extension to use (csv, txt, json...)
        :param directory: Output directory
        :return: Full path to file
        """
        if not directory:
            directory = os.getcwd()
        file_name = "{}.{}".format(self.title[:100], extension)
        return os.path.join(directory, file_name)

    @property
    def participants(self):
        """List of thread participants.
        
        Creates a list of all unique names found in the thread's messages. 
        If, for some reason, the thread has no messages, generates the 
        participant list from the thread title.
        
        :return: List of thread participant names
        """
        if self._participants is None:
            names = list(set(m.user for m in self.messages))
            if not bool(names):
                names = self.title.split(', ')
            self.participants = names
        return self._participants

    @participants.setter
    def participants(self, participants):
        self._participants = participants

    @property
    def messages(self):
        """List of messages found in this thread."""
        return self._messages

    @messages.setter
    def messages(self, tree):
        self._messages = []
        message = _Message()
        for msg in tree.iter():
            if msg.tag == 'div' and msg.get('class') == 'message':
                message.metadata = msg
            elif msg.tag == 'p':
                message.text = msg
            # Need to check for completeness, as the actual message text is
            # found immediately outside the div block.
            if message.complete:
                self._messages.append(message)
                message = _Message()
        # Facebook archives messages as most-to-least recent, which is
        # pretty annoying to read. Reverse them so they're old-to-new...
        self._messages = list(reversed(self._messages))

    def json(self):
        """JSON string representing this thread (includes messages)
        
        :return: JSON str
        """
        d = self.__dict__()
        for m in d['messages']:
            m['timestamp'] = datetime\
                .strftime(m['timestamp'], _Message.timestamp_format)
        return json.dumps(d, indent=4, sort_keys=True)

    def __dict__(self):
        """dict representing the thread"""
        return {
            'title': self.title,
            'participants': self.participants,
            'messages': [m.__dict__() for m in self.messages]
        }

    def __str__(self):
        """Returns a list of thread participants"""
        return "Thread: {}".format(', '.join(self.participants))


class _Message:
    #: Timestamp format to be used in place of the archive's lengthy default
    #: Ex: ``Saturday, December 11, 2017 at 05:12 PM`` to ``2017-12-11 17:12``
    timestamp_format = "%Y-%m-%d %H:%M"

    def __init__(self):
        self.user = None  #: User display name or UID (sender)
        self.timestamp = None  #: Message timestamp
        self._text = None  #: Message text/body
        self.original_timestamp = None  #: Long-form timestamp from archive

    @property
    def complete(self):
        """Returns *True* if all data needed is accounted for"""
        return (self.user is not None and
                self.timestamp is not None and
                self._text is not None)

    @property
    def metadata(self):
        """Message metadata (sending user and timestamp)"""
        return {'user': self.user, 'timestamp': self.timestamp}

    @metadata.setter
    def metadata(self, meta_tree):
        for node in meta_tree.iter():
            if node.get('class') == 'message_header':
                for n in node.iter():
                    if n.get('class') == 'user':
                        self.user = n.text
                    elif n.get('class') == 'meta':
                        # Retain original timestamp, but parse into datetime
                        self.original_timestamp = n.text
                        self.timestamp = date_parser.parse(n.text)

    @property
    def text(self):
        """Message text"""
        return self._text

    @text.setter
    def text(self, tree):
        # Messages are enclosed in ``<p></p>`` tags, however, a message
        # missing text (like one with only a GIF) drops the opening ``<p>``
        # tag. Set those to empty strings, rather than None
        if tree.text is None:
            self._text = ''
        else:
            self._text = tree.text

    def json(self):
        """Return a JSON string representing the message"""
        return json.dumps({
            'timestamp': datetime.strftime(self.timestamp,
                                           self.timestamp_format),
            'user': self.user,
            'text': self.text
        }, indent=4, sort_keys=True)

    def __dict__(self):
        """Return a dict representing the message"""
        return {
            'timestamp': self.timestamp,
            'user': self.user,
            'text': self.text
        }

    def __str__(self):
        """Print the message. Format: *[timestamp] [name]: [message_text]*"""
        ts = datetime.strftime(self.timestamp, "%Y-%m-%d %H:%M")
        return "[{:16}] {}: {}".format(ts, self.user, self.text)


def replacements(file_path):
    """Open file containing names to replace
    
    File should be formatted with each line like ``Original name=New name``
    
    Example::
    
        John H Smith=John Smith
        12345@facebook.com=John Smith
        J Smith=John Smith
    
    :param file_path: Path to file
    :return: dict containing replacements
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError("Couldn't find replacements "
                                "file: {}".format(file_path))
    # To make it easier on users, take in an INI file like "old name=new name"
    # without any section headers. Add the header on read
    with open(file_path, 'r') as ini_file:
        ini_str = "[DEFAULT]\n" + ini_file.read()
    conf = configparser.ConfigParser()
    conf.read_string(ini_str)
    replacement_names = conf['DEFAULT']
    d = defaultdict(list)
    # Flip it- create a dict with the "new" names as keys, and add any
    # being transformed to that key into a list of its values
    for k, v in replacement_names.items():
        d[v].append(k)
    return d


def command_line():
    prog = "FBParser"
    description = "Convert Facebook message archive"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(dest='input', help="messages.htm file")
    parser.add_argument('--dir', default='fbparser_out',
                        help="Directory for exports (default: fbparser_out/)")
    parser.add_argument('--csv', action='store_true', help="Export to CSV")
    parser.add_argument('--text', action='store_true', help="Export to TXT")
    parser.add_argument('--json', action='store_true', help="Export to JSON")
    parser.add_argument('--stdout', action='store_true',
                        help="Print threads to console")
    parser.add_argument('--uid', default=None,
                        help="Your Facebook UID (also replaced by --name)")
    parser.add_argument('--name', default=None,
                        help="Your Facebook name (will also replace UID)")
    parser.add_argument('--replace', default=None,
                        help="INI file with replacement names")
    parser.add_argument('--encoding', default='utf-8',
                        help="Output encoding (default: UTF-8)")
    parser.add_argument('--sanitize', action='store_true',
                        help="Strip invalid characters (creates backup of "
                             "original archive)")
    args = parser.parse_args()
    # Hard stop for missing input file
    if not os.path.exists(args.input):
        raise FileNotFoundError("Couldn't find input file: {}"
                                .format(args.input))
    # Read in replacements file
    replacement_names = None
    if args.replace is not None:
        replacement_names = replacements(args.replace)

    # Start/read in threads
    msg_archive = MessageArchive(args.input, args.uid, args.name,
                                 replacement_names=replacement_names,
                                 encoding=args.encoding,
                                 sanitize_xml=args.sanitize)
    threads = msg_archive.threads

    # Start doing things
    if args.csv:
        msg_archive.write(args.dir, 'csv')
    if args.text:
        msg_archive.write(args.dir, 'txt')
    if args.json:
        msg_archive.write(args.dir, 'json')
    if args.stdout:
        for t in threads:
            t.export_stdout()


if __name__ == '__main__':
    rplc_test = replacements('resources/replace.ini')
    archive = 'resources/messages2.htm'
    uid = "501029017"
    n = "Edward Wells"
    arch = MessageArchive(archive, my_uid=uid, my_name=n,
                          replacement_names=rplc_test)
    thrs = arch.threads
    print('')
    arch.write(export_format='txt')

