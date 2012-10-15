#!/usr/bin/env python
"""Demo of loading a CSV file using res.load_csv
"""
__author__ = "Kevin Davies"
__version__ = "2011-05-31"
__email__ = "kld@alumni.carnegiemellon.edu"

from res import load_csv

if __name__=='__main__':
    # Procedure for embedding the interpreter from:
    #    http://writeonly.wordpress.com/2008/09/08/embedding-a-python-shell-in-a-python-script/,
    #    accessed 2010/11/2

    fname = "load_csv.csv"
    data = load_csv(fname, header_row=2)
    print('Data has been loaded from "%s" into the "data" dictionary.'%fname)
    print("It contains these keys:")
    print(data.keys())

    # Open the IPython or standard Python interpreter.
    try:
        from IPython.Shell import IPShellEmbed
        IPShellEmbed(argv=['-noconfirm_exit'])()
        # Note: The -pylab option cannot be embedded (see http://article.gmane.org/gmane.comp.python.ipython.user/1190/match=pylab)
    except ImportError:
        import code
        # Calling this with globals ensures that we can see the environment.
        code.InteractiveConsole(globals()).interact()