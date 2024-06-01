import sys
import importlib
import os
import inspect

import django

sys.path.insert(0, '..')
django.setup()

def process_modules(app, what, name, obj, options, lines):
    """Add module names to spelling white list."""
    from enchant.tokenize import basic_tokenize

    if what != 'module':
        return lines

    spelling_white_list = ['', '.. spelling::']
    words = name.replace('-', '.').replace('_', '.').split('.')
    words = [s for s in words if s != '']
    for word in words:
        spelling_white_list += ["    %s" % ''.join(i for i in word if not i.isdigit())]
        spelling_white_list += ["    %s" % w[0] for w in basic_tokenize(word)]
    lines += spelling_white_list
    return lines

def remove_module_docstring(app, what, name, obj, options, lines):
    if what == "class" and name == "ery_backend.base.models.EryNamed":
        options["noindex"] = True

def linkcode_resolve(domain, info):
    if domain != 'py' or not info['module']:
        return None

    filename = info['module'].replace('.', '/')
    mod = importlib.import_module(info['module'])
    basename = os.path.splitext(mod.__file__)[0]
    if basename.endswith('__init__'):
        filename += '/__init__'
    item = mod
    lineno = ''
    for piece in info['fullname'].split('.'):
        item = getattr(item, piece)
        try:
            lineno = '#L%d' % inspect.getsourcelines(item)[1]
        except (TypeError, IOError):
            pass
    return "https://gitlab.com/zetadelta/ery/ery_backend/blob/develop/{}.py{}".format(filename, lineno)

def setup(app):
    app.connect('autodoc-process-docstring', process_modules)
    app.connect("autodoc-process-docstring", remove_module_docstring)

extensions = [
    'sphinx.ext.coverage',
    'sphinx.ext.napoleon',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.todo',
    'sphinx.ext.linkcode',
    'sphinx.ext.intersphinx',
    'sphinxcontrib.spelling',
    'sphinxcontrib_django',
]

napoleon_google_docstring = True
napoleon_include_init_with_doc = False
napoleon_use_keyword = True

autodoc_default_options = {
    'members': None,
    'show-inheritance': None,
    #'inherited-members',
}
autosummary_generate = True

spelling_lang = 'en_US'
spelling_word_list_filename = 'spelling_wordlist.txt'
spelling_show_suggestions = True
spelling_ignore_pypi_package_names = True

templates_path = ['templates']

source_suffix = '.rst'

master_doc = 'index'

project = 'ery.Backend'
copyright = '2018, Zeta Delta OÜ'  # pylint: disable=redefined-builtin
author = 'Los normales'

language = 'en'

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

todo_include_todos = True


html_theme = 'sphinx_rtd_theme'
htmlhelp_basename = 'ery_backenddoc'

latex_documents = [
    (master_doc, 'ery_backend.tex', 'ery.Backend Documentation',
     'Alexander Funcke', 'Development manual'),
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3.6/', None),
    'sphinx': ('http://www.sphinx-doc.org/en/master/', None),
    'django': ('http://django.readthedocs.org/en/latest/', None),
    'google-cloud': ('https://google-cloud-python.readthedocs.io/en/latest/', None),
    'model-utils': ('https://django-model-utils.readthedocs.io/en/latest/', None),
}
