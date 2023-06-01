"""
In this file, we introduce a TemplateClass, whose purpose is to be used as the base class
for all tests developed.
"""
# TODO: load the abc module here and use it


class BaseTest:
    """
    This is a BaseTest class that contains a few auxiliary functions that
    multiple tests might find useful. The intended usage is that every new test
    is a subclass of this class.
    """

    def run(self, tx_hash):
        """
        This function runs the test. It must be implemented by all subclasses.
        """

    def alert(self, msg: str):
        """
        This function is called to create an alert for a failed test.
        It must be implemented by all subclasses.
        """
