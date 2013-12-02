# -*- coding: utf-8 -*-
import warnings

from Products.CMFCore.permissions import setDefaultRoles
from zope.i18nmessageid import MessageFactory

_ = MessageFactory('collective.cover')

setDefaultRoles(
    'collective.cover: Can Export Layout', ('Manager', 'Site Administrator'))

# supress unused template warnings from grok for templates we know are actually
# used, but not stored on the template attribute of the class. Check layout.py
# for an example of how many templates are used on a class, without being
# associated with it.
#
# for more see https://github.com/collective/collective.cover/issues/362

used_templates = [
    'generalmarkup.pt',
    'group.pt',
    'row.pt',
    'search_list.pt',
    'tile.pt',
    'tree_template.pt',
]

ignore_expr = (
    r'Found.+unassociated template.+/({})'.format('|'.join(used_templates))
)
warnings.filterwarnings('ignore', category=UserWarning, message=ignore_expr)
