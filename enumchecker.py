import ast
import collections
import itertools
import logging
import os
import sys
from argparse import ArgumentParser
from enum import Enum
from pprint import pformat
from typing import Dict, Iterator, List, Optional, Set, Tuple


class DuplicateEnumClassError(Exception):
    pass


class DuplicateEnumItemError(Exception):
    pass


class EnumChecker(object):
    def __init__(self, enumdata: Dict[str, Set[str]]) -> None:
        self.visitor = EnumCheckerVisitor(enumdata)
        self.filename: Optional[str] = None
        self.code = ""

    def checkfile(self, filename):
        """Check a python file for bad enum values"""
        self.filename = filename
        with open(filename, "r") as f:
            self.code = f.read()

        self.visitor.badnodes = []
        self.visitor.visit(ast.parse(self.code, filename=self.filename))

    def summary(self) -> Tuple[int, int]:
        """Return a summary of errors"""
        nodecount = len(self.visitor.badnodes)
        linecount = len(set(n.lineno for n in self.visitor.badnodes))
        return nodecount, linecount

    def results(self) -> Iterator[Tuple[int, str]]:
        """Return verbose errors"""
        if not self.visitor.badnodes:
            return

        suspectlines = [n.lineno for n in self.visitor.badnodes]
        if not suspectlines:
            return

        codelines = self.code.split(os.linesep)
        for badnode in self.visitor.badnodes:
            lineno = badnode.lineno
            yield lineno, codelines[lineno - 1]


class EnumCheckerVisitor(ast.NodeVisitor):
    """
    A class which visits nodes in an abstract syntax tree. For each node, check
    if:
    - it is of type Attribute
    - it is of the form "object.attribute"
    - the object is in the list of enum classes
    - the attribute is *not* in the list of values associated with that object.
    """

    # e.g. Accessing MyEnum.__members__ is ok
    oklist = set(dir(Enum)) | set(vars(Enum))

    def __init__(self, enumdata: Dict[str, Set[str]]):
        self.enums = enumdata
        self.badnodes: List[ast.AST] = []

        super(EnumCheckerVisitor, self).__init__()

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.value, ast.Name):
            # Potentially accessing MyEnum.foo
            enumclassname = node.value.id
        elif isinstance(node.value, ast.Attribute):
            # Potentially accessing my.module.MyEnum.foo
            enumclassname = node.value.attr
        else:
            return

        if (
            enumclassname in self.enums
            and node.attr not in self.enums[enumclassname]
            and node.attr not in self.oklist
        ):
            # Found a non-existant enum attribute
            self.badnodes.append(node)

        self.generic_visit(node)


class EnumCollectorVisitor(ast.NodeVisitor):
    """
    Visit nodes in an abstract syntax tree, looking for Enum classes and
    collecting their member values.
    """

    def __init__(self) -> None:
        self.enums: Dict[str, Set[str]] = {}

        super(EnumCollectorVisitor, self).__init__()

    def visit_ClassDef(self, node: ast.ClassDef):
        if not is_enum_class(node):
            return

        values = assignment_names(node)
        if node.name in self.enums and self.enums[node.name] != values:
            raise DuplicateEnumClassError(node.name)

        self.enums[node.name] = values
        self.generic_visit(node)


def assignment_names(node: ast.ClassDef) -> Set[str]:
    """Find names assigned in a class definition"""
    assignments = (n for n in node.body if isinstance(n, ast.Assign))
    targets = itertools.chain(*[a.targets for a in assignments])
    names = [target.id for target in targets if isinstance(target, ast.Name)]

    detect_duplicates(names)
    return set(names)


def detect_duplicates(names: List[str]) -> None:
    """Detect if there exist duplicate items in an enum"""
    counts = collections.Counter(names)
    for name, count in counts.items():
        if count > 1:
            raise DuplicateEnumItemError(name)


def is_enum_class(node: ast.AST) -> bool:
    if not isinstance(node, ast.ClassDef):
        return False

    return any(
        isinstance(base, ast.Name) and base.id == "Enum" for base in node.bases
    )


def pyfiles(dir_: str) -> Iterator[str]:
    for dirpath, _, filenames in os.walk(dir_):
        for filename in filenames:
            if filename.endswith(".py"):
                yield os.path.join(dirpath, filename)


def collect_enums(
    filenames: List[str], logger: logging.Logger
) -> Dict[str, Set[str]]:

    visitor = EnumCollectorVisitor()
    logger.info("Collecting enums from %d files", len(filenames))
    for fn in filenames:
        try:
            visitor.visit(ast.parse(open(fn).read(), filename=fn))
        except DuplicateEnumClassError as e:
            logger.warning("Found a duplicate enum class name: %s", repr(e))
        except DuplicateEnumItemError as e:
            logger.warning("Found a duplicate enum item: %s", repr(e))
        except SyntaxError:
            logger.warning("Ignoring syntax error in file: %s", fn)

    logger.debug("Enums: %s", pformat(visitor.enums))
    return visitor.enums


def check_files(
    filenames: List[str], enums: Dict[str, Set[str]], logger: logging.Logger
) -> int:
    logger.info("Checking enum values in %d files", len(filenames))

    checker = EnumChecker(enums)

    badfiles = 0
    for fn in filenames:
        logger.debug("Checking file: %s", fn)
        checker.checkfile(fn)
        for lineno, codeline in checker.results():
            logger.info("%s: Line %d: %s", fn, lineno, codeline)

        nodecount, linecount = checker.summary()
        if nodecount:
            logger.warning(
                "%s: %d errors on %d lines", fn, nodecount, linecount
            )
            badfiles += 1

    if not badfiles:
        logger.info("All is well.")
    else:
        logger.critical("Found %d bad files.", badfiles)

    return badfiles


def configure_logger(level: str) -> logging.Logger:
    """Configure a logger"""
    logger = logging.getLogger("Check enums")
    logger.setLevel(level)

    strh = logging.StreamHandler(sys.stdout)

    class CustomFormatter(logging.Formatter):
        def format(self, record):
            # Standard datetime+level+message format, but rjustify the level so
            # that line numbers are also rjustified.
            return "%s %s" % (
                record.levelname.rjust(7),
                record.msg % record.args,
            )

    strh.setFormatter(CustomFormatter())
    logger.addHandler(strh)
    return logger


def parse_args(argv: List[str]) -> Tuple[str, str]:
    parser = ArgumentParser()
    parser.add_argument(
        "--dirname", help="directory to check for py files", default="."
    )
    parser.add_argument("-v", help="verbose", action="store_true")
    parser.add_argument("-q", help="quiet", action="store_true")

    args = parser.parse_args(argv)

    if args.v and args.q:
        print(
            "ERROR: quiet and verbose options are mutually exlusive",
            file=sys.stderr,
        )
        exit(1)

    if args.v:
        loglevel = "DEBUG"
    elif args.q:
        loglevel = "WARNING"
    else:
        loglevel = "INFO"

    return loglevel, args.dirname


def main() -> int:
    loglevel, dirname = parse_args(sys.argv[1:])

    logger = configure_logger(loglevel)
    filenames = list(pyfiles(dirname))

    enums = collect_enums(filenames, logger)

    return min(check_files(filenames, enums, logger), 1)


if __name__ == "__main__":
    exit(main())
