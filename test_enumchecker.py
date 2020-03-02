import ast

import pytest

from enumchecker import (
    DuplicateEnumItemError,
    assignment_names,
    detect_duplicates,
    is_enum_class,
    parse_args,
)


def test_assignment_names():
    code = """
class Foo(Enum):
    x = y = r.s = "xy"
    z = "z"

    def something(self):
        var = 1
    """

    node = ast.parse(code).body[0]
    actual = assignment_names(node)
    expected = set("xyz")

    assert actual == expected


def test_detect_duplicates():

    # No duplicates - all OK
    detect_duplicates(list("abc"))

    # Duplicates - not OK
    with pytest.raises(DuplicateEnumItemError):
        detect_duplicates(list("abac"))


def test_is_enum_class():
    class NotAnEnum(object):
        bases = ["Enum"]

    assert not is_enum_class(NotAnEnum)

    code = """
class Foo(Enum, SomethingElse):
    x = "x"
    """

    classdef = ast.parse(code).body[0]
    assert is_enum_class(classdef)


def test_parse_args():
    assert parse_args([]) == ("INFO", ".")
    assert parse_args(["--dirname", "foo"]) == ("INFO", "foo")
    assert parse_args(["--dirname", "foo", "-q"]) == ("WARNING", "foo")
    assert parse_args(["--dirname", "spam", "-v"]) == ("DEBUG", "spam")

    with pytest.raises(SystemExit):
        parse_args(["-q", "-v"])
