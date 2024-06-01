===================================
Documentation guidelines for Python
===================================

Figuring out the right level of specificity and coverage for documentation is a challenge.
In getting ready to fill out a doc-string one should be clear about why one is writing it.

Reasons to document
-------------------
1.  *Explain code.* Make it easy to understand the code for others and your future self. 
    Especially non-obvious or complex code.
2.  *Describe API* Make it possible to use a module's API without looking at the implementation details. 
    Especially publicly available methods and classes.
3.  *Free-standing documentation* Generating a documenation page for the whole project is very valuable as one tries
    to on-board new developer to the team or just to a certain part of the project.

Reasons not to document
-----------------------
1.  *Redundant information.* If the code is obvious and the method or class is not publically available, 
    then adding documentation does not add any value. For private methods, try to write obvious code instead
    of comments. Not always possible.
2.  *Obsolete information.* Documentation needs to be maintained. Having faulty documenation where the implementation
    has been updated, but the documenation has not been updated to reflect it is often worse than not having any 
    documentation at all.

What must be documented?
------------------------
A function, method or generator must have a docstring unless it meets all of the following criteria:
1.  Not public
2.  Not many lines of code
3.  Obvious

Generating documentation
------------------------

Type the following in the ery_backend directory::

    funcke@xps:~/ery/ery_backend$ make docs

The Makefile target will execute a sphinx build script that will "autodoc" the project's modules using autodoc and 
after that generate html pages from the static and newly generated reStructured text in the docs directory.

reStructured Text
+++++++++++++++++
Sphinx uses what is called reStructured text in order to typeset the documenation. This means that as you write doc-strings
you have the possibility to include fairly complex typesetting with lists, tables, figures and so forth. To learn more about
how to use reStructured Text, check out this Quick guide: http://docutils.sourceforge.net/docs/user/rst/quickref.html.
Or for a less quick guide, the specification: http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html.
For refering to python constructs in documentation, use the Domains functionality: 
http://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html

Napoleon
++++++++
Perhaps more importantly than typesetting the documentation is that the docstrings are easy to read when one is
browsing the code itself. reStructuredText can unfortunately get a bit dense with references. Luckily two projects have
developed pre-processors that let you write documentation that is easy on your eyes when you read it in the code but
that can be processed into the more dense reStructuredText. Out of the two, Numpy and Google, we use the latters style
as it seems less cluttered for our type of modules. Read more about Google's standard, here: 
https://google.github.io/styleguide/pyguide.html?showone=Comments#Comments
List of Docstring sections: http://sphinxcontrib-napoleon.readthedocs.io/en/latest/index.html#id1

We use an extension to Sphinx called Napoleon (http://www.sphinx-doc.org/en/master/ext/napoleon.html) as the preprocessor.

ReedTheDocs theme
+++++++++++++++++
To find out how the various reStructuredText will be rendered in our theme. Check out: http://sphinx-rtd-theme.readthedocs.io/en/latest/demo/demo.html


Public functions, methods and generators
----------------------------------------
For public functions, methods and generators a docstring should give enough information to write a call to the function
without reading the function's code. A docstring should describe the function's calling syntax and its semantics, not
its implementation. For tricky code, comments alongside the code are more appropriate than using docstrings.

As PEP-257 prescribes, the docstring is a phrase ending in a period. It describes the function or method's effect as a command ("Do this", "Return that"), not as a description; e.g. don't write "Returns the pathname ...".

Certain aspects of a function should be documented in special sections, listed below. Each section begins with a heading line, which ends with a colon. Sections should be indented two spaces, except for the heading.

Note that there's no blank line either before or after the docstring (PEP-257).

Args:
    List each parameter by name. A description should follow the name, and be separated by a colon and a space. 
    If the description is too long to fit on a single 127-character line, use a hanging indent of 2 or 4 spaces 
    (be consistent with the rest of the file).
    The description should mention required type(s) and the meaning of the argument.

    If a function accepts \*foo (variable length argument lists) and/or \*\*bar (arbitrary keyword arguments), 
    they should be listed as \*foo and \*\*bar.

Returns: (or Yields: for generators)
    Describe the type and semantics of the return value. If the function only returns None, this section is not required.

Raises:
    List all exceptions that are relevant to the interface.

Example
-------
.. code-block:: python

	def fetch_bigtable_rows(big_table, keys, other_silly_variable=None):
		"""
        Fetch rows from a Bigtable.

		Retrieves rows pertaining to the given keys from the Table instance
		represented by big_table.  Silly things may happen if
		other_silly_variable is not None.

		Args:
			big_table: An open Bigtable Table instance.
			keys: A sequence of strings representing the key of each table row
				to fetch.
			other_silly_variable: Another optional variable, that has a much
				longer name than the other args, and which does nothing.

		Returns:
			A dict mapping keys to the corresponding table row data
			fetched. Each row is represented as a tuple of strings. For
			example:

			{'Serak': ('Rigel VII', 'Preparer'),
			 'Zim': ('Irk', 'Invader'),
			 'Lrrr': ('Omicron Persei 8', 'Emperor')}

			If a key from the keys argument is missing from the dictionary,
			then that row was not found in the table.

		Raises:
			IOError: An error occurred accessing the bigtable.Table object.
		"""
		pass


Classes
-------
Classes should have a doc string below the class definition describing the class. If your class has public attributes, 
they should be documented here in an Attributes section and follow the same formatting as a function's Args section.
Note that the Django fields are public attributes of the class.

Example
-------
.. code-block:: python

	class SampleClass(object):
		"""
        Summary of class here.

		Longer class information....
		Longer class information....

		Attributes:
			likes_spam: A boolean indicating if we like SPAM or not.
			eggs: An integer count of the eggs we have laid.
		"""

		def __init__(self, likes_spam=False):
			"""Inits SampleClass with blah."""
			self.likes_spam = likes_spam
			self.eggs = 0

		def public_method(self):
			"""Performs operation blah."""


Writing Style
-------------
https://developers.google.com/style/
