import unittest
import mpi4py
import numpy as np
import pytest

import chainermn
from chainermn.communicators.naive_communicator import NaiveCommunicator
from chainermn.communicators._communication_utility import chunked_bcast  # NOQA
from chainermn.communicators._communication_utility import INT_MAX  # NOQA

class TestCommunicationUtility(unittest.TestCase):
    def setUp(self):
        self.mpi_comm = mpi4py.MPI.COMM_WORLD
        self.communicator = NaiveCommunicator(self.mpi_comm)

    def test_chunked_bcasts(self):
        # success
        for (s, l) in [(10, 1), (1024, 7), (355678, 2378), (234, INT_MAX - 1)]:
            self.check_chunked_bcast(s, l)
        # fail
        for (s, l) in [(200, -1), (23, INT_MAX)]:
            with pytest.raises(AssertionError):
                self.check_chunked_bcast(s, l)

    def check_chunked_bcast(self, data_size, max_buf_len):
        root = 0
        obj = np.arange(data_size)
        src = None
        if self.communicator.mpi_comm.rank == root:
            src = obj

        dst = chunked_bcast(src, self.communicator.mpi_comm,
                            max_buf_len, root)
        assert len(dst) == len(obj)
        for i in range(len(obj)):
            assert dst[i] == obj[i]
