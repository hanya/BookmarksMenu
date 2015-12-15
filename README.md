
BookmarksMenu extension
------
Bookmarks Menu is an extension which provides farovite menu on OpenOffice.

See releases for extension package which can be installed.

## How to install
1. Download OXT package having .oxt file extension from the releases section.
2. Install the OXT package through the extension manager of the office.
3. Restart your office.
4. How to use: https://github.com/hanya/BookmarksMenu/wiki

## Requirements
Current version supports Apache OpenOffice 3.4 and later version. 
And also LibreOffice 4.0 or later is supported.

This is written in Python, which is required to execute PyUNO bridge 
installation.


## Development
For developers.

### Packaging
Compiling is not required but files have to be packed into 
OXT package. zip command is required to make package.

```
 > ./mkzip.sh
```

Help files are converted from MediaWiki syntax to xhp format. 
mwxhp is used this task.

```
 > python mwxhpconv -f bookmarksmenu.xml
```

String resources are stored in po files for each locales. 
They have to be converted into each files and this can be 
done by genres.py script.

```
 > python genres.py
```
