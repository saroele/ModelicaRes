#!/usr/bin/python
"""Methods to format numbers to support LaTeX_

This module contains three main functions:

- :meth:`label_number` - Generates text to label a number as a quantity
  expressed in a unit

- :meth:`label_quantity` - Generates text to write a quantity as a number times
  a unit

- :meth:`unit2tex` - Converts a Modelica_ unit string to LaTeX_

.. _LaTeX: http://www.latex-project.org/
"""
__author__ = "Kevin Davies"
__email__ = "kdavies4@gmail.com"
__copyright__ = "Copyright 2012-2013, Georgia Tech Research Corporation"
__license__ = "BSD-compatible (see LICENSE.txt)"


import re


# Special replacements for unit strings in tex
rpls = [(re.compile(rpl[0]), rpl[1])
        for rpl in
        [('degC', '^{\circ}\!C'),
         ('degF', '^{\circ}\!F'),
         ('%', r'\%'),
         ('ohm', r'\Omega'),
         ('angstrom', r'\AA'),
         ('pi', r'\pi'),
         ('alpha', r'\alpha'),
         ('Phi', r'\Phi'),
         ('mu', r'\mu'),
         ('epsilon', r'\epsilon')]]

def label_number(quantity="", unit=None, times='\,', per='\,/\,', roman=False):
    r"""Generate text to label a number as a quantity expressed in a unit.

    The unit is formatted with LaTeX_ as needed.

    **Arguments:**

    - *quantity*: String describing the quantity

    - *unit*: String specifying the unit

         This is expressed in extended Modelica_ notation.  See
         :meth:`unit2tex`.

    - *times*: LaTeX_ math string to indicate multiplication

         *times* is applied between the number and the first unit and between
         units.  The default is 3/18 quad space.  The multiplication between
         the significand and the exponent is always indicated by
         ":math:`\times`".

    - *per*: LaTeX_ math string to indicate division

         It is applied between the quantity and the units.  The default is a
         3/18 quad space followed by '/; and another 3/18 quad space.  The
         division associated with the units on the denominator is always
         indicated by a negative exponential.

         If the unit is not a simple scaling factor, then "in" is used instead.
         For example,

            >>> label_number("Gain", "dB")
            'Gain in $dB$'

    - *roman*: *True*, if the units should be typeset in Roman text (rather
      than italics)

    **Examples:**

       >>> label_number("Mobility", "m2/(V.s)", roman=True)
       'Mobility$\\,/\\,\\mathrm{m^{2}\\,V^{-1}\\,s^{-1}}$'

       in LaTeX_: Mobility :math:`\,/\,\mathrm{m^{2}\,V^{-1}\,s^{-1}}`

       >>> label_number("Mole fraction", "1")
       'Mole fraction'

    .. _Modelica: http://www.modelica.org/
    """
    if unit in ['dB', 'degC', 'degF', 'Pag', 'kPag']:
        return "%s in $%s$" % (quantity, unit2tex(unit, times, roman))
    if unit and unit != '1':
        return quantity + '$' + per + unit2tex(unit, times, roman) + '$'
    else:
        return quantity

