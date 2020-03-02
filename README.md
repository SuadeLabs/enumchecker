# enumchecker
Checks your python enums. Eliminates common attribute errors and name conflicts.

## Usage

Enumchecker checks for common mistakes with enums, including conflicting class definitions and the use of enums that don't exist. For example:

```
from enum import Enum

class MyEnum(Enum):
    a = "a"
    b = "b"

def check(x):
    if x == MyEnum.c:  # <- AttributeError
        print("x was 'c'")
```

You can call the script directly via `python enumchecker.py --dirname <dir>`, to check all files in a directory. Alternatively, once installed, you can invoke the `enumchecker` command.

## Implementation notes

The script `enumchecker.py` is a good resource for learning about python's `ast` module. It searches through class definitions and looks for subclasses of the `Enum` class. It's not foolproof - by reading the source code you can probably think of a few ways to fool it!
