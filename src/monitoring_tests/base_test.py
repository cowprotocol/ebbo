"""
In this file, we introduce a TemplateClass, whose purpose is to be used as the base class
for all tests developed.
"""
from abc import ABC, abstractmethod


class BaseTest(ABC):
    """
    This is a BaseTest class that contains a few auxiliary functions that
    multiple tests might find useful. The intended usage is that every new test
    is a subclass of this class.
    """

    @abstractmethod
    def run(self, tx_hash):
        """
        This function runs the test. It must be implemented by all subclasses.
        """

    @abstractmethod
    def alert(self, msg: str):
        """
        This function is called to create an alert for a failed test.
        It must be implemented by all subclasses.
        """
