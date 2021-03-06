#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Set up and help run Modelica_ simulation experiments.

This module supports two approaches for managing simulations.  The first is to
create a Modelica_ script (using :meth:`write_script`) and run it within
a Modelica_ environment (see the scripts in "examples/ChuaCircuit/"), which
translates and simulates the models with the prescribed settings.  The second
approach is to execute pre-translated models.  The :meth:`run_models` method
handles this by writing to initialization file(s) (e.g, "dsin.txt") and
launching the appropriate model executables.  The advantage of the first
approach is that formal parameters (those that are hard-coded during
translation) can be adjusted.  However, the second approach is faster because it
does not require a model to be recompiled when only tunable parameters (those
that are not hard-coded during translation) are changed.

The first step in either case is to create a dictionary to specify model
parameters and other settings for simulation experiment.  A single model
parameter may have multiple possible values.  The dictionary is passed to the
:meth:`gen_experiments` function (see that function for a description of the
dictionary format), which combines the values of all the variables (by
piecewise alignment or permutation) and returns a generator to step through the
experiments.  Finally, the generator is passed to the :meth:`write_script` or
:meth:`run_models` function (see first paragraph).

.. _Modelica: http://www.modelica.org/
"""
__author__ = "Kevin Davies"
__email__ = "kdavies4@gmail.com"
__copyright__ = "Copyright 2012-2013, Georgia Tech Research Corporation"
__license__ = "BSD-compatible (see LICENSE.txt)"


import os
import re
import numpy as np
import modelicares.base as base
import doe

from itertools import count
from collections import namedtuple
from datetime import date
from types import GeneratorType


Experiment = namedtuple('Experiment', ['model', 'params', 'args'])
"""Named tuple class to represent a simulation experiment

Instances of this class may be used in the *experiments* argument of
:meth:`write_script` and :meth:`run_models`, although there are some
differences in the entries (see those functions for details).

**Example:**

.. code-block:: python

   >>> from modelicares import *

   >>> experiment = Experiment('ChuaCircuit', params={'L.L': 18}, args={})
   >>> experiment.model
   'ChuaCircuit'