def label_quantity(number, unit='', format='%G', times='\,', roman=False):
    r"""Generate text to write a quantity as a number times a unit.

    If an exponent is present, then either a LaTeX-formatted exponential or a
    System International (SI) prefix is applied.

    **Arguments:**

    - *number*: Floating point or integer number

    - *unit*: String specifying the unit

         *unit* uses extended Modelica_ notation.  See :meth:`unit2tex`.

    - *format*: Modified Python_ number formatting string

         If LaTeX-formatted exponentials should be applied, then then use an
         uppercase exponential formatter ('E' or 'G').  A lowercase exponential
         formatter ('e' or 'g') will result in a System International (SI)
         prefix, if applicable.

         .. Seealso::
            http://docs.python.org/release/2.5.2/lib/typesseq-strings.html
            and http://en.wikipedia.org/wiki/SI_prefix

    - *times*: LaTeX_ math string to indicate multiplication

         *times* is applied between the number and the first unit and between
         units.  The default is 3/18 quad space.  The multiplication between
         the significand and the exponent is always indicated by
         ":math:`\times`".

    - *roman*: *True*, if the units should be typeset in Roman text (rather
      than italics)

    **Examples:**

       >>> label_quantity(1.2345e-3, 'm', format='%.3e', roman=True)
       '1.234$\\,\\mathrm{mm}$'

       in LaTeX_: :math:`1.234\mathrm{\,mm}`

       >>> label_quantity(1.2345e-3, 'm', format='%.3E', roman=True)
       '1.234$\\times10^{-3}$$\\,\\mathrm{m}$'

       in LaTeX_: :math:`1.234\times10^{-3}\,\mathrm{m}`

       >>> label_quantity(1.2345e6)
       '1.2345$\\times10^{6}$'

       in LaTeX_: :math:`1.2345\times10^{6}`

       >>> label_quantity(1e3, '\Omega', format='%.1e', roman=True)
       '1.0$\\,\\mathrm{k\\Omega}$'

       in LaTeX_: :math:`1.0\,\mathrm{k\Omega}`

    .. _Python: http://www.python.org/
    """
    def _si_prefix(pow1000):
        """Return the SI prefix for a power of 1000.
        """
        # Prefixes according to Table 5 of BIPM 2006
        # (http://www.bipm.org/en/si/si_brochure/; excluding hecto, deca, deci,
        # and centi).
        try:
            return ['Y', # yotta (10^24)
                    'Z', # zetta (10^21)
                    'E', # exa (10^18)
                    'P', # peta (10^15)
                    'T', # tera (10^12)
                    'G', # giga (10^9)
                    'M', # mega (10^6)
                    'k', # kilo (10^3)
                    '', # (10^0)
                    'm', # milli (10^-3)
                    r'{\mu}', # micro (10^-6)
                    'n', # nano (10^-9)
                    'p', # pico (10^-12)
                    'f', # femto (10^-15)
                    'a', # atto (10^-18)
                    'z', # zepto (10^-21)
                    'y'][8 - pow1000] # yocto (10^-24)
        except IndexError:
            print("The factor 1e%i is beyond the range covered by the SI "
                  "prefixes (1e-24 to 1e24)." % 3*pow1000)
            raise

    # Apply engineering notation and SI prefixes.
    if 'E' in format:
        use_SI = False
        format = format.replace('E', 'e')
    elif 'G' in format:
        use_SI = False
        format = format.replace('G', 'g')
    else:
        use_SI = True

    # Format the number as a string.
    numstr = format % number

    # Use LaTeX formatting or SI prefixes if an exponent is present.
    try: # to format the exponent in LaTeX.
        significand, exponent = numstr.split('e')
        if use_SI:
            e = int(exponent)
            if e >= 0:
                pow1000 = e/3
            else:
                pow1000 = -(-e/3)
            pow1000 = int(pow1000) # TODO:  Why is this necessary in Python 3?
            if -8 <= pow1000 <= 8:
                unit = _si_prefix(pow1000) + unit
                numstr, exponent = (format % (number/1000**pow1000)).split('e')
        if not use_SI or exponent != '+00': # Use LaTeX formatting.
            exponent = (exponent[0] + exponent[1:].lstrip('0')).lstrip('+')
            numstr = significand + r'$\times10^{' + exponent + '}$'
    except:
        pass # since no exponent.
    if unit:
        return numstr + '$\,' + unit2tex(unit, times, roman) + '$'
    else:
        return numstr


def unit2tex(unit, times='\,', roman=False):
    r"""Convert a Modelica_ unit string to LaTeX_.

    **Arguments:**

    - *unit*: Unit string in extended Modelica_ notation

        .. Seealso:: Modelica Specification, version 3.2, p. 209
           (https://www.modelica.org/documents)

           In summary, '.' indicates multiplication.  The denominator is
           enclosed in parentheses and begins with a '/'.  Exponents directly
           follow the significand (e.g., no carat ('^')).

    - *times*: LaTeX_ math string to indicate multiplication

         *times* is applied between the number and the first unit and between
         units.  The default is 3/18 quad space.

    - *roman*: *True*, if the units should be typeset in Roman text (rather
      than italics)

    **Example:**

       >>> unit2tex("m/s2", roman=True)
       '\\mathrm{m\\,s^{-2}}'

       which will render in LaTeX_ math as :math:`\mathrm{m\,s^{-2}}`
    """
    splitter = re.compile('([^0-9+-]*)(.*)')

    def _process_unit(unit, is_numerator):
        """Convert a simple Modelica_ unit to LaTeX.
        """
        if unit == '1' or not unit:
            return ''
        tex, exponent = splitter.match(unit).groups()
        if exponent:
            tex += ('^{%s}' if is_numerator else '^{-%s}') % exponent
        elif not is_numerator:
            tex += '^{-1}'
        return tex

    def _process_group(unit, times=r'\,', is_numerator=True):
        """Convert the numerator or denominator of a Modelica_ unit to LaTeX.
        """
        if unit.startswith('('):
            assert unit.endswith(')'), ("The unit group %s starts with '(' but "
                                        "does not end with ')'." % unit)
            unit = unit[1:-1]
        texs = [_process_unit(u, is_numerator) for u in unit.split('.')]
        return times.join(texs)

    if unit:
        # Split the numerator and the denominator.
        if '/' in unit:
            try:
                numerator, denominator = unit.split('/')
            except ValueError:
                print("Check that the unit string %s has at most one division "
                      "sign." % unit)
            unit = (_process_group(numerator, times) + times +
                    _process_group(denominator, times, is_numerator=False))
        else:
            unit = _process_group(unit, times)

        # Make the special replacements.
        for rpl in rpls:
            unit = rpl[0].sub(rpl[1], unit)

        if roman:
            unit = '\mathrm{%s}' % unit

    return unit


if __name__ == '__main__':
    """Test the contents of this file."""
    import doctest
    doctest.testmod()
