Tips and FAQs
=============


Using MultiprocessIterator
~~~~~~~~~~~~~~~~~~~~~~~~~~
If you are using ``MultiprocessIterator`` and communication goes through InfiniBand,
you would probably face crashing problems.
This is because ``MultiprocessIterator`` creates child processes by the ``fork`` system call,
which has `incompatibilities with the design of MPI and InfiniBand <https://www.open-mpi.org/faq/?category=tuning#fork-warning>`_.
To cope with this issue, we can use ``multiprocessing.set_start_method``
to change the way to start child processes::

  multiprocessing.set_start_method('forkserver')

Both ``forkserver`` mode and ``spawn`` mode should work.
Please also refer to our ImageNet example, where ``MultiprocessIterator`` is used.
Unfortunately, ``multiprocessing.set_start_method`` is only available in Python 3.4+.
Therefore you need those recent Python versions to use ``MultiprocessIterator``.


Using Your Own Evaluator
~~~~~~~~~~~~~~~~~~~~~~~~
Method ``create_multi_node_evaluator`` can also be used for customized evaluator classes
that inherit from ``chainer.training.extensions.Evaluator``.
Specifically, it wraps the ``evaluate`` method and returns the averaged values over all workers.
Please also refer to our ImageNet example, where a customized evaluator is used.


Using MPI4py Communicator
~~~~~~~~~~~~~~~~~~~~~~~~~
ChainerMN is based on MPI4py. For advanced users
(e.g., those who want to parallelize preprocessing, create custom extension, etc.),
we encourage you to make use of MPI4py communicators.
Let ``comm`` be a ChainerMN communicator,
then you can obtain MPI4py communicator by ``comm.mpi_comm``.
Please refer to `MPI4py API reference <http://pythonhosted.org/mpi4py/apiref/mpi4py.MPI.Comm-class.html>`_.

Using FP16
~~~~~~~~~~
FP16 (16-bit half precision floating point values) is not supported in ChainerMN as of now.



MPI processes don't exit when an error occurs in a process
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


An MPI runtime is expected to kill all of its child processes if one of them
exits abnormally or without calling `MPI_Finalize()`.  However,
when a Python program runs on `mpi4py`, the MPI runtime often fails to detect
the process failure, and the rest of the processes hang infinitely. It is especially problematic
when you run your ChainerMN program on a cloud environment, in which you are charged on time basis.

This tiny program demonstrates the issue.::

  # test.py
  def func():
    import mpi4py.MPI
    mpi_comm = mpi4py.MPI.COMM_WORLD
    if mpi_comm.rank == 0:
      raise ValueError('failure!')

    mpi4py.MPI.COMM_WORLD.Barrier()

  if __name__ == '__main__':
    func()

  # mpiexec -n 2 python test.py



`mpi4py` offers a solution to force all processes to abort if an uncaught exception occurs.. ::

  $ mpiexec -n 2 python -m mpi4py yourscript.py ...

This also works well with ChainerMN. See `here <http://mpi4py.readthedocs.io/en/stable/mpi4py.run.html>`_
for more details.

If you cannot apply the solution (i.e. you don't have a control of how Python interpreter is invoked),
you can inject the following code snippet into your script file ::

  import sys

  # === begin code snippet
  _old_hook = sys.excepthook

  # Global error handler
  def global_except_hook(exctype, value, traceback):
    import sys
    try:
        import mpi4py.MPI

        _old_hook(exctype, value, traceback)

        rank = mpi4py.MPI.COMM_WORLD.Get_rank()
        sys.stderr.write("\n")
        sys.stderr.write("********************************************************\n")
        sys.stderr.write("ChainerMN: Uncaught exception was detected on rank {}. \n".format(rank))
        sys.stderr.write("           Calling MPI_Abort() to shut down MPI processes...\n")
        sys.stderr.write("********************************************************\n\n\n")
        sys.stderr.flush()

    finally:
        try:
            import mpi4py.MPI
            mpi4py.MPI.COMM_WORLD.Abort(1)
        except Exception as e:
            sys.stderr.write("Sorry, we failed to stop MPI, this MPI process may hang.\n")
            sys.stderr.flush()
            raise e

  sys.excepthook = global_except_hook

  # === end code snippet

  def func():
    "A sample function to cause the problem"
    import mpi4py.MPI
    mpi_comm = mpi4py.MPI.COMM_WORLD
    if mpi_comm.rank == 0:
        raise ValueError('failure!')

    mpi4py.MPI.COMM_WORLD.Barrier()


  if __name__ == '__main__':
    func()

You can choose any of these solutions depending on your environment and restrictions.

NOTE: These techniques are effective only for unhandled Python exceptions.
If your program crashes due to lower-level issues such as `SIGSEGV`, the MPI process may still hang.