"""

def gen_experiments(models=None, params={}, args={}, design=doe.fullfact):
    """Return a generator for a set of simulation experiments using permutation
    or simple element-wise grouping.

    The generator yields instances of :class:`Experiment`---named tuples of
    (*model*, *params*, *args*), where *model* is the name of a single model
    (type :class:`str`), *params* is a specialized dictionary
    (:class:`ParamDict`) of model parameter names and values, and *arg_dict* is
    a dictionary (:class:`dict`) of command arguments (keyword and value) for
    the Modelica_ tool or environment.

    **Arguments:**

    - *models*: List of model names (including the full model path in Modelica_
      dot notation)

    - *params*: Dictionary of model parameters

         Each key is a variable name and each entry is a list of values.  The
         keys must indicate the hierarchy within the model---either in
         Modelica_ dot notation or via nested dictionaries.

    - *args*: Dictionary of command arguments for the Modelica_ tool or
      environment (e.g., to the :meth:`simulateModel` command in Dymola)

         Each key is an argument name and each entry is a list of settings.

    - *design*: Method of generating the simulation experiments (i.e., design of
      experiments)

         This is a function that returns a iterable object that contains or
         generates the simulation settings.  Several options are available in
         :mod:`modelicares.doe`.

    **Example 1 (element-wise list of experiments):**

    .. code-block:: python

       >>> from modelicares import *

       >>> experiments = gen_experiments(
       ...                  ['Modelica.Electrical.Analog.Examples.ChuaCircuit']*3,
       ...                  {'L.L': [16, 18, 20], 'C2.C': [80, 100, 120]},
       ...                  design=doe.aslisted)
       >>> for experiment in experiments:
       ...     print(experiment.model + str(experiment.params))
       Modelica.Electrical.Analog.Examples.ChuaCircuit(C2(C=80), L(L=16))
       Modelica.Electrical.Analog.Examples.ChuaCircuit(C2(C=100), L(L=18))
       Modelica.Electrical.Analog.Examples.ChuaCircuit(C2(C=120), L(L=20))
       >>> # Note that the model name must be repeated in the models argument.

    **Example 2 (one-factor-at-a-time; first entries are baseline):**

    .. code-block:: python

       >>> from modelicares import *

       >>> experiments = gen_experiments(
       ...                  ['Modelica.Electrical.Analog.Examples.ChuaCircuit'],
       ...                  {'L.L': [16, 18, 20], 'C2.C': [80, 100, 120]},
       ...                  design=doe.ofat)
       >>> for experiment in experiments:
       ...     print(experiment.model + str(experiment.params))
       Modelica.Electrical.Analog.Examples.ChuaCircuit(C2(C=80), L(L=16))
       Modelica.Electrical.Analog.Examples.ChuaCircuit(C2(C=80), L(L=18))
       Modelica.Electrical.Analog.Examples.ChuaCircuit(C2(C=80), L(L=20))
       Modelica.Electrical.Analog.Examples.ChuaCircuit(C2(C=100), L(L=16))
       Modelica.Electrical.Analog.Examples.ChuaCircuit(C2(C=120), L(L=16))

    **Example 3 (permutation---full-factorial design of experiments):**

    .. code-block:: python

       >>> from modelicares import *

       >>> experiments = gen_experiments(
       ...                  ['Modelica.Electrical.Analog.Examples.ChuaCircuit'],
       ...                  {'L.L': [16, 18, 20], 'C2.C': [80, 100, 120]},
       ...                  design=doe.fullfact)
       >>> for experiment in experiments:
       ...     print(experiment.model + str(experiment.params))
       Modelica.Electrical.Analog.Examples.ChuaCircuit(C2(C=80), L(L=16))
       Modelica.Electrical.Analog.Examples.ChuaCircuit(C2(C=100), L(L=16))
       Modelica.Electrical.Analog.Examples.ChuaCircuit(C2(C=120), L(L=16))
       Modelica.Electrical.Analog.Examples.ChuaCircuit(C2(C=80), L(L=18))
       Modelica.Electrical.Analog.Examples.ChuaCircuit(C2(C=100), L(L=18))
       Modelica.Electrical.Analog.Examples.ChuaCircuit(C2(C=120), L(L=18))
       Modelica.Electrical.Analog.Examples.ChuaCircuit(C2(C=80), L(L=20))
       Modelica.Electrical.Analog.Examples.ChuaCircuit(C2(C=100), L(L=20))
       Modelica.Electrical.Analog.Examples.ChuaCircuit(C2(C=120), L(L=20))

    **Example 4 (parameters given in nested form):**

    .. code-block:: python

       >>> from modelicares import *

       >>> models = ['Modelica.Mechanics.MultiBody.Examples.Systems.RobotR3.oneAxis']
       >>> params = dict(axis=dict(motor=dict(i_max=[5, 15],
       ...                                    Ra=dict(R=[200, 300]))))
       >>> for experiment in gen_experiments(models, params):
       ...     print(experiment.model + str(experiment.params))
       Modelica.Mechanics.MultiBody.Examples.Systems.RobotR3.oneAxis(axis(motor(i_max=5, Ra(R=200))))
       Modelica.Mechanics.MultiBody.Examples.Systems.RobotR3.oneAxis(axis(motor(i_max=15, Ra(R=200))))
       Modelica.Mechanics.MultiBody.Examples.Systems.RobotR3.oneAxis(axis(motor(i_max=5, Ra(R=300))))
       Modelica.Mechanics.MultiBody.Examples.Systems.RobotR3.oneAxis(axis(motor(i_max=15, Ra(R=300))))

       >>> # Note that the underlying representation of the parameters is
       >>> # actually flat:
       >>> for experiment in gen_experiments(models, params):
       ...     experiment.params
       {'axis.motor.Ra.R': 200, 'axis.motor.i_max': 5}
       {'axis.motor.Ra.R': 200, 'axis.motor.i_max': 15}
       {'axis.motor.Ra.R': 300, 'axis.motor.i_max': 5}
       {'axis.motor.Ra.R': 300, 'axis.motor.i_max': 15}
       >>> # Also note that Python dictionaries do not preserve order (and it
       >>> # is not necessary here).
    """
    params = base.flatten_dict(params)
    i_args = len(params) + 1
    experiment = lambda x: Experiment(
                             model=x[0],
                             params=ParamDict(zip(params.keys(), x[1:i_args])),
                             args=dict(zip(args.keys(), x[i_args:])))
    try:
        return (experiment(x) for x in
                    design(*([models] + params.values() + args.values())))
    except TypeError:
        print("Error in call to gen_experiments(): models and all of the "
              "entries in params and args must be lists.")

def modelica_array(x):
    """Return a string representing a NumPy_ array in Modelica_ format.

    Square brackets are curled and Booleans are cast to lowercase.

    **Example:**

    .. code-block:: python

       >>> from numpy import array
       >>> from modelicares import *

       >>> x = array([[1, 2], [3, 4]])
       >>> modelica_array(x)
       '{{1, 2}, {3, 4}}'

       >>> modelica_array(array([[True, True], [False, False]]))
       '{{true, true}, {false, false}}'

    .. _NumPy: http://numpy.scipy.org/
    """
    assert isinstance(x, np.ndarray), "Only numpy arrays are supported."
    x = str(x)
    for old, new in [('\[', '{'), ('\]', '}'), (r'\n', ''),
                     (' ?True', 'true'), ('False', 'false'), (' +', ', ')]:
        # Python 2.7 puts an extra space before True when representing an
        # array.
        x = re.sub(old, new, x)
    return x


def modelica_boolean(x):
    """Return a string representing an instance of Python's :class:`bool` in
    Modelica_.

    This is simply 'true' or 'false' (in lowercase).

    **Example:**

    .. code-block:: python

       >>> from modelicares import *

       >>> modelica_boolean(True)
       'true'
       >>> modelica_boolean(False)
       'false'
    """
    return 'true' if x else 'false'


def read_params(names, fname='dsin.txt'):
    """Read parameter values from an initialization or final values file.

    **Arguments:**

    - *names*: Parameter name or list of names (with full model path in
      Modelica_ dot notation)

         A parameter name includes array indices (if any) in Modelica_
         representation (1-base indexing); the values are scalar.

    - *fname*: Name of the file (may include the file path)

    **Example:**

    .. code-block:: python

       >>> from modelicares import *

       >>> read_params(['L.L', 'C1.C'], 'examples/dsin.txt')
       [18.0, 10.0]
    """
    # Aliases for some regular subexpressions
    f = '[+-]?\d+(?:\.\d+)?(?:[Ee][+-]\d+)?' # Floating point number
    i = '[+-]?\d+' # Integer
    u = '\d+' # Unsigned integer

    # Possible regular expressions for a parameter specification (with '%s' for
    # the parameter name)
    patterns = [# Dymola 1- or 2-line parameter specification
                (r'^ *%s +(%s) +%s +%s *\n? +%s +%s +# +%s *$'
                 % (i, f, f, f, u, u, '%s')),
                # From Dymola:
                # column 1: Type of initial value
                #           = -2: special case: for continuing simulation
                #                               (column 2 = value)
                #           = -1: fixed value   (column 2 = fixed value)
                #           =  0: free value, i.e., no restriction
                #                               (column 2 = initial value)
                #           >  0: desired value (column 1 = weight for
                #                                           optimization
                #                                column 2 = desired value)
                #                 use weight=1, since automatic scaling usually
                #                 leads to equally weighted terms
                # column 2: fixed, free or desired value according to column 1.
                # column 3: Minimum value (ignored, if Minimum >= Maximum).
                # column 4: Maximum value (ignored, if Minimum >= Maximum).
                #           Minimum and maximum restrict the search range in
                #           initial value calculation. They might also be used
                #           for scaling.
                # column 5: Category of variable.
                #           = 1: parameter.
                #           = 2: state.
                #           = 3: state derivative.
                #           = 4: output.
                #           = 5: input.
                #           = 6: baseiliary variable.
                # column 6: Data type of variable.
                #           = 0: real.
                #           = 1: boolean.
                #           = 2: integer.
               ]
    # These are tried in order until there is a match.  The group or pair of
    # parentheses contains the parameter value.

    # Read the file.
    src = open(fname, 'r')
    text = src.read()
    src.close()

    # Read the parameters.
    def _read_param(name):
        """Read a single parameter"""
        namere = name.replace('.', '\.') # Escape the dots.
        for pattern in patterns:
            try:
                return float(re.search(pattern % namere, text,
                             re.MULTILINE).group(1))
            except AttributeError:
                pass # Try the next pattern.
        else:
            raise AssertionError(
                "Parameter %s does not exist or is not formatted as expected "
                "in %s." % (name, fname))

    if isinstance(names, basestring):
        return _read_param(names)
    else:
        return [_read_param(name) for name in names]


def run_models(experiments=[(None, {}, {})],
               filemap = {'dslog.txt': '%s_%i.log',
                          'dsres.mat': '%s_%i.mat'}):
    """Run Modelica_ models via pairs of executables and initialization files.

    .. Warning:: This function has not yet been implemented.

    **Arguments**:

    - *experiments*: Tuple or (list or generator of) tuples specifying the
      simulation experiment(s)

         The first entry of each tuple is the name of the model executable.
         The second is a dictionary of model parameter names and values.  The
         third is a dictionary of simulation settings (keyword and value).

         Each tuple may be (optionally) an instance of the tuple subclass
         :class:`Experiment`, which names the entries as *model*, *params*, and
         *args*.  These designations are used below for clarity.

         *model* may include the file path.  It is not necessary to include the
         extension (e.g., ".exe").   There must be a corresponding model
         initialization file on the same path with the same base name and the
         extension ".in".  For Dymola\ :sup:`®`, the executable is the
         "dymosim" file (possibly renamed) and the initialization file is a
         renamed 'dsin.txt' file.

         The keys or variable names in the *params* dictionary must indicate
         the hierarchy within the model---either in Modelica_ dot notation or
         via nested dictionaries.  The items in the dictionary must correspond
         to parameters in the initialization file.  In Dymola, these are
         integers or floating point numbers.  Therefore, arrays must be broken
         into scalars by indicating the indices (Modelica_ 1-based indexing) in
         the key along with the variable name.  Enumerations and Booleans must
         be given as their unsigned integer equivalents (e.g., 0 for *False*).
         Strings and prefixes are not supported.

         Items with values of *None* in *params* and *args* are skipped.

    - *filemap*: Dictionary of result file mappings

          Each key is the path/name of a file that is generated during
          simulation (source) and each value is the path/name it will be copied
          as (destination).  The sources and destinations are relative to the
          directory indicated by the *model* subargument.  '%s' may be included
          in the destination to indicate the model name (*model*) without the
          full path or extension.  '%i' may be included to indicate the
          simulation number in the sequence of experiments.

    There are no return values.
    """
    raise NotImplementedError("run_models() has not yet been implemented.")
    """
    **Examples:**
