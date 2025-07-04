from unittest.mock import Mock, MagicMock, patch

class ClassThatDoesSomething:
    def some_method(self):
        return "something"

def example_code(ObjectDoesSomething):
    result = ObjectDoesSomething.some_method()
    return result[:4]


def test_example_code():
    thing = ClassThatDoesSomething()
    thing.some_method = Mock(return_value="testcase")

    result = example_code(thing)

    assert result == "test"