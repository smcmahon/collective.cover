
from z3c.form import button
from z3c.form import form

from z3c.form.interfaces import IDataManager
from z3c.form.interfaces import NO_VALUE

from zope.component import getMultiAdapter

from zope.interface import implements
from zope.interface import Interface

from zope.publisher.interfaces import IPublishTraverse
from zope.publisher.interfaces.browser import IBrowserView

from zope.traversing.browser.absoluteurl import absoluteURL

from plone.app.tiles.browser.base import TileForm

from plone.app.tiles.browser.traversal import TileTraverser

from plone.app.tiles.utils import appendJSONData

from plone.z3cform import layout

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from Products.statusmessages.interfaces import IStatusMessage

from collective.composition.tiles.configuration import ITilesConfigurationScreen
from collective.composition import _


class ITileConfigureView(IBrowserView):
    """
    A tile add view as found by the @@configure-tile traversal view.

    The default edit view is an adapter from (context, request, tile_info) to
    this interface. Per-tile type overrides can be created by registering
    named adapters matching the tile name.
    """


class ConfigureTile(TileTraverser):
    """
    Implements the @@configure-tile namespace.

    This is based on the @@edit-tile
    """

    targetInterface = ITileConfigureView

    def __call__(self):
        raise KeyError("Please traverse to @@configure-tile/tilename/id")

    def publishTraverse(self, request, name):
        """Allow traversal to @@<view>/tilename/tileid
        """

        # Look up the view
        if self.view is None:
            self.view = self.getTileViewByName(name)
            return self

        # 2. Set the id and return the view we looked up in the previous
        # traversal step.
        elif getattr(self.view, 'tileId', None) is None:
            self.view.tileId = name
            return self.view

        raise KeyError(name)


class DefaultConfigureForm(TileForm, form.Form):
    """
    Standard tile configure form, which is wrapped by DefaultConfigureView (see
    below).

    This form is capable of rendering the fields of any tile schema as defined
    by an ITileType utility.
    """

    mode = 'configure'

    name = "configure_tile"

    # Set during traversal
    tileType = None
    tileId = None

    # We need to ignore the context, because for the configuration we can have
    # a lot of stuff stored, which may not be able to be converted to the
    # format the widget expects
    ignoreContext = True

    # Avoid the data to be extracted from the request directly by the form
    # instead of using the tile data manager.
    ignoreRequest = True

    def __init__(self, context, request):
        super(DefaultConfigureForm, self).__init__(context, request)
        self.request['disable_border'] = True

    def update(self):
        if 'buttons.save' in self.request.form or \
           'buttons.cancel' in self.request.form:
            self.ignoreRequest = False

        super(DefaultConfigureForm, self).update()

    def getContent(self):
        typeName = self.tileType.__name__
        tileId = self.tileId

        # Traverse to the tile. If it is a transient tile, it will pick up
        # query string parameters from the original request
        tile = self.context.restrictedTraverse('@@%s/%s' % (typeName, tileId,))
        tile_conf_adapter = getMultiAdapter((self.context, self.request, tile),
                                             ITilesConfigurationScreen)

        configuration = tile_conf_adapter.get_configuration()
        return configuration

    def extractData(self):
        #XXX: Find a better way to implement this
        data = {}
        errors = {}
        for name, widget in self.widgets.items():
            for key, value in self.request.form.items():
                if key.startswith(widget.name):
                    config_name = key[len(widget.name)+1:]
                    field = data.get(name, {})
                    field[config_name] = value
                    data[name] = field
                    if config_name == 'order':
                        widget.field.order = int(value)

        # XXX: Implement error checking
        return data, errors

    def getFieldConfiguration(self, widget):
        conf = getMultiAdapter((widget.context, widget.field),
                               IDataManager).query()

        if conf == NO_VALUE:
            conf = {}

        return conf

    # UI

    @property
    def label(self):
        return _(u"Configure ${name}", mapping={'name': self.tileType.title})

    # Buttons/actions

    @button.buttonAndHandler(_('Save'), name='save')
    def handleSave(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        typeName = self.tileType.__name__

        # Traverse to a new tile in the context, with no data
        tile = self.context.restrictedTraverse('@@%s/%s' % (typeName, self.tileId,))

        tile_conf_adapter = getMultiAdapter((self.context, self.request, tile),
                                             ITilesConfigurationScreen)

        tile_conf_adapter.set_configuration(data)

        #dataManager = ITileDataManager(tile)
        #dataManager.set(data)

        # Look up the URL - We need to redirect to the layout view, since
        # there's the only way from where a user would access the configuration
        contextURL = absoluteURL(tile.context, self.request)

        layoutURL = '%s/layoutedit' % contextURL

        # XXX: We need to fire a notification ?
        #notify(ObjectModifiedEvent(tile))

        # Get the tile URL, possibly with encoded data
        IStatusMessage(self.request).addStatusMessage(_(u"Tile configuration saved.",), type=u'info')

        self.request.response.redirect(layoutURL)

    @button.buttonAndHandler(_(u'Cancel'), name='cancel')
    def handleCancel(self, action):
        contextURL = absoluteURL(self.context, self.request)
        layoutURL = '%s/layoutedit' % contextURL

        # XXX: We need to fire a notification ?
        #notify(ObjectModifiedEvent(tile))

        # Get the tile URL, possibly with encoded data
        IStatusMessage(self.request).addStatusMessage(_(u"Tile configuration cancelled.",), type=u'info')

        self.request.response.redirect(layoutURL)

    def updateActions(self):
        super(DefaultConfigureForm, self).updateActions()
        self.actions["save"].addClass("context")
        self.actions["cancel"].addClass("standalone")


class DefaultConfigureView(layout.FormWrapper):
    """
    This is the default configure view as looked up by the @@configure-tile
    traveral view. It is an unnamed adapter on  (context, request, tileType).

    Note that this is registered in ZCML as a simple <adapter />, but we
    also use the <class /> directive to set up security.
    """

    form = DefaultConfigureForm
    index = ViewPageTemplateFile('templates/tilesconfigurationlayout.pt')

    # Set by sub-path traversal in @@configure-tile - we delegate to the form

    def __getTileId(self):
        return getattr(self.form_instance, 'tileId', None)

    def __setTileId(self, value):
        self.form_instance.tileId = value
    tileId = property(__getTileId, __setTileId)

    def __init__(self, context, request, tileType):
        super(DefaultConfigureView, self).__init__(context, request)
        self.tileType = tileType

        # Configure the form instance
        if self.form_instance is not None:
            if getattr(self.form_instance, 'tileType', None) is None:
                self.form_instance.tileType = tileType
