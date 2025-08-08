"""Verify specific pylint error codes are suppressed in the tool (to correctly mirror platform behavior)."""


# E1101: no-member (testing with dynamic object)
class DynamicObject:
    def __init__(self):
        # Simulate dynamic attribute creation
        setattr(self, "dynamic_attr", "value")


def test_no_member():
    obj = DynamicObject()
    # This would trigger no-member as pylint can't see dynamic_attr
    return obj.dynamic_attr + obj.another_dynamic_attr


# E0611: no-name-in-module (simulate import from external module)
try:
    from phantom.apps import BaseConnector  # noqa: F401  # This might not exist in test env
except ImportError:
    pass


# E1135: unsupported-membership-test
class CustomContainer:
    def __init__(self):
        self.data = []


def test_unsupported_membership():
    container = CustomContainer()
    # This might trigger unsupported-membership-test depending on implementation
    return "item" in container


# E1137: unsupported-assignment-operation
def test_unsupported_assignment():
    some_object = "string"
    # This would trigger unsupported-assignment-operation
    some_object[0] = "x"


# E1136: unsubscriptable-object
def test_unsubscriptable_object():
    some_value = None
    # This would trigger unsubscriptable-object
    return some_value[0]