import os

from itertools import count, product

from modelicares import *

model = 'Modelica.Mechanics.MultiBody.Examples.Systems.RobotR3.oneAxis'
params = {'axis.motor.i_max': [5, 9, 15],
          'axis.motor.Ra.R': [200, 250, 300]}
params = {'axis.motor.i_max': 9,
          'axis.motor.Ra.R': 250}
params = {'L.L': [18, 20],
          'C1.C': [8, 10],
          'C2.C': [80, 100, 120]}


doe = gen_doe(params)
for e in doe:
   print(str(e) + ' or ' + modifier(e))

params.items()

simspecs = [SimSpec(model + "(L(L=%s), C1(C=%s), C2(C=%s))" % params,
            resultFile="ChuaCircuit%i" % i)
            for i, params in zip(count(1), product(Ls, C1s, C2s))]
    """


def write_params(params, fname='dsin.txt'):
    """Write parameter values to a simulation initialization file.

    **Arguments:**

    - *params*: Dictionary of parameters

         Each key is a parameter name (including the full model path in
         Modelica_ dot notation) and each entry is a parameter value.  The
         parameter name includes array indices (if any) in Modelica_
         representation (1-bases indexing).  The values must be representable
         as scalar numbers (integer or floating point).  *True* and *False*
         (not 'true' and 'false') are automatically mapped to 1 and 0.
         Enumerations must be given explicitly as the unsigned integer
         equivalent.  Strings, functions, redeclarations, etc. are not
         supported.

    - *fname*: Name of the file (may include the file path)

    **Example:**

    .. code-block:: python

       >>> from modelicares import *

       >>> write_params({'L.L': 10, 'C1.C': 15}, 'examples/dsin.txt')

    .. testcleanup::
       >>> write_params({'L.L': 18, 'C1.C': 10}, 'examples/dsin.txt')

    This updates the appropriate lines in "examples/dsin.txt":

    .. code-block:: modelica

       -1      10                  0       0                  1  280   # L.L
       ...
       -1      15                  0  1.000000000000000E+100  1  280   # C1.C
    """
    # Pre-process the values.
    for key, value in params.items():
        if isinstance(value, bool):
            params[key] = 1 if value else 0
        assert not isinstance(value, np.ndarray), ("Arrays must be split "
            "into scalars for the simulation initialization file.")
        assert not isinstance(value, basestring), ("Strings cannot be "
            "used as values in the simulation initialization file.")

    # Aliases for some regular subexpressions
    f = '[+-]?\d+(?:\.\d+)?(?:[Ee][+-]\d+)?' # Floating point number
    i = '[+-]?\d+' # Integer
    u = '\d+' # Unsigned integer

    # Possible regular expressions for a parameter specification (with '%s' for
    # the parameter name)
    patterns = [# Dymola 1- or 2-line parameter specification
                (r'(^ *%s *) %s ( *%s +%s *\n? +%s +%s +# +%s *)$'
                 % (i, f, f, f, u, u, '%s')),
                (r'(^ *) %s ( *# *%s *)' % (i, '%s')),
                (r'(^ *) %s ( *# *%s *)' % (f, '%s')),
                # See read_params() for descriptions of the columns.
               ]
    # These are tried in order until there is a match.  The first group or pair
    # of parentheses contains the text before the parameter value and the
    # second contains the text after it (minus one space on both sides for
    # clarity).

    # Read the file.
    src = open(fname, 'r')
    text = src.read()
    src.close()

    # Set the parameters.
    for name, value in params.items():
        namere = name.replace('.', '\.') # Escape the dots.
        for pattern in patterns:
            text, n = re.subn(pattern % namere, r'\1 %s \2' % value, text, 1,
                              re.MULTILINE)
            if n == 1:
                break
        else:
            raise AssertionError(
                "Parameter %s does not exist or is not formatted as expected "
                "in %s." % (name, fname))

    # Re-write the file.
    src = open(fname, 'w')
    src.write(text)
    src.close()


def write_script(experiments=[(None, {}, {})], packages=[],
                 working_dir="~/Documents/Modelica", fname="run-sims.mos",
                 command='simulateModel',
                 results=['dsin.txt', 'dslog.txt', 'dsres.mat', 'dymosim%x',
                          'dymolalg.txt']):
    """Write a Modelica_ script to run simulations.

    **Arguments**:

    - *experiments*: Tuple or (list or generator of) tuples specifying the
      simulation experiment(s)

         The first entry of each tuple is the name of the model to be
         simulated, including the full path in Modelica_ dot notation.  The
         second is a dictionary of parameter names and values.  The third is a
         dictionary of command arguments (keyword and value) for the Modelica_
         tool or environment (see below for Dymola\ :sup:`®`).

         Each tuple may be (optionally) an instance of the tuple subclass
         :class:`Experiment`, which names the entries as *model*, *params*, and
         *args*.  These designations are used below for clarity.

         The keys or variable names in the *params* dictionary must indicate
         the hierarchy within the model---either in Modelica_ dot notation or
         via nested dictionaries.  If *model* is *None*, then *params* is not
         used.  Python_ values are automatically mapped to their Modelica_
         equivalent (see :meth:`ParamDict.__str__`).  Redeclarations and other
         prefixes must be included in the keys along with the variable names.

         :meth:`gen_experiments` can be used to create a generator for this
         argument.

         Items with values of *None* in *params* and *args* are skipped.

    - *working_dir*: Working directory (for the
      executable, log files, etc.)

         '~' may be included to represent the user directory.

    - *packages*: List of Modelica_ packages that should be preloaded or scripts
      that should be run

         Each may be a "\*.mo" file, a folder that contains a "package.mo" file,
         or a "\*.mos" file.  The path may be absolute or relative to
         *working_dir*.  It may be necessary to include in *packages* the file
         or folder that contains the model specified by the *model* subargument,
         but the Modelica Standard Library generally does not need to be
         included.  If an entry is a script ("\*.mos"), it is run from its
         folder.

    - *fname*: Name of the script file to be written (usually in the form
       "\*.mos")

          This may include the path ('~' for user directory).  The results will
          be stored relative to the same folder.  If the folder does not exist,
          it will be created.

    - *command*: Simulation or other command to the Modelica_ tool or
      environment

         Instead of the default ('simulateModel'), this could be
         'linearizeModel' to create a state space representation or
         'translateModel' to create model executables without running them.

    - *results*: List of files to copy to the results folder

         Each entry is the path/name of a file that is generated during
         simulation.  The path is relative to the working directory.  '%x' may
         be included in the filename to represent '.exe' if the operating
         system is Windows and '' otherwise.  The result folders are named by
         the number of the simulation run and placed within the folder that
         contains the simulation script (*fname*).

    If *command* is 'simulateModel' and the Modelica_ environment is
    Dymola\ :sup:`®`, then the following keywords may be used in *args*
    (see *experiments* above).  The defaults (shown in parentheses) are applied
    by Dymola\ :sup:`®`---not by this function.

    - *startTime* (0): Start of simulation

    - *stopTime* (1): End of simulation

    - *numberOfIntervals* (0): Number of output points

    - *outputInterval* (0): Distance between output points

    - *method* ("Dassl"): Integration method

    - *tolerance* (0.0001): Tolerance of integration

    - *fixedstepsize* (0): Fixed step size for Euler

    - *resultFile* ("dsres.mat"): Where to store result

    Note that *problem* is not listed.  It is generated from *model* and
    *params*.  If *model* is *None*, the currently/previously translated model
    will be simulated.

    **Returns:**

    1. List of model names without full model paths

    2. Directory where the script has been saved

    **Example 1 (single simulation):**

    .. code-block:: python

       >>> from modelicares import *

       >>> experiment = Experiment(model='Modelica.Electrical.Analog.Examples.ChuaCircuit',
       ...                         params={},
       ...                         args=dict(stopTime=2500))
       >>> write_script(experiment,
       ...              fname="examples/ChuaCircuit/run-sims1.mos") # doctest: +ELLIPSIS
       (['ChuaCircuit'], '...examples/ChuaCircuit')

    In "examples/ChuaCircuit/run-sims1.mos":

    .. code-block:: modelica

       import Modelica.Utilities.Files.copy;
       import Modelica.Utilities.Files.createDirectory;
       Advanced.TranslationInCommandLog = true "Also include translation log in command log";
       cd(".../Documents/Modelica");
       destination = ".../examples/ChuaCircuit/";

       // Experiment 1
       ok = simulateModel("Modelica.Electrical.Analog.Examples.ChuaCircuit", stopTime=2500);
       if ok then
           savelog();
           createDirectory(destination + "1");
           copy("dsin.txt", destination + "1/dsin.txt", true);
           copy("dslog.txt", destination + "1/dslog.txt", true);
           copy("dsres.mat", destination + "1/dsres.mat", true);
           copy("dymosim", destination + "1/dymosim", true);
           copy("dymolalg.txt", destination + "1/dymolalg.txt", true);
       end if;

       exit();

    where "..." depends on the local system.

    **Example 2 (full-factorial design of experiments):**

    .. code-block:: python

       >>> from modelicares import *

       >>> experiments = gen_experiments(
       ...     models=["Modelica.Electrical.Analog.Examples.ChuaCircuit"],
       ...     params={'L.L': [18, 20],
       ...             'C1.C': [8, 10],
       ...             'C2.C': [80, 100, 120]})
       >>> write_script(experiments, fname="examples/ChuaCircuit/run-sims2.mos") # doctest: +ELLIPSIS
       (['ChuaCircuit', 'ChuaCircuit', 'ChuaCircuit', 'ChuaCircuit', 'ChuaCircuit', 'ChuaCircuit', 'ChuaCircuit', 'ChuaCircuit', 'ChuaCircuit', 'ChuaCircuit', 'ChuaCircuit', 'ChuaCircuit'], '...examples/ChuaCircuit')

    In "examples/ChuaCircuit/run-sims2.mos", there are commands to run and
    save results from 12 simulation experiments.
    """
    # Preprocess the arguments.
    if not isinstance(experiments, (list, GeneratorType)):
        experiments = [experiments]
    fname = base.expand_path(fname)

    working_dir = base.expand_path(working_dir)
    results_dir = os.path.split(fname)[0]
    exe = '.exe' if os.name == 'nt' else ''
    for i, result in enumerate(results):
        results[i] = result.replace('%x', exe)

    # Create the Modelica script and write its header.
    mos = open(fname, 'w')
    mos.write('// Modelica experiment script written by modelicares %s\n'
              % date.isoformat(date.today()))
    mos.write('import Modelica.Utilities.Files.copy;\n')
    mos.write('import Modelica.Utilities.Files.createDirectory;\n')
    mos.write('Advanced.TranslationInCommandLog = true "Also include translation log in command log";\n')
    mos.write('cd("%s");\n' % working_dir)
    for package in packages:
        if package.endswith('.mos'):
            mos.write('cd("%s");\n' % os.path.dirname(package))
            mos.write('RunScript("%s");\n' % os.path.basename(package))
        else:
            if package.endswith('.mo'):
                mos.write('openModel("%s");\n' % package)
            else:
                mos.write('openModel("%s");\n' % os.path.join(package, 'package.mo'))
            mos.write('cd("%s");\n' % working_dir)
    mos.write('destination = "%s";\n'
              % (os.path.normpath(results_dir) + os.path.sep))
    mos.write('\n')
    # Sometimes Dymola opens with an error; simulate any model to clear the
    # error.
    #mos.write('simulateModel("Modelica.Electrical.Analog.Examples.'
    #          'ChuaCircuit");\n\n')

    # Write commands to run the experiments.
    models = []
    for i, (model, params, args) in zip(count(1), experiments):
        # Create an abbreviated name for the model.
        models.append(model[model.rfind('.')+1:])

        # Write to the Modelica script.
        mos.write('// Experiment %i\n' % i)
        if model:
            params = ParamDict(base.flatten_dict(params))
            args['problem'] =  '"%s%s"' % (model, params)
        if args:
            mos.write('ok = %s%s;\n' % (command, ParamDict(args)))
        else:
            mos.write('ok = %s();\n' % command)
        mos.write('if ok then\n')
        mos.write('    savelog();\n')
        folder = str(i)
        mos.write('    createDirectory(destination + "%s");\n' % folder)
        for result in results:
            mos.write('    copy("%s", destination + "%s", true);\n' %
                      (result, os.path.join(folder, result)))
        mos.write('end if;\n')
        mos.write('clearlog();\n\n')

    # Exit the simulation environment.
    # Otherwise, the script will hang until it is closed manually.
    mos.write("exit();\n")
    mos.close()
    return models, results_dir


class ParamDict(dict):
    """Dictionary that prints its items (string mapping) as nested tuple-based
    modifiers, formatted for Modelica_

    Otherwise, this class is the same as :class:`dict`.  The underlying
    structure is not nested or reformatted---only the informal representation
    (:meth:`ParamDict.__str__`).
    """
    def __str__(self):
        """Map the :class:`ParamDict` instance to a string using tuple-based
        modifiers formatted for Modelica_.

        Each key is interpreted as a parameter name (including the full model
        path in Modelica_ dot notation) and each entry is a parameter value.
        The value may be a number (integer or float), Boolean constant (in
        Python_ format---*True* or *False*, not 'true' or 'false'), string, or
        NumPy_ arrays of these.  Modelica_ strings must be given with double
        quotes included (e.g., '"hello"').  Enumerations may be used as values
        (e.g., 'Axis.x').  Values may include functions, but the entire value
        must be expressed as a Python_ string (e.g., 'fill(true, 2, 2)').
        Items with a value of *None* are not shown.

        Redeclarations and other prefixes must be included in the key along
        with the name of the instance (e.g., 'redeclare Region
        regions[n_x, n_y, n_z]').  The single quotes must be explicitly
        included for instance names that contain symbols (e.g., "'H+'").

        Note that Python_ dictionaries do not preserve order.

        **Example:**

        .. code-block:: python

           >>> from numpy import array
           >>> from modelicares import *

           >>> d = ParamDict({'a': 1, 'b.c': array([2, 3]), 'b.d': False,
           ...                'b.e': '"hello"', 'b.f': None})
           >>> print(d)
           (a=1, b(c={2, 3}, e="hello", d=false))

           # The formal representation (and the internal structure) is unaffected:
           >>> d
           {'a': 1, 'b.c': array([2, 3]), 'b.f': None, 'b.e': '"hello"', 'b.d': False}

           # An empty dictionary prints as an empty string (not "()"):
           print(ParamDict({}))

        .. _Python: http://www.python.org/
        """
        def _str(d):
            """Return a string representation of a dictionary in the form of
            tuple-based modifiers (e.g., (a=1, b(c={2, 3}, d=false))).

            Substitutions are made to properly represent Boolean variables and
            arrays in Modelica_.
            """
            elements = []
            for key, value in d.items():
                if isinstance(value, ParamDict):
                    elements.append('%s%s' % (key, value))
                else:
                    if isinstance(value, bool):
                        value = modelica_boolean(value)
                    elif isinstance(value, np.ndarray):
                        value = modelica_array(value)
                    if value is not None:
                        elements.append('%s=%s' % (key, value))
            return '(%s)' % ', '.join(elements) if elements else ''

        # This method to build a nested dictionary adapted from DyMat version
        # 0.5 (Joerg Raedler,
        # http://www.j-raedler.de/2011/09/dymat-reading-modelica-results-with-python/,
        # BSD License).
        root = ParamDict()
        for name in self.keys():
            branch = root
            elements = name.split('.')
            for element in elements[:-1]:
                if not element in branch:
                    branch[element] = ParamDict()
                branch = branch[element]
            branch[elements[-1]] = self.__getitem__(name)

        return _str(root)


if __name__ == '__main__':
    """Test the contents of this file."""
    import doctest
    doctest.testmod()
    exit()
