# FBParser

CLI tool/library to parse, organize and export your Facebook message archives.

Facebook data can be downloaded via the link at the bottom of 
your [settings page](https://www.facebook.com/settings). 
This library makes use of the `messages.htm` file located in the `html/` 
directory inside your archive.

#### Why?

Facebook exports your messages as one gigantic HTML file. Messages are grouped 
into individual threads, though chats with a single person are broken up 
throughout the file, which reads oldest-to-newest. That's annoying. This 
fixes that.

## Example use
To simply export your threads to CSV, from the directory containing 
 *messages.htm*, run this command:

`fbparser --csv messages.htm`

This will create a directory named *fbparser_out/* in your current directory 
containing your CSV exports. Exports can also be made in JSON or plaintext 
formats (with `--json` and `--text`), or printed to the console with `--stdout`

To specify your Facebook name (to remove from filenames), use the `--name` 
flag. If you specify your Facebook UID with `--uid`, that UID will be 
replaced with the name you specified. For example:

`fbparser --csv --name="John Smith" --uid="12345@facebook.com" messages.htm`

Everywhere *12345@facebook.com* is found, it will be replaced with 
*John Smith*, which will also be removed from export filenames for clarity.

## Replacing names/UIDs
Facebook's archives are littered with UIDs and people that have changed 
their display names multiple times. To substitute certain names, feed in a 
file with `--replace=file_name.txt`

Example:

```
J Smith=John Smith
12345@facebook.com=John Smith
John H Smith=John Smith
```

Each line should be `Name to replace=New name`

FBParser merges threads containing the same users, so if you see numerous 
threads for the same person with different display names (or UIDs), this 
will correct those names prior to merging the threads.

Example:

`fbparser --csv --uid="12345@facebook.com" --name="John Smith" 
--replace="replace.txt" messages.htm`

## XML parsing errors
If you encounter errors trying to parse an archive, use the `--sanitize` flag. 
This creates a backup as *messages.htm.bak* and writes the new version to 
the original filename before attempting to parse the file.

## Installation

To install from the command line, run the setup script:

`python setup.py install`

